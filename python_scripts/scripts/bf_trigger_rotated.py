import math

EVAL_TIME_MIN = 26000
EVAL_TIME_MAX = 26000

MIN_SPEED_KMH = 0
MIN_CP = 0
MIN_WHEELS_ON_GROUND = 0
#GEAR = 0
TRIGGER = [523, 9, 458, 550, 20, 490]
TRIGGER_ANGLE = 45

import math
import numpy
import sys

from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

class CarState():
    def __init__(self) -> None:
        self.time = -1
        self.distance = -1
        self.speed = -1

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller bruteforce')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration
        print(f"Base run time: {self.lowest_time}")
        if not (EVAL_TIME_MIN <= EVAL_TIME_MAX <= self.lowest_time):
            print("ERROR: MUST HAVE 'EVAL_TIME_MIN <= EVAL_TIME_MAX <= REPLAY_TIME'")

        self.last_dist = 0

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        self.curr = CarState()
        self.curr.time = info.time
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING
        
        if self.phase == BFPhase.INITIAL:
            if self.is_eval_time() and self.is_better(iface):
                self.best = self.curr

            if self.is_max_time():
                green_text = f"base at {self.best.time}: {self.best.distance=}, {self.best.speed=}"
                print(green_text)

                if self.best.time > 0:
                    global EVAL_TIME_MAX
                    EVAL_TIME_MAX = min(EVAL_TIME_MAX, self.best.time)

        elif self.phase == BFPhase.SEARCH:
            if self.is_eval_time() and self.is_better(iface):
                response.decision = BFEvaluationDecision.ACCEPT
                        
            if self.is_past_eval_time():
                if response.decision != BFEvaluationDecision.ACCEPT:
                    response.decision = BFEvaluationDecision.REJECT

        return response

    def is_better(self, iface):
        state = iface.get_simulation_state()
        car_speed_kmh = numpy.linalg.norm(state.velocity) * 3.6

        # Conditions
        if MIN_SPEED_KMH > car_speed_kmh:
            return False

        if MIN_CP > get_nb_cp(state):
            return False

        if MIN_WHEELS_ON_GROUND > nb_wheels_on_ground(state):
            return False
        
        # if GEAR != state.scene_mobil.engine.gear:
        #     return False

        #x, y, z = state.position
        #x1, y1, z1, x2, y2, z2 = TRIGGER
        #if not (min(x1,x2) < x < max(x1,x2) and min(y1,y2) < y < max(y1,y2) and min(z1,z2) < z < max(z1,z2)):
        #    return False

        self.curr.distance = self.last_dist
        self.curr.speed = car_speed_kmh
        
        d = distance_to_trigger()
        if d > 0:
            self.last_dist = d
            return False
        
        if self.best.time == -1:
            # Base run (past conditions)
            return True
        
        if self.curr.time < self.best.time or (self.curr.time == self.best.time and self.last_dist < self.best.distance):
            return True
        
        return False

    def is_eval_time(self):
        return EVAL_TIME_MIN <= self.curr.time <= EVAL_TIME_MAX

    def is_past_eval_time(self):
        return EVAL_TIME_MAX <= self.curr.time

    def is_max_time(self):
        return EVAL_TIME_MAX == self.curr.time

def to_rad(deg):
    return deg / 180 * math.pi

def to_deg(rad):
    return rad * 180 / math.pi

def get_nb_cp(state):
    return len([cp_time.time for cp_time in state.cp_data.cp_times if cp_time.time != -1])

def nb_wheels_on_ground(state):
    number = 0
    for wheel in state.simulation_wheels:
        if wheel.real_time_state.has_ground_contact:
            number += 1

    return number

def distance_to_trigger(pos):
    x, y, z = pos
    x1, y1, z1, x2, y2, z2 = TRIGGER

    # change center: trigger point is new 0,0
    x_mid = x - min(x1,x2)
    z_mid = z - min(z1,z2)

    print(x_mid)
    print(z_mid)

    # transpose with target direction
    angle = to_rad(TRIGGER_ANGLE)

    x_new = x_mid * math.cos(angle) - z_mid * math.sin(angle)
    z_new = x_mid * math.sin(angle) + z_mid * math.cos(angle)

    print(x_new)
    print(z_new)

    x_size = max(x1,x2) - min(x1,x2)
    z_size = max(z1,z2) - min(z1,z2)

    # if 0 < x_new < x_size and 0 < z_new < z_size and min(y1,y2) < y < max(y1,y2):
    #     return 0
    
    dist = 0
    if x_new < 0     : dist += abs(x_new)          ** 2
    if x_new > x_size: dist += abs(x_new - x_size) ** 2
    if z_new < 0     : dist += abs(z_new)          ** 2
    if z_new > z_size: dist += abs(z_new - z_size) ** 2
    if y < min(y1,y2): dist += abs(y - min(y1,y2)) ** 2
    if y > min(y1,y2): dist += abs(y - max(y1,y2)) ** 2

    return math.sqrt(dist)


def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
