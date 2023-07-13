
from dataclasses import dataclass
from enum import IntEnum
import os
import random
import sys
import time

# import tminterface.structs as structs
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME

class ChangeType(IntEnum):
    STEER_DIFF = 0
    TIMING = 1
     # TODO CREATE_REMOVE = 2

@dataclass
class Change:
    input : str
    change_type : ChangeType
    proba : float
    start_time : int
    end_time : int
    value : int

"""START OF PARAMETERS (you can change here)"""
rules = []
# rules.append(Change(0.02, 10000, 12000, Input.UP, ChangeType.TIMING, 50))
# rules.append(Change(0.1, 0, 100, Input.DOWN, ChangeType.CREATE_REMOVE, 0))

# rules.append(Change(0.01, 25000, 26130, ANALOG_STEER_NAME, ChangeType.STEER_DIFF, 15000))

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.025, start_time=3000, end_time=4390, value=15000))

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.05, start_time=0, end_time=1820, value=1000))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.2, start_time=1830, end_time=4000, value=100))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,     proba=1, start_time=4000, end_time=4390, value=10))

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.2,  start_time=0, end_time=1300, value=1000))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,     proba=0.2,  start_time=0, end_time=1300, value=10))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.05, start_time=1300, end_time=1820, value=1000))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.2, start_time=1830, end_time=4000, value=100))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,     proba=1, start_time=4000, end_time=4390, value=10))

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=1,   start_time=0, end_time=4390, value=1000))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,     proba=1, start_time=0, end_time=4390, value=10))

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,     proba=1,   start_time=10500, end_time=12680, value=50))
# rules.append(Change(BINARY_ACCELERATE_NAME, ChangeType.TIMING,proba=1,   start_time=10500, end_time=12680, value=50))
# rules.append(Change(BINARY_BRAKE_NAME, ChangeType.TIMING,     proba=0.5,   start_time=10500, end_time=12680, value=50))

rules.append(Change(BINARY_ACCELERATE_NAME, ChangeType.TIMING, proba=1,   start_time=22000, end_time=27000, value=30))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,    proba=1, start_time=26000, end_time=27000, value=1000))

PRECISION = 0.001
FILL_INPUTS = True
LOCK_BASE_RUN = False

# steer_cap_accept = True
steer_equal_last_input_proba = 0
"""END OF PARAMETERS"""

# class Input(IntEnum):
#     UP = 0
#     DOWN = 1
#     STEER = 2

class Phase(IntEnum):
    WAITING_GAME_FINISH = 0
    ESTIMATING_PRECISE_FINISH = 1

class IterationState(IntEnum):
    FASTER = 0
    SLOWER = 1
    TIED = 2
    FASTER_ESTIMATING = 3

lowest_poss_change = min([c.start_time for c in rules])
highest_poss_change = max([c.end_time for c in rules])


