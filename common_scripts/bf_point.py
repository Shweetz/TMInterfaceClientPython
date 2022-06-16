TIME_MIN = 32500
TIME_MAX = TIME_MIN

POINT = [816, 64, 464]

import numpy
from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

import sys

class MainClient(Client):
    def __init__(self) -> None:
        self.best = -1
        self.time = -1

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration
        print(f"Base run time: {self.lowest_time}")
        if not (TIME_MIN <= TIME_MAX <= self.lowest_time):
            print("ERROR: MUST HAVE 'TIME_MIN <= TIME_MAX <= REPLAY_TIME'")

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
        pos = state.position
        speed = numpy.linalg.norm(state.velocity)

        # Conditions
        if get_nb_cp(state) < 3:
            return False
        if speed < 450:
            return False
        if pos[0] < 500 and pos[0] < 500 and pos[0] < 500:
            return False
        
        # Distance evaluation
        self.current = (pos[0]-POINT[0]) ** 2 + (pos[1]-POINT[1]) ** 2 + (pos[2]-POINT[2]) ** 2
        return self.best == -1 or self.current < self.best

    def is_eval_time(self):
        return TIME_MIN <= self.current_time <= TIME_MAX

    def is_past_eval_time(self):
        return TIME_MAX <= self.current_time

    def is_max_time(self):
        return TIME_MAX == self.current_time

def get_nb_cp(state):
    return len([time for (time, _) in state.cp_data.cp_times if time != -1])

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
