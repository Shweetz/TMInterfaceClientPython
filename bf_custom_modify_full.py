
from dataclasses import dataclass
from enum import IntEnum
import math
import numpy
import os
import random
import struct
import sys
import time
import pickle

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME, BINARY_RESPAWN_NAME
from commandlist import CommandList, InputCommand, InputType
# import load_state

# class Input(IntEnum):
#     UP = BINARY_ACCELERATE_NAME
#     DOWN = BINARY_BRAKE_NAME
#     STEER = ANALOG_STEER_NAME

class ChangeType(IntEnum):
    STEER_DIFF = 0
    TIMING = 1
    AVG_REBRUTE = 2
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

class Eval(IntEnum):
    """Eval time: CP if optimizing CP, else use a shorter time frame for slightly faster bf"""
    TIME = 0
    CP = 1

class Optimize(IntEnum):
    """What to optimize for"""
    CUSTOM = 0
    TIME = 1
    DISTANCE = 2
    VELOCITY = 3
    DIST_VELO = 4

"""START OF PARAMETERS (you can change here)"""
rules = []
# Examples
# rules.append(Change(0.02, 10000, 12000, Input.UP, ChangeType.TIMING, 50))
# rules.append(Change(0.1, 0, 100, Input.DOWN, ChangeType.CREATE_REMOVE, 0))
# rules.append(Change(Input.STEER, ChangeType.STEER_DIFF,     proba=0.01, start_time=40000, end_time=42880, diff=65536))

# A-0
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,     proba=1, start_time=0, end_time=4390, diff=100))

# A07
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=0.02,   start_time=22600, end_time=26160, value=15000))

# TODO
# rules.append(Change(ANALOG_STEER_NAME, ChangeType.AVG_REBRUTE, proba=0, start_time=4000, end_time=8000, diff=5000))

# Decimation CP 41 10:16.25
# Cette règle fait que tes steer changent en steer + ou -
rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF,  proba=0.05, start_time=613000, end_time=617000, diff=65536))

# Cette règle fait que tes steer changent de timing (comme TMI)
rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,      proba=0, start_time=613000, end_time=617000, diff=50))

# Cette règle fait que tes press up/down changent de timing (comme TMI)
rules.append(Change(BINARY_ACCELERATE_NAME, ChangeType.TIMING, proba=0, start_time=613000, end_time=617000, diff=50))
rules.append(Change(BINARY_BRAKE_NAME, ChangeType.TIMING,      proba=0, start_time=613000, end_time=617000, diff=50))

PRECISION = 0.000001
FILL_INPUTS = True
LOCK_BASE_RUN = False
LOAD_INPUTS_FROM_FILE = False
LOAD_REPLAY_FROM_STATE = False

# steer_cap_accept = True
steer_equal_last_input_proba = 0
steer_zero_proba = 0 # proba to randomize steer to 0 instead of changing direction left/right

# From previous script
eval = Eval.CP
parameter = Optimize.CUSTOM

TIME_MIN = 10000
TIME_MAX = 10000

# eval == Eval.CP:
CP_NUMBER = 1

# parameter == Optimize.DISTANCE:
POINT_POS = [497, 25, 80]

# Min diff to consider an improvement worthy
min_diff = 0
min_diff_frac = 0
"""END OF PARAMETERS"""

