EVAL_TIME_MIN = 43150
EVAL_TIME_MAX = EVAL_TIME_MIN

MIN_CP = 0

import math
import numpy
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
        if not (EVAL_TIME_MIN <= EVAL_TIME_MAX <= self.lowest_time):
            print("ERROR: MUST HAVE 'EVAL_TIME_MIN <= EVAL_TIME_MAX <= REPLAY_TIME'")

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

        pos_x, pos_y, pos_z = state.position
        vel_x, vel_y, vel_z = state.velocity
        yaw_rad, pitch_rad, roll_rad = state.yaw_pitch_roll
        speed_kmh = numpy.linalg.norm(state.velocity) * 3.6

        if MIN_CP > get_nb_cp(state):
            return False

        self.current = speed_kmh
        #self.current = ((vel_x ** 2 + vel_z ** 2) ** 0.5) * 3.6

        return self.best == -1 or self.current > self.best

    def is_eval_time(self):
        return EVAL_TIME_MIN <= self.current_time <= EVAL_TIME_MAX

    def is_past_eval_time(self):
        return EVAL_TIME_MAX <= self.current_time

    def is_max_time(self):
        return EVAL_TIME_MAX == self.current_time

def get_nb_cp(state):
    return len([cp_time.time for cp_time in state.cp_data.cp_times if cp_time.time != -1])

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
