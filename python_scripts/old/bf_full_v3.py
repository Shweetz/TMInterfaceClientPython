
from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

from enum import IntEnum
import math
import numpy
import sys
import time

# Eval time: CP if optimizing CP, else use a shorter time frame for slightly faster bf
class Eval(IntEnum):
    TIME = 0
    CP = 1

# What to optimize for
class Optimize(IntEnum):
    CUSTOM = -1
    TIME = 0
    DISTANCE = 1
    VELOCITY = 2
    DIST_VELO = 3

# Compares current iteration's time vs best iteration's time 
class TimeCompare(IntEnum):
    EARLIER = 0
    TIED = 1
    LATER = 2

"""START OF PARAMETERS BLOCK (change this to your needs)"""
eval = Eval.TIME
parameter = Optimize.VELOCITY

if eval == Eval.TIME:
    TIME_MIN = 65000
    TIME_MAX = 65500
    TIME_MAX = TIME_MIN
if eval == Eval.CP:
    CP_NUMBER = 1

if parameter == Optimize.DISTANCE:
    POINT_POS = [382, 40.5, 143]
    POINT_POS = [390, 40.5, 143]

# Use trigger ?
USE_TRIGGER = False
TRIGGER = [496.91, 86.275, 288.92, 490.42, 89.482, 283.21]

# Min diff to consider an improvement worthy
min_diff = 1
"""END OF PARAMETERS BLOCK"""