# Files stuff

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
        self.cp_count = 0
        self.car = None
        # self.best_state = None
        self.best_car = None
        self.pre_rewind_buffer = None

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        print(f"Randomizing inputs between {lowest_poss_change} and {highest_poss_change}")
        for rule in rules:
            print(rule)

    def on_simulation_begin(self, iface):
        iface.remove_state_validation()

        # Fill begin_buffer
        self.begin_buffer = iface.get_event_buffer()
        self.pre_rewind_buffer = iface.get_event_buffer()
        if LOAD_INPUTS_FROM_FILE:
            self.load_inputs_from_file()
            # iface.set_event_buffer(self.begin_buffer) # COMMENT FOR PARTIAL BUFFER
        if FILL_INPUTS:
            self.fill_inputs(lowest_poss_change, highest_poss_change)

        self.lowest_time = self.begin_buffer.events_duration

        self.current_buffer = self.begin_buffer.copy() # copy avoids timeout?
        print(self.begin_buffer.to_commands_str())

        # Load state
        if LOAD_REPLAY_FROM_STATE:
            file_name = "../States/state.bin"
            self.state_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + file_name
            # self.state_min_change = load_state.load_state(self.state_file)
            self.state_min_change = pickle.load(open(self.state_file, "rb"))
            iface.rewind_to_state(self.state_min_change)
        
    def fill_inputs(self, start_fill=0, end_fill=0):
        """Fill inputs between start_fill and end_fill included"""
        if end_fill == 0:
            end_fill = self.begin_buffer.events_duration
            
        curr_steer = 0
        for event_time in range(start_fill, end_fill+10, 10):
            events_at_time = self.begin_buffer.find(time=event_time, event_name=ANALOG_STEER_NAME)
            if len(events_at_time) > 0:
                curr_steer = events_at_time[-1].analog_value
            else:
                self.begin_buffer.add(event_time, ANALOG_STEER_NAME, curr_steer)
        
    def on_simulation_step(self, iface: TMInterface, _time: int):
        self.race_time = _time
        if not self.state_min_change:
            if self.race_time % 10000 == 0:
                sys.stdout.write(f"\rSimulating base run... {int(self.race_time/1000)}sec")
                sys.stdout.flush()
            # if self.race_time == self.lowest_time:
            #     print()

            if self.race_time == lowest_poss_change:
                # Store state to rewind to for every iteration, for now it is earliest possible input change
                # - 10 because 1 tick is needed to apply inputs in physics?
                self.state_min_change = iface.get_simulation_state()
                file_name = "../States/state.bin"
                self.state_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + file_name
                pickle.dump(self.state_min_change, open(self.state_file, "wb"))

        if self.is_eval_time():
            # print("eval_time")
            state = iface.get_simulation_state()
            # state.timee = _time
            if self.is_better(state):
                # self.best_state = state
                self.best_car = self.car
                
                if self.nb_iterations == 0:
                    print() # after write/flush
                    print(f"base = {_time}")
                else:
                    print(f"FOUND IMPROVEMENT: {_time}")
                    if not LOCK_BASE_RUN:
                        self.begin_buffer.events = self.current_buffer.events
                
                    # Save inputs to file
                    self.save_result()

        # Wait until the end of eval time before rewinding, in case an even better state is found later on
        if self.is_past_eval_time():
            # print("past eval_time")
            self.start_new_iteration(iface)

    def is_better(self, state):
        self.car = Car(self.race_time)
        self.car.update(state)

        if not self.condition(state):
            return False

        # Calculate & print for base car on next iteration with condition True
        if not self.best_car:
            ret = True
            
        if parameter == Optimize.TIME:
            if self.car._time < self.best_car._time:
                return True

        if parameter == Optimize.DISTANCE:
            return self.is_closer(min_diff)

        if parameter == Optimize.VELOCITY:
            return self.is_faster(min_diff)

        if parameter == Optimize.CUSTOM:
            return self.is_custom(min_diff)

        return ret

    def is_custom(self, state="", min_diff=0):
        """Evaluates if the iteration is better when parameter == Optimize.CUSTOM"""
        if not self.best_car.custom:
            self.best_car.custom = get_dist_2_points(POINT_POS, self.best_car.state.position, axis)
            print(f"Base run distance = {math.sqrt(self.best_car.distance)}")
        self.current = abs(car.pitch_deg - 90)
        self.current = car.z
        # self.current = get_dist_2_points(POINT_POS, state.position, "xz")
        # self.current = car.get_speed("xz")
        if self.best == -1:
            return True
        return self.current < self.best + min_diff
    
    def is_closer(self, min_diff=0, axis="xyz"):
        if not self.best_car.distance:
            self.best_car.distance = get_dist_2_points(POINT_POS, self.best_car.state.position, axis)
            print(f"Base run distance = {math.sqrt(self.best_car.distance)}")

        self.car.distance = get_dist_2_points(POINT_POS, self.car.state.position, axis)
        if self.car.distance < self.best_car.distance - min_diff:
            print(f"Improved distance = {math.sqrt(self.best_car.distance)}")
            return True
        
        return False
        
    def is_faster(self, min_diff=0):
        if not self.best_car.velocity:
            self.best_car.velocity = min(self.best_car.speed_kmh, 1000)
            print(f"Base run velocity = {self.best_car.velocity}")

        self.car.velocity = min(self.car.speed_kmh, 1000)
        if self.car.velocity > self.best_car.velocity + min_diff:
            print(f"Improved velocity = {self.car.velocity}")
            return True
        
        return False

    def condition(self):
        """Returns False if conditions are not met so run is rejected"""
        return True
        return self.car.y > 25

    def is_eval_time(self):
        if eval == Eval.TIME:
            # print(self.current_time)
            if TIME_MIN <= self.current_time <= TIME_MAX:
                return True
        if eval == Eval.CP:
            if CP_NUMBER <= self.cp_count or self.race_time > highest_poss_change:
                return True
        
        return False

    def is_past_eval_time(self):
        if eval == Eval.TIME:
            if TIME_MAX <= self.current_time:
                return True

        if eval == Eval.CP:
            if CP_NUMBER <= self.cp_count or (self.best_car and self.race_time == self.best_car._time):
                # self.cp_count = 0
                return True
        
        return False

    def start_new_iteration(self, iface):
        # print("start_new_iteration")
        """Randomize and rewind"""
        self.randomize_inputs()
        iface.set_event_buffer(self.current_buffer)

        if not self.state_min_change:
            print("no self.state_min_change to rewind to")
            sys.exit()
        iface.rewind_to_state(self.state_min_change)

        self.cp_count = self.get_nb_cp(iface)
        # print(f"{self.cp_count=}")
        self.nb_iterations += 1
        if self.nb_iterations <= 5 or self.nb_iterations % 1000 == 0:
            print(f"{self.nb_iterations=}")

    def randomize_inputs(self):
        """Restore base run events (with deepcopy) and randomize them using rules.
        Deepcopy can't use EventBufferData.copy() because events is deepcopied but not the individual events"""
        
        # Restore events from base run (self.begin_buffer.events) in self.current_buffer.events using deepcopy
        self.current_buffer.clear()
        for event in self.begin_buffer.events:
            event_time = event.time - 100010
            # if event_time >= lowest_poss_change:
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
            time_found = self.race_time
        # Write inputs in file
        res_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + file_name
        with open(res_file, "w") as f:
            f.write(f"# Time: {time_found}, iterations: {self.nb_iterations}\n")
            if self.pre_rewind_buffer:
                # print inputs before inputs_min_time
                f.write(self.pre_rewind_buffer.to_commands_str())
            f.write(self.current_buffer.to_commands_str())

    def load_inputs_from_file(self, file_name="inputs.txt"):
        # Clear and re-fill the buffer (to keep control_names and event_duration: worth?)
        self.begin_buffer.clear()
        self.pre_rewind_buffer.clear()

        inputs_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + file_name
        cmdlist = CommandList(open(inputs_file, 'r'))
        commands = [cmd for cmd in cmdlist.timed_commands if isinstance(cmd, InputCommand)]

        for command in commands:
            if command.input_type == InputType.UP: command.input = BINARY_ACCELERATE_NAME
            elif command.input_type == InputType.DOWN: command.input = BINARY_BRAKE_NAME
            elif command.input_type == InputType.LEFT: command.input = BINARY_LEFT_NAME
            elif command.input_type == InputType.RIGHT: command.input = BINARY_RIGHT_NAME
            elif command.input_type == InputType.RESPAWN: command.input = BINARY_RESPAWN_NAME
            elif command.input_type == InputType.STEER: command.input = ANALOG_STEER_NAME
            else: print(f"{command.input_type=}"); continue

            if command.timestamp < lowest_poss_change:
                self.pre_rewind_buffer.add(command.timestamp, command.input, command.state)
            else:
                self.begin_buffer.add(command.timestamp, command.input, command.state)
        # for event_time in range(start_fill, end_fill+10, 10):
        #     events_at_time = self.begin_buffer.find(time=event_time, event_name=ANALOG_STEER_NAME)
        #     if len(events_at_time) > 0:
        #         curr_steer = events_at_time[-1].analog_value
        #     else:
        #         self.begin_buffer.add(event_time, ANALOG_STEER_NAME, curr_steer)
        # return 

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        self.cp_count = current
        # if current == CP_NUMBER:
        #     print(current)
        # print(f'Reached checkpoint {current}/{target}')
        # if current == target:
        #     # print(f'Finished the race at {self.race_time}')
        #     self.finished = True
        #     iface.prevent_simulation_finish()

    def get_nb_cp(self, iface):
        cp_times = iface.get_checkpoint_state().cp_times
        self.nb_cp = len([time for (time, _) in cp_times if time != -1])
        # print(f"{current} {self.nb_cp=}")
        return len([time for (time, _) in cp_times if time != -1])
    
    def get_angular_velocity(self, state):
        ax = struct.unpack('f', state.dyna[536:540])[0]
        ay = struct.unpack('f', state.dyna[540:544])[0]
        az = struct.unpack('f', state.dyna[544:548])[0]
        return ([ax, ay, az])
    
    def set_angular_velocity(self, state, angular_velocity):
        state.dyna[536:540] = list(struct.pack('f', angular_velocity[0]))
        state.dyna[540:544] = list(struct.pack('f', angular_velocity[1]))
        state.dyna[544:548] = list(struct.pack('f', angular_velocity[2]))

