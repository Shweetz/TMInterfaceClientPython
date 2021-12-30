
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

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.1,   start_time=22000, end_time=27000, value=65000))

rules.append(Change(BINARY_ACCELERATE_NAME, ChangeType.TIMING, proba=1,   start_time=22000, end_time=27000, value=30))

PRECISION = 0.0001
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
        self.max_coeff = 0
        self.max_coeff = 1
        self.best_coeff = -1
        self.nb_iterations = 0

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
        
    def fill_inputs(self):
        curr_steer = 0
        for event_time in range(0, self.lowest_time, 10):
            events_at_time = self.begin_buffer.find(time=event_time, event_name=ANALOG_STEER_NAME)
            if len(events_at_time) > 0:
                curr_steer = events_at_time[-1].analog_value
            else:
                self.begin_buffer.add(event_time, ANALOG_STEER_NAME, curr_steer)
        
    def on_simulation_step(self, iface: TMInterface, _time: int):
        self.race_time = _time
        if not self.state_min_change and self.race_time == lowest_poss_change:
            self.state_min_change = iface.get_simulation_state()

        if self.phase == Phase.WAITING_GAME_FINISH:
            # print(f"{self.race_time=} {self.finished=}")
            # If at least 0.01 slower, randomize and rewind
            if self.race_time > self.lowest_time + 10:
                # print(f"-1 ({self.race_time})")
                
                # Start new iteration
                self.finished = False
                self.states = []
                self.randomize_inputs()
                iface.set_event_buffer(self.current_buffer)
                iface.rewind_to_state(self.state_min_change)
                self.nb_iterations += 1
                if self.nb_iterations % 1000 == 0:
                    print(f"{self.nb_iterations=}")
                return

            if self.finished:
                # print(f"{self.race_time} finished")
                if self.race_time <= self.lowest_time:
                    self.lowest_time = self.race_time-10
                    # self.best_inputs = self.current_buffer.to_commands_str()
                    self.save_result("result_0.01_better.txt")
                    self.best_coeff = -1

                # Finish time is tied or better, now evaluate precise finish time
                self.phase = Phase.ESTIMATING_PRECISE_FINISH
                self.finished = False
                self.base_velocity = None
                self.base_state = self.states[-2]
                iface.rewind_to_state(self.states[-3])
            else:
                # Save states to rewind after finding regular finish
                self.states.append(iface.get_simulation_state())

        elif self.phase == Phase.ESTIMATING_PRECISE_FINISH:
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
                self.phase = Phase.WAITING_GAME_FINISH
                self.finished = False
                self.states = []
                self.randomize_inputs()
                iface.set_event_buffer(self.current_buffer)
                iface.rewind_to_state(self.state_min_change)
                self.nb_iterations += 1
                if self.nb_iterations % 1000 == 0:
                    print(f"{self.nb_iterations=}")

    def on_step(self, iface, _time):
        if _time < self.lowest_time - 10:
            print("idk")
            return

        # print(f"s {_time}")
        elif _time == self.lowest_time - 10:
            # print("hello")
            self.min_coeff = 0
            self.max_coeff = 1
            # self.base_velocity = None

        # if _time == self.lowest_time - 10:
            # Save base state to rewind before any change
            # self.base_state = iface.get_simulation_state()
            pass
            # print()

        elif _time == self.lowest_time:
            self.coeff = (self.min_coeff + self.max_coeff) / 2

            self.state = iface.get_simulation_state()

            # Save base run velocity
            if not self.base_velocity:
                self.base_velocity = self.state.velocity

            # Apply a coefficient to the speed on the last tick
            self.state.velocity = [v * self.coeff for v in self.base_velocity]
            iface.rewind_to_state(self.state)

            # print(f"pos_z={self.state.position[2]}")
            # print(f"vel_z={self.state.velocity[2]}")

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
            # so if min_coeff > best_coeff then it is slower and stop estimating
            if self.min_coeff > self.best_coeff and self.best_coeff != -1:
                return True
                
            # time.sleep(0.1)
            # iface.prevent_simulation_finish()
            if self.max_coeff - self.min_coeff > PRECISION:
                iface.rewind_to_state(self.base_state)
                self.finished = False
            else:
                return True
 
        return False
            # print(f"{self.finish_crossed=}")
            # self.nb_rewinds += 1
            # self.rewinded = True

        # if _time >= self.lowest_time + 20:
        #     self.min_coeff = 0
        #     self.max_coeff = 0
        #     self.time_with_speed_coeff = _time / 1000

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
