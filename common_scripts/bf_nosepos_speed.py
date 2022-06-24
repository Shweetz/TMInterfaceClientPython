TIME_MIN = 83200
TIME_MAX = 83250
MIN_SPEED_KMH = 450
MIN_CP = 0
MUST_TOUCH_GROUND = False # True = 1 wheel must not be in air

import math
import numpy
import struct
import sys

from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

class MainClient(Client):
    def __init__(self) -> None:
        self.best = -1
        self.time = -1

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller bruteforce')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration
        print(f"Base run time: {self.lowest_time}")
        if not (TIME_MIN <= self.lowest_time):
            print("ERROR: MUST HAVE 'TIME_MIN <= REPLAY_TIME'")

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

        if MIN_SPEED_KMH > numpy.linalg.norm(state.velocity) * 3.6:
            return False

        if MIN_CP > get_nb_cp(state):
            return False

        if MUST_TOUCH_GROUND and nb_wheels_on_ground(state) == 0:
            return False

        car_yaw, car_pitch, car_roll = state.yaw_pitch_roll

        target_yaw = math.atan2(state.velocity[0], state.velocity[2])
        target_pitch = to_rad(90)
        target_roll = to_rad(0)

        # Customize diff_yaw
        strategy = "any"

        if strategy == "any":
            # any angle
            diff_yaw = to_deg(abs(car_yaw - target_yaw))
            if diff_yaw < 90:
                diff_yaw = 0

        else:
            # define the yaw angle you want in degrees, from -90 to -90
            extra_yaw = 0
            target_yaw += to_rad(extra_yaw)
            diff_yaw = to_deg(abs(car_yaw - target_yaw))

        self.current = diff_yaw + to_deg(abs(car_pitch - target_pitch)) + to_deg(abs(car_roll - target_roll))

        return self.best == -1 or self.current < self.best

    def is_eval_time(self):
        return TIME_MIN <= self.current_time <= TIME_MAX

    def is_past_eval_time(self):
        return TIME_MAX <= self.current_time

    def is_max_time(self):
        return TIME_MAX == self.current_time

def to_rad(deg):
    return deg / 180 * math.pi

def to_deg(rad):
    return rad * 180 / math.pi

def get_nb_cp(state):
    return len([time for (time, _) in state.cp_data.cp_times if time != -1])

def nb_wheels_on_ground(state):
    number = 0
    
    for i in range(4):
        current_offset = (3056 // 4) * i
        hasgroundcontact = struct.unpack('i', state.simulation_wheels[current_offset+292:current_offset+296])[0]
        if hasgroundcontact:
            number += 1

    return number

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
