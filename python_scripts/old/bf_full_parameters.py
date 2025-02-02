
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
    CUSTOM = 0
    TIME = 1
    DISTANCE = 2
    VELOCITY = 3
    DIST_VELO = 4

# What to optimize for
class TriggerShape(IntEnum):
    NONE = 0
    RECTANGLE = 1
    SPHERE = 2
    DIAGONAL = 3

# Compares current iteration's time vs best iteration's time 
class TimeCompare(IntEnum):
    EARLIER = 0
    TIED = 1
    LATER = 2

"""START OF PARAMETERS BLOCK (change this to your needs)"""
eval = Eval.CP
parameter = Optimize.CUSTOM
trigger_shape = TriggerShape.NONE

#eval == Eval.TIME:
TIME_MIN = 22000 # A07 uphill
TIME_MIN = 26130 # A07 finish
TIME_MIN = 87900 # E02 FIN
TIME_MAX = 90300 # E02 FIN
TIME_MAX = TIME_MIN

# eval == Eval.CP:
CP_NUMBER = 2

# parameter == Optimize.DISTANCE:
POINT_POS = [382, 40.5, 143]
POINT_POS = [390, 40.5, 143]
POINT_POS = [689, 44, 269]
POINT_POS = [210, 10, 52] # A12 BUGFIN
POINT_POS = [304, 13, 52.5] # A12 FIN
POINT_POS = [688, 18, 460] # D07 FIN
POINT_POS = [950, 35, 464] # E02 CP 23
POINT_POS = [944, 25, 464] # E02 CP 23
POINT_POS = [369, 25, 464] # E02 CP 24
POINT_POS = [400, 73, 745] # E02 CP 25
POINT_POS = [413, 73, 752] # E02 CP 25
POINT_POS = [413, 73, 753] # E02 CP 25 right
POINT_POS = [740, 40, 652] # NL82
POINT_POS = [944, 73, 940] # E02 FIN
POINT_POS = [956, 71, 941] # E02 FIN
POINT_POS = [931, 72.5, 940] # E02 FIN
POINT_POS = [805, 58, 850] # E02 NB TO FIN

# trigger_shape != TriggerShape.NONE:
TRIGGER = [138.3, 105, 479, 158, 107, 452]
TRIGGER = [417, 112, 734, 447, 96, 704] # A07 diag uphill

# Min diff to consider an improvement worthy
min_diff = 0
"""END OF PARAMETERS BLOCK"""

