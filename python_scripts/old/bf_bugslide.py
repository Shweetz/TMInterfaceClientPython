EVAL_TIME_MIN = 7500
EVAL_TIME_MAX = 7500
BUGSLIDE = "auto" # "auto"/"left"/"right"

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

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller bruteforce')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration
        print(f"Base run time: {self.lowest_time}")
        if not (EVAL_TIME_MIN <= EVAL_TIME_MAX <= self.lowest_time):
            print("ERROR: MUST HAVE 'EVAL_TIME_MIN <= EVAL_TIME_MAX <= REPLAY_TIME'")
            
        self.best = -1
        self.time = -1

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        self.current_time = info.time
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING
        
        if self.phase == BFPhase.INITIAL:
            if self.is_eval_time() and self.is_better(iface):
                self.best = self.current
                self.time = self.current_time

            if self.is_max_time():
                print(f"base at {self.time}: {self.best=}")

        elif self.phase == BFPhase.SEARCH:
            if self.is_eval_time() and self.is_better(iface):
                response.decision = BFEvaluationDecision.ACCEPT
                        
            if self.is_past_eval_time():
                if response.decision != BFEvaluationDecision.ACCEPT:
                    response.decision = BFEvaluationDecision.REJECT

        return response

    def is_better(self, iface):
        state = iface.get_simulation_state()

        # Conditions
        if MIN_SPEED_KMH > numpy.linalg.norm(state.velocity) * 3.6:
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
        target_pitch = 0
        target_roll  = 0
        
        diff_yaw_left  = abs(car_yaw - (target_yaw + 90))
        diff_yaw_right = abs(car_yaw - (target_yaw - 90))

        if   BUGSLIDE == "left":  diff_yaw = diff_yaw_left
        elif BUGSLIDE == "right": diff_yaw = diff_yaw_right
        else:                     diff_yaw = min(diff_yaw_left, diff_yaw_right)

        self.current = diff_yaw + abs(car_pitch - target_pitch) + abs(car_roll - target_roll)

        return self.best == -1 or self.current < self.best

    def is_eval_time(self):
        return EVAL_TIME_MIN <= self.current_time <= EVAL_TIME_MAX

    def is_past_eval_time(self):
        return EVAL_TIME_MAX <= self.current_time

    def is_max_time(self):
        return EVAL_TIME_MAX == self.current_time

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

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
