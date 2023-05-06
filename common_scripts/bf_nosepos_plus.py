EVAL_TIME_MIN = 26000
EVAL_TIME_MAX = 26000
NEXT_EVAL = "time" # "none"/"speed"/"point"/"time"
#POINT = [523, 9, 458]
GOOD_NOSEPOS_DEG = 10

MIN_SPEED_KMH = 0
MIN_CP = 0
MIN_WHEELS_ON_GROUND = 0
#GEAR = 0
#TRIGGER = [523, 9, 458, 550, 20, 490]

import math
import numpy
import sys

from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

class CarState():
    def __init__(self) -> None:
        self.time = -1
        self.angle = -1
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
        
        if NEXT_EVAL != "point":
            global POINT
            POINT = [0, 0, 0]

        self.best = CarState()

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
                green_text = f"base at {self.best.time}: {self.best.angle=}"
                if   NEXT_EVAL == "point": green_text += f", {self.best.distance=}"
                elif NEXT_EVAL == "speed": green_text += f", {self.best.speed=}"                
                print(green_text)

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

        car_yaw   = to_deg(state.yaw_pitch_roll[0])
        car_pitch = to_deg(state.yaw_pitch_roll[1])
        car_roll  = to_deg(state.yaw_pitch_roll[2])

        target_yaw   = to_deg(math.atan2(state.velocity[0], state.velocity[2]))
        target_pitch = 90
        target_roll  = 0

        diff_yaw = abs(car_yaw - target_yaw)
        diff_yaw = max(diff_yaw - 90, 0) # [-90; 90]° yaw is ok to nosebug, so 100° should only add 10°

        self.curr.angle = diff_yaw + abs(car_pitch - target_pitch) + abs(car_roll - target_roll)
        self.curr.distance = distance_to_point(state.position)
        self.curr.speed = car_speed_kmh
        
        if self.best.time == -1:
            # Base run (past conditions)
            return True
        
        if self.best.angle < GOOD_NOSEPOS_DEG and self.curr.angle < GOOD_NOSEPOS_DEG:
            # Best and current have a good angle, now check next eval
            if NEXT_EVAL == "point":
                return self.curr.distance < self.best.distance
            
            if NEXT_EVAL == "speed":
                return self.curr.speed > self.best.speed
            
            if NEXT_EVAL == "time":
                return self.curr.time < self.best.time
        
        return self.curr.angle < self.best.angle

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

def distance_to_point(pos):
    return (pos[0]-POINT[0]) ** 2 + (pos[1]-POINT[1]) ** 2 + (pos[2]-POINT[2]) ** 2

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