class MainClient(Client):
    def __init__(self) -> None:
        self.best = -1
        self.time = -1
        self.cp_count = 0
        self.force_accept = False
        self.phase = Phase.WAITING_GAME_FINISH
        self.best_precise_time = -1
        self.curr_finish_time = -1
        self.finished = False
        self.state_min_change = None
        self.states = []
        self.begin_buffer = None
        self.current_buffer = None
        # self.best_buffer = None
        # self.best_inputs = None
        self.base_velocity = None
        self.best_coeff = -1
        self.nb_iterations = 0
        self.iteration_is_faster = False

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_simulation_begin(self, iface):
        iface.remove_state_validation()

        self.begin_buffer = iface.get_event_buffer()
        self.lowest_time = self.begin_buffer.events_duration
        if FILL_INPUTS:
            self.fill_inputs()
        self.current_buffer = self.begin_buffer.copy() # copy avoids timeout?
        # print(self.current_buffer.to_commands_str())
        
    def fill_inputs(self, start_fill=0, end_fill=0):
        """Fill inputs between start_fill and end_fill included"""
        if end_fill == 0:
            end_fill = self.lowest_time
            
        curr_steer = 0
        for event_time in range(start_fill, end_fill+10, 10):
            events_at_time = self.begin_buffer.find(time=event_time, event_name=ANALOG_STEER_NAME)
            if len(events_at_time) > 0:
                curr_steer = events_at_time[-1].analog_value
            else:
                self.begin_buffer.add(event_time, ANALOG_STEER_NAME, curr_steer)
        
    def on_simulation_step(self, iface: TMInterface, _time: int):
        """ 
        WARNING with self.lowest_time (real game finish time)!
        If best time = 5.005, then self.lowest_time = 5000 but self.race_time = 5010 when finished = True
        
        Main idea:
        1. Iteration accept if finished with self.race_time <= self.lowest_time
        2. Iteration reject if not finished with self.race_time > self.lowest_time
        3. Estimate a precise time if better or tied to 0.01
        4. If tied, start estimating with best velocity coeff: if iteration doesn't finish, reject

        if self.finished:
            if self.race_time <= self.lowest_time:
                print("better 0.01")
            else:
                print("need estimate")
                coeff = best_coeff
                if finishes: better or equal => more estimate
                else: worse => throw
        else:
            if self.race_time > self.lowest_time:
                print("worse 0.01")
        """

        self.race_time = _time
        if not self.state_min_change and self.race_time == lowest_poss_change:
            self.state_min_change = iface.get_simulation_state()



        if self.phase == Phase.WAITING_GAME_FINISH:
            # print("on_simulation_step WAITING_GAME_FINISH")
            # print(f"{self.race_time=} {self.finished=}")

            # WARNING WITH self.lowest_time!
            # If best time = 5.005, then self.lowest_time = 5000 but self.race_time = 5010 when finished = True

            # If reached finish, check finish time
            if self.finished:
                # print(f"{self.race_time} finished")
                if self.race_time <= self.lowest_time:
                    self.save_result("result_0.01_better.txt")
                    # print(f"better yo {self.race_time=} {self.lowest_time=}")
                    self.lowest_time = self.race_time-10 # -10 because game floors the ms
                    self.best_coeff = -1
                    self.coeff = 0.5
                    # self.iteration_is_faster = True
                    # self.best_inputs = self.current_buffer.to_commands_str()
                
                # Finish time is tied or better, now evaluate precise finish time
                self.phase = Phase.ESTIMATING_PRECISE_FINISH
                # self.base_velocity = self.states[-1].velocity # velocity on tick before finish
                self.min_coeff = 0
                self.max_coeff = 1
                if self.best_coeff != -1:
                    self.coeff = 1
                else:
                    self.coeff = (self.min_coeff + self.max_coeff) / 2
                self.base_state = self.states[-2]
                # self.state_before_finish = self.states[-1]
                # self.base_velocity = self.state_before_finish.velocity # velocity on tick before finish
                self.finished = False
                iface.rewind_to_state(self.states[-2])

            # Not reached finish
            else:
                # Save states to rewind after finding regular finish
                self.states.append(iface.get_simulation_state())
                # not needed? only last state needed?
                
                # If finish time is at least 0.01 slower, randomize and rewind
                if self.race_time > self.lowest_time:
                    # print(f"-1 ({self.race_time})")
                    # print(f"worse yo {self.race_time=} {self.lowest_time=}")
                    self.start_new_iteration(iface)
                return

        elif self.phase == Phase.ESTIMATING_PRECISE_FINISH:
            # print("on_simulation_step ESTIMATING_PRECISE_FINISH")
            # if self.best_coeff == -1:
            #     self.coeff = 0.5
            # else:
            #     self.coeff = self.best_coeff

            is_evaluated = self.on_step(iface, _time)
            # There are 3 states we can be in: precise finish is better, worse, or needs more precise evaluation
            if is_evaluated:
                # print(f"{self.time_with_speed_coeff} evaluated")
                if self.time_with_speed_coeff < self.best_precise_time or self.best_precise_time == -1:
                    self.best_coeff = self.max_coeff
                    self.best_precise_time = self.time_with_speed_coeff
                    # self.best_inputs = self.current_buffer.to_commands_str()
                    if self.nb_iterations == 0:
                        print(f"base = {self.time_with_speed_coeff}")
                    else:
                        print(f"accept {self.time_with_speed_coeff}")
                        if not LOCK_BASE_RUN:
                            self.begin_buffer.events = self.current_buffer.events

                    self.save_result()
                else:
                    # print(f"{self.best_precise_time} < {self.time_with_speed_coeff}")
                    pass

                # Start new iteration
                self.start_new_iteration(iface)

    def on_step(self, iface, _time):
        """This many ticks rewinded make no sense but if it's not done, it doesn't work, so enjoy"""
        # print(f"on_step {_time}, {self.coeff=}, {self.finished=}")

        if _time < self.lowest_time - 10:
            print("should not happen!")
            return False

        elif _time == self.lowest_time - 10:
            # This is necessary to rewind here for some reason even if nothing needs to be done here
            # return
        #     self.min_coeff = 0
        #     self.max_coeff = 1
            # self.base_velocity = None

        # if _time == self.lowest_time - 10:
            # Save base state to rewind before any change
            self.base_state = iface.get_simulation_state()
            
            # print()

        elif _time == self.lowest_time:
            # This is necessary to rewind here for some reason even if nothing needs to be done here
            # return
            self.state_before_finish = iface.get_simulation_state()

            # Save base run velocity
            if not self.base_velocity:
                self.base_velocity = self.state_before_finish.velocity

            # self.coeff = (self.min_coeff + self.max_coeff) / 2

            # Apply a coefficient to the speed on the last tick
            self.state_before_finish.velocity = [v * self.coeff for v in self.base_velocity]
            iface.rewind_to_state(self.state_before_finish)

            # print(f"pos_z={self.state.position[2]}")
            # print(f"vel_z={self.state.velocity[2]}")
            # pass

        elif _time == self.lowest_time + 10:
            # print(f"pos_z={iface.get_simulation_state().position[2]} (tick+1)")

            if self.finished:
                # print(f"finish with {self.coeff}")
                # print(f"{self.time_with_speed_coeff}: finish")
                self.max_coeff = self.coeff
            else:
                # print(f"no finish with {self.coeff}")
                # print(f"{self.time_with_speed_coeff}: no finish")
                self.min_coeff = self.coeff

            self.time_with_speed_coeff = (_time-10 + self.max_coeff*10) / 1000

            # min_coeff = best possible time
            # so if min_coeff >= best_coeff then it is slower and stop estimating
            if self.min_coeff >= self.best_coeff and self.best_coeff != -1:
                # print("worse tied")
                return True # worse
                
            # if precise enough, return
            if self.max_coeff - self.min_coeff < PRECISION:
                # print("precise")
                return True # better
            else:
                self.coeff = (self.min_coeff + self.max_coeff) / 2
                self.rewind_hell(iface)
 
        return False
            # print(f"{self.finish_crossed=}")
            # self.nb_rewinds += 1
            # self.rewinded = True

        # if _time >= self.lowest_time + 20:
        #     self.min_coeff = 0
        #     self.max_coeff = 0
        #     self.time_with_speed_coeff = _time / 1000

    def start_new_iteration(self, iface):
        self.phase = Phase.WAITING_GAME_FINISH
        self.min_coeff = 0
        self.max_coeff = 1
        self.base_velocity = None
        self.finished = False
        self.states = []
        self.randomize_inputs()
        iface.set_event_buffer(self.current_buffer)
        if not self.state_min_change:
            print("no self.state_min_change to rewind to")
            sys.exit()
        iface.rewind_to_state(self.state_min_change)
        self.nb_iterations += 1
        if self.nb_iterations % 1000 == 0:
            print(f"{self.nb_iterations=}")
        self.iteration_is_faster = False

    def rewind_hell(self, iface):
        self.phase = Phase.ESTIMATING_PRECISE_FINISH
        # self.state_before_finish = state
        # self.base_velocity = self.state_before_finish.velocity # velocity on tick before finish
        self.finished = False
        # self.state_before_finish.velocity = [v * self.coeff for v in self.base_velocity]
        iface.rewind_to_state(self.base_state)

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        # print(f'Reached checkpoint {current}/{target}')
        if current == target:
            # print(f'Finished the race at {self.race_time}')
            self.finished = True
            iface.prevent_simulation_finish()

    def randomize_inputs(self):
        # Deepcopy EventBufferData.events
        # can't use copy() because events is deepcopied but not the individual events
        # self.current_buffer = self.begin_buffer.copy()
        
        self.current_buffer.clear()
        for event in self.begin_buffer.events:
            event_time = event.time - 100010
            event_name = self.begin_buffer.control_names[event.name_index]
            event_value = event.analog_value if "analog" in event_name else event.binary_value
            self.current_buffer.add(event_time, event_name, event_value)

        # print(self.begin_buffer.to_commands_str())
        # print(self.current_buffer.to_commands_str())
        # Apply rules
        for rule in rules:
            # only inputs that match the rule (ex: steer)
            events = self.current_buffer.find(event_name=rule.input)
            last_steer = 0
            for event in events:
                event_realtime = event.time - 100010
                # print("1")
                # print(event_realtime)
                # event in rule time
                if rule.start_time <= event_realtime <= rule.end_time:
                    # event proba
                    if random.random() < rule.proba:
                        # event type
                        if rule.change_type == ChangeType.STEER_DIFF:
                            if random.random() < steer_equal_last_input_proba:
                                event.analog_value = last_steer
                            else:
                                new_steer = event.analog_value + random.randint(-rule.value, rule.value)
                                # if diff makes steer change direction (left/right), try 0
                                if (event.analog_value < 0 < new_steer or new_steer < 0 < event.analog_value) and random.random() < 0.5:
                                    event.analog_value = 0
                                else:
                                    event.analog_value = new_steer
                                event.analog_value = min(event.analog_value, 65536)
                                event.analog_value = max(event.analog_value, -65536)
                                
                        if rule.change_type == ChangeType.TIMING:
                            # ms -> 0.01
                            diff = random.randint(-rule.value/10, rule.value/10)
                            # 0.01 -> ms
                            event.time += diff*10

                if ANALOG_STEER_NAME == self.begin_buffer.control_names[event.name_index]:
                    last_steer = event.analog_value
                # print(event)
        # print(self.current_buffer.to_commands_str())
        
    def save_result(self, file_name="result.txt"):
        # Write inputs in result.txt
        res_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + file_name
        with open(res_file, "w") as f:
            f.write(f"# Time: {self.time_with_speed_coeff}, iterations: {self.nb_iterations}\n")
            f.write(self.current_buffer.to_commands_str())

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""Ideas:
- not rewind to time 0 => rewind to lowest_poss => rewind to 1st change
"""