class MainClient(Client):
    def __init__(self) -> None:
        self.best = -1
        self.time = -1
        self.cp_count = 0
        self.force_accept = False
        self.phase = BFPhase.INITIAL

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    # def on_run_step(self, iface, _time):
    #     x1, y1, z1, x2, y2, z2 = TRIGGER
    #     # z = f(x) = ax + b
    #     self.diag_slope = (x2-x1) / (z2-z1)
    #     self.diag_offset = x1 - (z1*self.diag_slope)
    #     if z2-z1 > 0:
    #         self.diag_above = "above"
    #     else:
    #         self.diag_above = "below"
    #     state = iface.get_simulation_state()
    #     car.update(state)
    #     a = car.is_above_diag(self.diag_slope, self.diag_offset)
    #     print(f"{self.diag_above=}, {a}")

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        self.current_time = info.time
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING

        if self.force_accept:
            print("force_accept STOP")
            response.decision = BFEvaluationDecision.STOP
            # time.sleep(100000)
        
        if self.phase == BFPhase.INITIAL:
            if self.is_eval_time():
                state = iface.get_simulation_state()
                car.update(state)
                if self.condition(state):
                    if self.is_better(state):
                        self.best = self.current
                        self.time = self.current_time

            if self.is_past_eval_time():
                print(f"base at {self.time}: {self.best=}")
                self.cp_count = 0

        elif self.phase == BFPhase.SEARCH:
            if self.is_eval_time():
                state = iface.get_simulation_state()
                car.update(state)
                if self.condition(state):
                    if self.is_better(state, min_diff):
                        response.decision = BFEvaluationDecision.ACCEPT
                # else:
                    # print(f"not better at {self.current_time}: {self.current=}")
                        
            if self.is_past_eval_time():
                if response.decision != BFEvaluationDecision.ACCEPT:
                    response.decision = BFEvaluationDecision.REJECT

                self.cp_count = 0

        return response

    """Returns False if conditions are not met so run is rejected"""
    def condition(self, state):
        # Extra conditions for trigger, but regular conditions still apply
        if USE_TRIGGER:
            # Cube trigger
            if len(TRIGGER) == 6:
                x1, y1, z1, x2, y2, z2 = TRIGGER
                if not (min(x1,x2) < car.x < max(x1,x2) and min(y1,y2) < car.y < max(y1,y2) and min(z1,z2) < car.z < max(z1,z2)):
                    return False

            # Sphere trigger
            if len(TRIGGER) == 4:
                x, y, z, radius = TRIGGER
                if get_dist_2_points([x, y, z], state.position) > radius**2:
                    return False

        return self.cp_count >= 18

        pos = car.x > 600 and car.y > 40 and car.z < 570
        speed = True
        yaw_pitch_roll = 1.47 < car.pitch_rad < 1.67
        return pos and speed and yaw_pitch_roll
        
    """Evaluates if the iteration is better when parameter == Optimize.CUSTOM"""
    def is_custom(self, state="", min_diff=0):
        self.current = car.y
        if self.best == -1:
            return True
        return self.current < self.best + min_diff

    def is_better(self, state, min_diff=0):
        if self.is_force_accept():
            print("force_accept")
            self.force_accept = True
            return True
        
        if parameter == Optimize.TIME:
            return self.is_earlier(min_diff)

        if parameter == Optimize.DISTANCE:
            return self.is_closer(state, min_diff)

        if parameter == Optimize.VELOCITY:
            if self.best < 999:
                return self.is_faster(min_diff)
            else:
                # Add condition to differenciate equal 1000 speed
                return car.speed_kmh(state) > 999 and self.is_earlier()

        if parameter == Optimize.DIST_VELO:
            return self.is_earlier_or_faster(min_diff)

        if parameter == Optimize.CUSTOM:
            return self.is_custom(state, min_diff)

        return False

    def is_force_accept(self):
        # return self.cp_count >= 18
        return False
    
    def is_earlier(self, min_diff=0):
        self.current = self.current_time
        if self.best == -1:
            return True
        return self.compare_time() == TimeCompare.EARLIER
    
    def is_closer(self, state, min_diff=0, axis="xyz"):
        self.current = get_dist_2_points(POINT_POS, state.position, axis)
        if self.best == -1:
            return True
        return self.current < self.best - min_diff
        
    def is_faster(self, min_diff=0):
        self.current = min(car.speed_kmh, 1000)
        if self.best == -1:
            return True
        return self.current > self.best + min_diff

    def is_earlier_or_faster(self, min_diff):
        self.current = car.speed_kmh
        if self.compare_time() == TimeCompare.EARLIER:
            return True
        if self.compare_time() == TimeCompare.LATER:
            return False
        return self.is_faster(min_diff)
    
    def is_further(self, state, min_diff=0, axis="xyz"):
        self.current = get_dist_2_points(POINT_POS, state.position, axis)
        if self.best == -1:
            return True
        return self.current > self.best + min_diff
    
    def compare_time(self) -> TimeCompare:
        if self.time == -1:
            return TimeCompare.EARLIER
        if self.current_time < self.time:
            return TimeCompare.EARLIER
        if self.current_time == self.time:
            return TimeCompare.TIED
        else:
            return TimeCompare.LATER

    def is_eval_time(self):
        if eval == Eval.TIME:
            if TIME_MIN <= self.current_time <= TIME_MAX:
                return True
        if eval == Eval.CP:
            if CP_NUMBER <= self.cp_count:
                return True
        
        return False

    def is_past_eval_time(self):
        if eval == Eval.TIME:
            if self.current_time == TIME_MAX:
                return True
        if eval == Eval.CP:
            if CP_NUMBER <= self.cp_count:
                self.cp_count = 0
                return True
        
        return False
            
    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        self.cp_count = current

def get_dist_2_points(pos1, pos2, axis="xyz"):
    dist = 0
    if "x" in axis:
        dist += (pos2[0]-pos1[0]) ** 2
    if "y" in axis:
        dist += (pos2[1]-pos1[1]) ** 2
    if "z" in axis:
        dist += (pos2[2]-pos1[2]) ** 2
    return dist

class Car():
    def update(self, state):
        self.position = state.position
        self.x, self.y, self.z = state.position
        self.yaw_rad, self.pitch_rad, self.roll_rad = state.yaw_pitch_roll
        self.vel_x, self.vel_y, self.vel_z = state.velocity
        self.speed_mph = numpy.linalg.norm(state.velocity) # if > 1000/3.6?

        self.yaw_deg   = self.yaw_rad   * 180 / math.pi
        self.pitch_deg = self.pitch_rad * 180 / math.pi
        self.roll_deg  = self.roll_rad  * 180 / math.pi
        self.speed_kmh = self.speed_mph * 3.6 # if > 1000?

car = Car()

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""Ideas:
- condition() before is_better()
- TIME_MAX = self.time for Optimize.TIME and Optimize.DIST_VELO
"""
