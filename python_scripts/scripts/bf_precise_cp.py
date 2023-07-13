
from dataclasses import dataclass
from enum import IntEnum
import os
import random
import struct
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

rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.01, start_time=4400, end_time=5760, diff=65536))
#rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,     proba=0.01, start_time=2800, end_time=4000, diff=20))
#rules.append(Change(BINARY_ACCELERATE_NAME, ChangeType.TIMING,proba=0.05, start_time=28000, end_time=62000, diff=30))
#rules.append(Change(BINARY_BRAKE_NAME, ChangeType.TIMING,     proba=0.05, start_time=28000, end_time=99000, diff=30))

PRECISION = 0.000001
FILL_INPUTS = True
LOCK_BASE_RUN = False

# steer_cap_accept = True
steer_equal_last_input_proba = 0
steer_zero_proba = 0 # proba to randomize steer to 0 instead of changing direction left/right 
sim_end = 5760
target_CP = 1
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
        self.simu_end = sim_end

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
            end_fill = self.simu_end
            
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

                # Game finish time is tied or better, now evaluate precise finish time
                self.phase = Phase.ESTIMATING_PRECISE_FINISH
                self.min_coeff = 0
                self.max_coeff = 1
                # If best_coeff exists, then it was enough to hit finish in best run.
                # So if best_coeff isn't enough for current iteration, then it is proven worse with 1 comparison 
                self.coeff = (self.best_coeff if self.best_coeff != -1 else (self.min_coeff + self.max_coeff) / 2)

                self.base_velocity = self.state_before_finish.velocity # velocity on tick before finish
                self.base_angular_velocity = self.get_angular_velocity(self.state_before_finish)
                self.rewind_before_finish(iface)

            else:
                # Not reached finish yet
                
                if self.race_time > self.simu_end:
                    # 0.01 worse (at least)
                    #block new iteration for CP estimation from most recent critical CP reached
                    if self.CP_reached == True:
                        
                        self.state_before_finish = self.cp_state
                        _time = self.cp_time
                        
                        self.phase = Phase.ESTIMATING_PRECISE_FINISH
                        self.min_coeff = 0
                        self.max_coeff = 1
                        self.coeff = (self.min_coeff + self.max_coeff) / 2

                        self.base_velocity = self.state_before_finish.velocity # velocity on tick before finish
                        self.base_angular_velocity = self.get_angular_velocity(self.state_before_finish)
                        self.rewind_before_finish(iface)
                        
                    else:
                        self.start_new_iteration(iface)
                else:
                    # Save last state before regular game finish
                    self.state_before_finish = iface.get_simulation_state()
                    self.state_before_finish_time = _time + 10

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
        self.set_angular_velocity(self.state_before_finish, [v * self.coeff for v in self.base_angular_velocity])
        iface.rewind_to_state(self.state_before_finish)

    def start_new_iteration(self, iface):
        """Randomize and rewind"""
        self.phase = Phase.WAITING_GAME_FINISH
        self.min_coeff = 0
        self.max_coeff = 1
        self.base_velocity = None
        self.base_angular_velocity = None
        self.finished = False
        self.randomize_inputs()
        self.CP_reached = False
        self.best_coeff = -1
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
        
    def save_result(self, time_found="", file_name="precisecp 1per.txt"):
        if time_found == "":
            time_found = self.time_with_speed_coeff
        # Write inputs in file
        res_file = os.path.expanduser('~/OneDrive/Documents') + "/TMInterface/Scripts/" + file_name
        with open(res_file, "w") as f:
            f.write(f"# Time: {time_found}, iterations: {self.nb_iterations}\n")
            f.write(self.current_buffer.to_commands_str())

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        print(f'Reached checkpoint {current}/{target}')
        
        if current == target_CP:
            self.CP_reached = True
            self.cp_state = self.state_before_finish
            self.cp_time = self.state_before_finish_time
            
            if self.phase == Phase.ESTIMATING_PRECISE_FINISH:
                print(f'Target2 at {self.race_time}')
                self.finished = True
        
        if current == target:
            print(f'Target at {self.race_time}')
            self.finished = True
            iface.prevent_simulation_finish()
    
    def get_angular_velocity(self, state):
        ax = struct.unpack('f', state.dyna[536:540])[0]
        ay = struct.unpack('f', state.dyna[540:544])[0]
        az = struct.unpack('f', state.dyna[544:548])[0]
        return ([ax, ay, az])
    
    def set_angular_velocity(self, state, angular_velocity):
        state.dyna[536:540] = list(struct.pack('f', angular_velocity[0]))
        state.dyna[540:544] = list(struct.pack('f', angular_velocity[1]))
        state.dyna[544:548] = list(struct.pack('f', angular_velocity[2]))


def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""Ideas:
- not rewind to time 0 => rewind to lowest_poss => rewind to 1st change
"""