def get_dist_2_points(pos1, pos2, axis="xyz"):
    dist = 0
    if "x" in axis:
        dist += (pos2[0]-pos1[0]) ** 2
    if "y" in axis:
        dist += (pos2[1]-pos1[1]) ** 2
    if "z" in axis:
        dist += (pos2[2]-pos1[2]) ** 2
    return dist

@dataclass
class Car():
    _time : int

    def update(self, state):
        self.state = state
        
        self.x, self.y, self.z = state.position
        self.yaw_rad, self.pitch_rad, self.roll_rad = state.yaw_pitch_roll
        self.vel_x, self.vel_y, self.vel_z = state.velocity
        self.speed_mph = numpy.linalg.norm(state.velocity) # if > 1000/3.6?

        self.yaw_deg   = self.yaw_rad   * 180 / math.pi
        self.pitch_deg = self.pitch_rad * 180 / math.pi
        self.roll_deg  = self.roll_rad  * 180 / math.pi
        self.speed_kmh = self.speed_mph * 3.6 # if > 1000?

        self.stunts_score = int.from_bytes(state.player_info[724:724+4], byteorder='little')
        if self.stunts_score > 1000000:
            self.stunts_score = 0

    def get_speed(self, axis="xz"):
        return self.get_vel(axis) * 3.6

    def get_vel(self, axis="xz"):
        ret = 0
        if "x" in axis:
            ret += self.vel_x ** 2
        if "y" in axis:
            ret += self.vel_y ** 2
        if "z" in axis:
            ret += self.vel_z ** 2
        return ret ** 0.5

    # def has_at_least_1_wheel_in_air(self):
    #     wheel_size = SIMULATION_WHEELS_SIZE // 4
        
    #     for i in range(4):
    #         current_offset = wheel_size * i
    #         hasgroundcontact = struct.unpack('i', self.state.simulation_wheels[current_offset+292:current_offset+296])[0]
    #         if hasgroundcontact == 0:
    #             return True

    #     return False
    
    # def is_above_diag(self, diag_slope, diag_offset):
    #     diag_x = (self.z*diag_slope) + diag_offset
    #     if self.x > diag_x:
    #         return "above"
        
    #     return "below"

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""Ideas:
- not rewind to time 0 => rewind to lowest_poss => rewind to 1st change
"""
