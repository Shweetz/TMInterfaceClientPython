EVAL_TIME_MIN = 32500

import math
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
        if not (EVAL_TIME_MIN <= self.lowest_time):
            print("ERROR: MUST HAVE 'EVAL_TIME_MIN <= EVAL_TIME_MAX <= REPLAY_TIME'")

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING

        if EVAL_TIME_MIN == info.time:
            if self.is_better(iface):
                response.decision = BFEvaluationDecision.ACCEPT
                self.best = self.current
                print(f"base at {EVAL_TIME_MIN}: {self.best=}")
            else:
                response.decision = BFEvaluationDecision.REJECT

        return response

    def is_better(self, iface):
        state = iface.get_simulation_state()

        car_yaw, car_pitch, car_roll = state.yaw_pitch_roll

        target_yaw = math.atan2(state.velocity[0], state.velocity[2])
        target_pitch = to_rad(90)
        target_roll = to_rad(0)

        self.current = to_deg(abs(car_yaw - target_yaw) + abs(car_pitch - target_pitch) + abs(car_roll - target_roll))

        return self.best == -1 or self.current < self.best

def to_rad(deg):
    return deg / 180 * math.pi

def to_deg(rad):
    return rad * 180 / math.pi

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
