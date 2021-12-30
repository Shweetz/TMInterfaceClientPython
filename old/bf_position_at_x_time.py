from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time

import math

start_eval_time = 13850
time_optimized = 15000
position_optimized = [606.4, 121.6, 371.7]
target_cp_number = 4 # needs more testing

def compute_dist_2_points(pos1, pos2):
    return math.sqrt((pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2)

class MainClient(Client):
    def __init__(self) -> None:
        self.lowest_time = 20400
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
        self.lowest_dist = 100000

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        # print("bf")
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING

        state = iface.get_simulation_state()
        self.current_time = state.get_time() - 2610

        # if self.current_time > time_optimized and self.phase == BFPhase.SEARCH:
        if self.current_time > time_optimized:
            
            if self.current_dist < self.lowest_dist:
                response.decision = BFEvaluationDecision.ACCEPT
                print(f"time={self.current_time}, dist={self.current_dist}, dist={self.lowest_dist}")
                self.lowest_dist = self.current_dist
                self.do_accept = True
            else:
                response.decision = BFEvaluationDecision.REJECT
                
        elif self.current_time > start_eval_time:
            # print(self.current_time)
            response.decision = BFEvaluationDecision.DO_NOTHING

            if self.phase == BFPhase.INITIAL:
                # self.lowest_time = state.get_time() - 2610
                dist = compute_dist_2_points(position_optimized, state.get_position())
                if dist < self.lowest_dist:
                    self.lowest_dist = min(self.lowest_dist, dist)
                    print(f"i_time={self.current_time}, i_dist={self.lowest_dist}")

            elif self.phase == BFPhase.SEARCH:

                dist = compute_dist_2_points(position_optimized, state.get_position())
                if dist < self.current_dist:
                    self.current_dist = min(self.current_dist, dist)
                
                # self.current_dist = compute_dist_2_points(position_optimized, state.get_position())
                # print(f"time2={self.current_time}, dist2={self.current_dist}")
                # if self.current_dist < self.lowest_dist:
                    # print(f"time={self.current_time}, dist={self.lowest_dist}")
                    # self.do_accept = True

            # if self.force_accept:
                # response.decision = BFEvaluationDecision.ACCEPT
                # self.lowest_time = self.current_time
                # self.lowest_dist = 100000
                # print(f"time2={self.current_time}, dist2={self.current_dist}")

            # elif self.do_accept:
                # response.decision = BFEvaluationDecision.ACCEPT
                # print(f"time={self.lowest_time}, dist={self.lowest_dist}")
                # self.lowest_dist = self.current_dist

        self.do_accept = False
        self.force_accept = False

        return response

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
