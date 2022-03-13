from dataclasses import dataclass
from enum import IntEnum, Enum
import math
import numpy
import struct

from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME, BINARY_RESPAWN_NAME
from tminterface.constants import SIMULATION_WHEELS_SIZE

class Input(Enum):
    UP___ = BINARY_ACCELERATE_NAME
    DOWN_ = BINARY_BRAKE_NAME
    # LEFT_ = BINARY_LEFT_NAME
    # RIGHT = BINARY_RIGHT_NAME
    # RESPAWN=BINARY_RESPAWN_NAME
    STEER = ANALOG_STEER_NAME

class Change(IntEnum):
    STEER_ = 0
    TIMING = 1
    CREATE = 2
    AVG_REBRUTE = 3

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

class MinMax(IntEnum):
    MIN = 0
    MAX = 1


@dataclass
class Rule:
    input : str
    change_type : Change
    proba : float
    start_time : str
    end_time : str
    diff : int

    def init(self):
        self.start_time = int(sec_to_ms(self.start_time))
        self.end_time = int(sec_to_ms(self.end_time))

    def __str__(self):
        start = ms_to_sec(self.start_time)
        end = ms_to_sec(self.end_time)
        return f"rule: From {start} to {end}, change {self.change_type.name} for {self.input} with max diff of {self.diff} and modify_prob={self.proba}"


@dataclass
class Car():
    _time : int

    def update(self, state):
        self.state = state
        
        self.position = state.position
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

    @property
    def nb_wheels_on_ground(self):
        number = 0
        
        for i in range(4):
            current_offset = (SIMULATION_WHEELS_SIZE // 4) * i
            hasgroundcontact = struct.unpack('i', self.state.simulation_wheels[current_offset+292:current_offset+296])[0]
            if hasgroundcontact:
                number += 1

        return number

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


@dataclass
class Goal():
    variable : str
    should_max : MinMax
    accept : int

    def achieved(self, car):
        """
        Checks if goal is achieved. Examples: 
        Goal('x', True, 50)        is achieved if car.x > 50
        Goal('_time', False, 4390) is achieved if car._time < 4390
        """
        if self.should_max == MinMax.MAX:
            if getattr(car, self.variable) > self.accept:
                return True
        else:
            if getattr(car, self.variable) < self.accept:
                return True
        return False
    
    def closer(self, car, best_car, min_diff=0):
        """Checks if car is closer to goal than best_car"""
        if self.should_max:
            if getattr(car, self.variable) > getattr(best_car, self.variable) + min_diff:
                return True
        else:
            if getattr(car, self.variable) < getattr(best_car, self.variable) - min_diff:
                return True
        return False


def get_dist_2_points(pos1, pos2, axis="xyz"):
    dist = 0
    if "x" in axis:
        dist += (pos2[0]-pos1[0]) ** 2
    if "y" in axis:
        dist += (pos2[1]-pos1[1]) ** 2
    if "z" in axis:
        dist += (pos2[2]-pos1[2]) ** 2
    return dist

def sec_to_ms(line_time: str) -> str:
    """Converter sec->ms for time value
    Example: '12:43.90' -> '763900'
    """
    if type(line_time) == int:
        line_time = str(line_time)

    splits = line_time.replace(":", ".").split(".")
    
    hours = 0
    minutes = 0

    if len(splits) == 1:
        return line_time
    elif len(splits) == 2:
        seconds = splits[0]
        milliseconds = splits[1]
    elif len(splits) == 3:
        minutes = splits[0]
        seconds = splits[1]
        milliseconds = splits[2]
    elif len(splits) == 4:
        hours = splits[0]
        minutes = splits[1]
        seconds = splits[2]
        milliseconds = splits[3]
        
    while len(milliseconds) < 3:
        milliseconds += "0"

    # print(hours)
    # print(minutes)
    # print(seconds)
    # print(milliseconds)        
    
    return str(int(hours) * 3_600_000 + int(minutes) * 60000 + int(seconds) * 1000 + int(milliseconds))
        
def ms_to_sec(line_time: str) -> str:
    """Converter ms->sec for time value
    Example: '763900' -> '12:43.90'
    """
    if type(line_time) == int:
        line_time = str(line_time)

    if "." in line_time or line_time == "0":
        return line_time

    minutes, milliseconds = divmod(int(line_time), 60 * 1000)
    hours, minutes = divmod(minutes, 60)
    seconds = milliseconds / 1000

    value = ""    
    if hours > 0:
        value += str(hours) + ":"
    if minutes > 0 or hours > 0:
        value += str(minutes) + ":"
    value += f"{seconds:.2f}"

    return value

def to_rad(deg):
    return deg / 180 * math.pi

def to_deg(rad):
    return rad * 180 / math.pi

def add_events_in_buffer(events, buffer):
    """
    events: list of Event
    buffer: EventBufferData (buffer.control_names must be filled)
    """
    # print(buffer.control_names)
    for event in events:
        if event.name_index > len(buffer.control_names):
            # print(event.name_index)
            pass
        else:
            # print(event.name_index)
            event_time = event.time - 100010
            event_name = buffer.control_names[event.name_index]
            event_value = event.analog_value if "analog" in event_name else event.binary_value
            buffer.add(event_time, event_name, event_value)
    