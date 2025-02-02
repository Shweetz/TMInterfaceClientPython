
from dataclasses import dataclass
from enum import IntEnum
import os
import random
import sys
import time

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
    diff : int

    def __str__(self):
        return f"rule: From {self.start_time} to {self.end_time}ms, change {self.change_type.name} for {self.input} with max diff of {self.diff} and modify_prob={self.proba}"

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

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.005,   start_time=0, end_time=5760, value=15000))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,     proba=0.5, start_time=3990, end_time=4010, value=5000))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,     proba=0.1, start_time=4020, end_time=4100, value=5000))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,     proba=0.5, start_time=4120, end_time=4160, value=30000))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,     proba=0.05, start_time=4170, end_time=4390, value=15000))

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,     proba=1,   start_time=10500, end_time=12680, value=50))
# rules.append(Change(BINARY_ACCELERATE_NAME, ChangeType.TIMING,proba=1,   start_time=10500, end_time=12680, value=50))
# rules.append(Change(BINARY_BRAKE_NAME, ChangeType.TIMING,     proba=0.3,   start_time=0, end_time=5760, value=20))

# rules.append(Change(BINARY_ACCELERATE_NAME, ChangeType.TIMING, proba=1,   start_time=22000, end_time=27000, value=30))
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,    proba=1, start_time=26000, end_time=27000, value=1000))

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.02,   start_time=22600, end_time=26160, value=15000))

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,     proba=0.1, start_time=3950, end_time=4390, value=1000))

# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,     proba=0.1, start_time=3500, end_time=4390, diff=5000))

rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,     proba=0.02, start_time=39000, end_time=43230, diff=65536))

rules.append(Change(BINARY_BRAKE_NAME, ChangeType.STEER_DIFF,     proba=0.1, start_time=40000, end_time=43230, diff=50))

PRECISION = 0.000001
FILL_INPUTS = True
LOCK_BASE_RUN = True

# steer_cap_accept = True
steer_equal_last_input_proba = 0
steer_zero_proba = 0 # proba to randomize steer to 0 instead of changing direction left/right 
"""END OF PARAMETERS"""

# class Input(IntEnum):
#     UP = BINARY_ACCELERATE_NAME
#     DOWN = BINARY_BRAKE_NAME
#     STEER = ANALOG_STEER_NAME

class Phase(IntEnum):
    WAITING_GAME_FINISH = 0
    ESTIMATING_PRECISE_FINISH = 1

# class IterationState(IntEnum):
#     FASTER = 0
#     SLOWER = 1
#     TIED = 2
#     FASTER_ESTIMATING = 3

lowest_poss_change = min([c.start_time for c in rules])
highest_poss_change = max([c.end_time for c in rules])


