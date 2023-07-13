from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time

import math

position_optimized = [800, 26.8, 824.8]
check_axes = "x"
target_cp_number = 2
best_cp_time = 22110
min_dist_diff = 1

def compute_dist_2_points(pos1, pos2):
    # return (pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2
    return (pos2[0]-pos1[0]) ** 2

class MainClient(Client):
    def __init__(self) -> None:
        self.lowest_time = 100000
        self.lowest_dist = 100000
        self.current_time = 100000
        self.current_dist = 100000
        self.do_accept = False
        self.force_accept = False
        self.phase = BFPhase.INITIAL

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller bruteforce')
        iface.execute_command('set bf_search_forever true')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        # print("bf")
        self.phase = info.phase
        self.current_time = info.time - 2610
        
        # if self.current_time == 52510:
            # print("bf")
            
        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING

        # if self.force_accept:
            # response.decision = BFEvaluationDecision.ACCEPT
            # self.lowest_time = self.current_time
            # self.lowest_dist = 100000
            
            # self.do_accept = False
            # self.force_accept = False
            # return response
            
        if self.do_accept:
            if self.current_dist < self.lowest_dist - min_dist_diff:
                response.decision = BFEvaluationDecision.ACCEPT
                # self.lowest_dist = self.current_dist

            else:
                response.decision = BFEvaluationDecision.REJECT
        
        elif self.current_time > best_cp_time:
            # CP not hit on time
            response.decision = BFEvaluationDecision.REJECT
            
        self.do_accept = False
        self.force_accept = False
        return response

    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        # if iface.get_simulation_state().get_time() - 2610 == 52510:
            # print("cp")
		# print(f"current={current}")
        if current == target_cp_number:
            state = iface.get_simulation_state()
            if self.phase == BFPhase.INITIAL:
                self.lowest_time = state.get_time() - 2610
                self.lowest_dist = compute_dist_2_points(position_optimized, state.get_position())
                print(f"time={self.lowest_time}, dist={self.lowest_dist}, {state.get_position()=}")
            elif self.phase == BFPhase.SEARCH:
                self.current_time = state.get_time() - 2610
                self.current_dist = compute_dist_2_points(position_optimized, state.get_position())
                # print(f"time2={self.current_time}, dist2={self.current_dist}")
                if self.current_time <= self.lowest_time:
                    self.do_accept = True

                if self.current_time < self.lowest_time:
                    self.force_accept = True

def main():
    server_name = 'TMInterface0'
    if len(sys.argv) > 1:
        server_name = 'TMInterface' + str(sys.argv[1])

    print(f'Connecting to {server_name}...')

    iface = TMInterface(server_name)
    def handler(signum, frame):
        iface.close()

    signal.signal(signal.SIGBREAK, handler)
    signal.signal(signal.SIGINT, handler)

    client = MainClient()
    iface.register(client)

    while iface.running:
        time.sleep(0)

if __name__ == '__main__':
    main()