class MainClient(Client):
    def __init__(self) -> None:
        self.best = -1
        self.time = -1
        self.cp_count = 0
        self.force_accept = False
        self.force_reject = False
        self.phase = BFPhase.INITIAL
        # self.nb_cp = 0

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
        iface.remove_state_validation()
        self.lowest_time = iface.get_event_buffer().events_duration

        if trigger_shape == TriggerShape.DIAGONAL:
            x1, y1, z1, x2, y2, z2 = TRIGGER
            # x = f(z) = az + b car axes TM dans ce sens
            self.diag_slope = (x2-x1) / (z2-z1)
            self.diag_offset = x1 - (z1*self.diag_slope)
            # in trigger = above or below line?
            if z2-z1 > 0:
                self.diag_above = "above"
            else:
                self.diag_above = "below"
            print(f"{self.diag_above=}")

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        if self.phase != info.phase:
            self.cp_count = -1

        self.current_time = info.time
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING

        if self.force_accept:
            print("force_accept STOP")
            response.decision = BFEvaluationDecision.STOP
            # time.sleep(100000)
            return response

        if self.force_reject:
            response.decision = BFEvaluationDecision.REJECT
            return response
        
        if self.phase == BFPhase.INITIAL:
            if self.is_eval_time():
                # print("a")
                state = iface.get_simulation_state()
                car.update(state)
                if self.condition(iface):
                    if self.is_better(state):
                        self.best = self.current
                        self.time = self.current_time

            if self.is_past_eval_time():
                print(f"base at {self.time}: {self.best=}")
            
            # if self.time == -1:
            #     if self.current_time == self.lowest_time - 10:
            #         print("a")
            #         self.cp_count = 0
            # else:
            #     if self.current_time == self.time + 10:
            #         print("b")
            #         self.cp_count = 0

        elif self.phase == BFPhase.SEARCH:
            if self.is_eval_time():
                state = iface.get_simulation_state()
                car.update(state)
                if self.condition(iface):
                    # min_diff = self.best / 100
                    if self.is_better(state, min_diff):
                        response.decision = BFEvaluationDecision.ACCEPT
                        self.cp_count = -1
                    # else:
                    #     print(f"not better at {self.current_time}: {self.current=}")
                        
            if self.is_past_eval_time():
                # print("ab")
                if response.decision != BFEvaluationDecision.ACCEPT:
                    # print("a")
                    response.decision = BFEvaluationDecision.REJECT

                self.cp_count = -1

            # if self.current_time > TIME_MAX:
            #     response.decision = BFEvaluationDecision.REJECT

        return response

    """Returns False if conditions are not met so run is rejected"""
    def condition(self, iface):
        state = iface.get_simulation_state()

        if car.y > 68:
            self.force_reject = True
            return False
            
        # Extra conditions for trigger, but regular conditions still apply
        if not self.trigger_condition(state):
            return False
        
        # if self.cp_count == -1:
        #     self.cp_count = self.get_nb_cp(iface)

        return True
        return car.x < 450
        # return self.cp_count >= 25
        # return self.cp_count >= 25 and abs(car.pitch_deg + 90) < 30
        # return self.cp_count >= 25 and car.y > 73
        return self.cp_count >= 25 and abs(car.pitch_deg - 90) < 30 and car.y > 58 and car.speed_kmh > 450
        return self.cp_count == 23 or self.cp_count == 0 and car.y > 50
        return self.cp_count == 23 or self.cp_count == 0
        return self.cp_count >= 23 and abs(car.pitch_deg - 90) < 30 and abs(car.roll_deg) < 30
        return self.cp_count >= 21 and car.vel_x > 0
        return self.cp_count >= 21 and car.vel_x > 0 and car.vel_z > 0
        return self.cp_count >= 21 and car.speed_kmh > 500 and get_dist_2_points(POINT_POS, state.position) < 4000
        return self.cp_count >= 22 and car.speed_kmh > 500 and abs(car.pitch_deg - 90) < 30 and abs(car.roll_deg) < 30
        return car.x < 450 # A07 uphill

        pos = car.x > 600 and car.y > 40 and car.z < 570
        speed = True
        yaw_pitch_roll = 1.47 < car.pitch_rad < 1.67
        return pos and speed and yaw_pitch_roll
        
    """Returns False if car is not in trigger"""
    def trigger_condition(self, state):
        if trigger_shape == TriggerShape.RECTANGLE:
            x1, y1, z1, x2, y2, z2 = TRIGGER
            if not (min(x1,x2) < car.x < max(x1,x2) and min(y1,y2) < car.y < max(y1,y2) and min(z1,z2) < car.z < max(z1,z2)):
                return False

        elif trigger_shape == TriggerShape.SPHERE:
            x, y, z, radius = TRIGGER
            if get_dist_2_points([x, y, z], state.position) > radius**2:
                return False
                
        elif trigger_shape == TriggerShape.DIAGONAL:
            # Find out if outside of diag trigger is below or above diagonal. At TIME_MIN, car is assumed outside
            # if self.diag_above == "unknown":
            #     self.diag_above = car.is_above_diag(self.diag_slope, self.diag_offset)
            
            # Compare if car is on other side of diagonal (current_time vs MIN_TIME)
            if self.diag_above != car.is_above_diag(self.diag_slope, self.diag_offset):
                return False

        return True

    """Evaluates if the iteration is better when parameter == Optimize.CUSTOM"""
    def is_custom(self, state="", min_diff=0):
        self.current = car.z
        if self.best == -1:
            return True
        return self.current < self.best - min_diff

    """Ultimate goal, forces bruteforce to save the result and stop"""
    def is_force_accept(self):
        # if self.cp_count == -1:
        #     self.cp_count = self.get_nb_cp()
        # return self.cp_count == 25
        return self.cp_count == 25
        return False

    def is_better(self, state, min_diff=0):
        if self.is_force_accept():
            print("force_accept")
            self.force_accept = True
            self.current = 0
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
    
    def is_earlier(self, min_diff=0):
        self.current = self.current_time
        if self.best == -1:
            return True
        return self.compare_time() == TimeCompare.EARLIER
    
    def is_closer(self, state, min_diff=0, axis="xyz"):
        self.current = get_dist_2_points(POINT_POS, state.position, axis)
        # if self.best == -1 and self.current < 40:
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
            # print(self.current_time)
            if TIME_MIN <= self.current_time <= TIME_MAX:
                return True
        if eval == Eval.CP:
            if CP_NUMBER <= self.cp_count:
                return True
        
        return False

    def is_past_eval_time(self):
        if eval == Eval.TIME:
            if self.phase == BFPhase.INITIAL:
                if TIME_MAX == self.current_time:
                    return True
            if self.phase == BFPhase.SEARCH:
                if TIME_MAX <= self.current_time:
                    return True

        if eval == Eval.CP:
            if CP_NUMBER <= self.cp_count:
                self.cp_count = 0
                return True
        
        return False            

    def get_nb_cp(self, iface):
        cp_times = iface.get_checkpoint_state().cp_times
        self.nb_cp = len([time for (time, _) in cp_times if time != -1])
        # print(f"{current} {self.nb_cp=}")
        return len([time for (time, _) in cp_times if time != -1])

    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        self.cp_count = current
        # iface.prevent_simulation_finish()
        # print(f"{current}")

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
    
    def is_above_diag(self, diag_slope, diag_offset):
        diag_x = (self.z*diag_slope) + diag_offset
        if self.x > diag_x:
            return "above"
        
        return "below"


car = Car()

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""
Ideas:
- force_reject
- get_nb_cp to fix bug of nb_cp when no cp is crossed between rewinds
- With trigger, evaluate as soon as trigger is crossed (if not condition, then reject)
- TIME_MAX = self.time for Optimize.TIME and Optimize.DIST_VELO

Done:
- condition() before is_better()
"""