class MainClient(Client):
    def __init__(self) -> None:
        self.phase = Phase.WAITING_GAME_FINISH
        self.best_precise_time = -1
        self.finished = False
        self.state_min_change = None
        # self.states = []
        self.begin_buffer = None
        self.current_buffer = None
        # self.base_velocity = None
        self.best_coeff = -1
        self.nb_iterations = 0

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        print(f"Randomizing inputs between {lowest_poss_change} and {highest_poss_change}")
        for rule in rules:
            print(rule)

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
        """

        self.race_time = _time
        if not self.state_min_change and self.race_time == lowest_poss_change - 10:
            # Store state to rewind to for every iteration, for now it is earliest possible input change
            # - 10 because 1 tick is needed to apply inputs in physics
            self.state_min_change = iface.get_simulation_state()

        if self.phase == Phase.WAITING_GAME_FINISH:
            # Wait until simulation reaches regular game finish

            if self.finished:
                # Check finish time

                if self.race_time <= self.lowest_time:
                    # 0.01 better (at least)
                    self.save_result("result_0.01_better.txt")
                    self.lowest_time = self.race_time-10 # -10 because game floors the ms
                    self.best_coeff = -1
                    print(f"FOUND IMPROVEMENT: {self.lowest_time}")
                
                # Game finish time is tied or better, now evaluate precise finish time
                self.phase = Phase.ESTIMATING_PRECISE_FINISH
                self.min_coeff = 0
                self.max_coeff = 1
                # If best_coeff exists, then it was enough to hit finish in best run.
                # So if best_coeff isn't enough for current iteration, then it is proven worse with 1 comparison 
                self.coeff = (self.best_coeff if self.best_coeff != -1 else (self.min_coeff + self.max_coeff) / 2)

                self.base_velocity = self.state_before_finish.velocity # velocity on tick before finish
                self.rewind_before_finish(iface)

            else:
                # Not reached finish yet
                
                if self.race_time > self.lowest_time:
                    # 0.01 worse (at least)
                    self.start_new_iteration(iface)
                else:
                    # Save last state before regular game finish
                    self.state_before_finish = iface.get_simulation_state()

        elif self.phase == Phase.ESTIMATING_PRECISE_FINISH:
            # Needs estimating, either because it's unclear if iteration is faster or because new best iteration needs
            estimate_current_iteration = self.estimate_iteration(iface, _time)

            if estimate_current_iteration == "worse":
                # Start new iteration
                self.start_new_iteration(iface)

            elif estimate_current_iteration == "estimated":
                if self.time_with_speed_coeff < self.best_precise_time or self.best_precise_time == -1:
                    # New best has been found
                    self.best_coeff = self.max_coeff
                    self.best_precise_time = self.time_with_speed_coeff
                    if self.nb_iterations == 0:
                        print(f"base = {self.time_with_speed_coeff}")
                    else:
                        print(f"accept {self.time_with_speed_coeff}")
                        if not LOCK_BASE_RUN:
                            self.begin_buffer.events = self.current_buffer.events
                    
                    # Save inputs to file
                    self.save_result()

                # Start new iteration
                self.start_new_iteration(iface)

            # do nothing if estimate_state == "not_estimated"

    def estimate_iteration(self, iface, _time):
        """Check if self.coeff was enough to finish, and returns 'worse', 'estimated' or 'not_estimated' """

        if _time != self.lowest_time + 10:
            print(f"{_time=} should not happen!")
            return False

        # If self.coeff was enough to finish, update precision on finish time
        if self.finished:
            self.max_coeff = self.coeff
        else:
            self.min_coeff = self.coeff

        self.time_with_speed_coeff = (_time-10 + self.max_coeff*10) / 1000

        # min_coeff = best possible coeff for current iteration
        if self.min_coeff >= self.best_coeff and self.best_coeff != -1:
            # worse (by less than 0.01)
            return "worse"

        elif self.max_coeff - self.min_coeff < PRECISION:
            # current iteration is precisely timed, more precision is a waste of time
            return "estimated"

        else:
            # more estimation needed: either currently tied with best, or current iteration is new best
            self.coeff = (self.min_coeff + self.max_coeff) / 2
            self.rewind_before_finish(iface)
 
        return "not_estimated"

    def rewind_before_finish(self, iface):
        """Rewind to the last tick before finish and apply a coefficient to its speed to estimate finish time"""
        self.phase = Phase.ESTIMATING_PRECISE_FINISH
        self.finished = False
        self.state_before_finish.velocity = [v * self.coeff for v in self.base_velocity]
        iface.rewind_to_state(self.state_before_finish)

    def start_new_iteration(self, iface):
        """Randomize and rewind"""
        self.phase = Phase.WAITING_GAME_FINISH
        self.min_coeff = 0
        self.max_coeff = 1
        self.base_velocity = None
        self.finished = False
        self.randomize_inputs()
        iface.set_event_buffer(self.current_buffer)
        if not self.state_min_change:
            print("no self.state_min_change to rewind to")
            sys.exit()
        iface.rewind_to_state(self.state_min_change)
        self.nb_iterations += 1
        if self.nb_iterations % 1000 == 0:
            print(f"{self.nb_iterations=}")

    def randomize_inputs(self):
        """Restore base run events (with deepcopy) and randomize them using rules.
        Deepcopy can't use EventBufferData.copy() because events is deepcopied but not the individual events"""
        
        # Restore events from base run (self.begin_buffer.events) in self.current_buffer.events using deepcopy
        self.current_buffer.clear()
        for event in self.begin_buffer.events:
            event_time = event.time - 100010
            event_name = self.begin_buffer.control_names[event.name_index]
            event_value = event.analog_value if "analog" in event_name else event.binary_value
            self.current_buffer.add(event_time, event_name, event_value)

        # Apply rules to self.current_buffer.events
        for rule in rules:
            # only inputs that match the rule (ex: steer)
            events = self.current_buffer.find(event_name=rule.input)
            last_steer = 0
            for event in events:
                event_realtime = event.time - 100010
                # event in rule time
                if rule.start_time <= event_realtime <= rule.end_time:
                    # event proba
                    if random.random() < rule.proba:
                        # event type
                        if rule.change_type == ChangeType.STEER_DIFF:
                            if random.random() < steer_equal_last_input_proba:
                                event.analog_value = last_steer
                            else:
                                new_steer = event.analog_value + random.randint(-rule.diff, rule.diff)
                                # if diff makes steer change direction (left/right), try 0
                                if (event.analog_value < 0 < new_steer or new_steer < 0 < event.analog_value) and random.random() < steer_zero_proba:
                                    event.analog_value = 0
                                else:
                                    event.analog_value = new_steer
                                event.analog_value = min(event.analog_value, 65536)
                                event.analog_value = max(event.analog_value, -65536)
                                
                        if rule.change_type == ChangeType.TIMING:
                            # ms -> 0.01
                            diff = random.randint(-rule.diff/10, rule.diff/10)
                            # 0.01 -> ms
                            event.time += diff*10

                if ANALOG_STEER_NAME == self.begin_buffer.control_names[event.name_index]:
                    last_steer = event.analog_value
        
    def save_result(self, time_found="", file_name="result.txt"):
        if time_found == "":
            time_found = self.time_with_speed_coeff
        # Write inputs in file
        res_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + file_name
        with open(res_file, "w") as f:
            f.write(f"# Time: {time_found}, iterations: {self.nb_iterations}\n")
            f.write(self.current_buffer.to_commands_str())

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        # print(f'Reached checkpoint {current}/{target}')
        if current == target:
            # print(f'Finished the race at {self.race_time}')
            self.finished = True
            iface.prevent_simulation_finish()

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""Ideas:
- not rewind to time 0 => rewind to lowest_poss => rewind to 1st change
"""
