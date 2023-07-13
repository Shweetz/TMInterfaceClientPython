from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time

import math

# eval_after_in_ms = 100
# target_cp_number = 1 # needs more testing
min_dist_diff = 1

position_optimized = [1000, 9, 585]
check_axes = "x"
eval_time_min = 10080
eval_time_max = 10080

def compute_dist_2_points(pos1, pos2):
    return (pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2
    # return (pos2[0]-pos1[0]) ** 2

class MainClient(Client):
    def __init__(self) -> None:
        self.lowest_time = 1000000
        self.lowest_dist = 1000000
        # self.current_time = 1000000
        # self.current_dist = 1000000
        # self.eval_time = -1
        self.do_accept = False
        self.do_reject = False
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
        self.current_time = info.time - 2610
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING
            
        if self.current_time < eval_time_min:
            return response
        
        if self.phase == BFPhase.INITIAL:
            # response.decision = BFEvaluationDecision.DO_NOTHING
            
            # print(f"{self.lowest_dist}")
            if self.current_time <= eval_time_max:
                state = iface.get_simulation_state()
                self.current_dist = compute_dist_2_points(position_optimized, state.get_position())
                if self.current_dist < self.lowest_dist:
                    self.lowest_dist = self.current_dist
                    self.time = self.current_time
                
            elif self.current_time == eval_time_max + 10:
                print(f"base at {self.time}: {self.lowest_dist=}")
                
        else:
                
            if self.current_time <= eval_time_max:
                state = iface.get_simulation_state()
                self.current_dist = compute_dist_2_points(position_optimized, state.get_position())
                # print(f"{self.current_dist=}, {self.lowest_dist=}")
                # z = state.get_position()[2]
                # if self.current_dist < self.lowest_dist - min_dist_diff and z > 800:
                # if self.current_dist < self.lowest_dist - min_dist_diff:
                if self.current_dist < self.lowest_dist:
                    self.do_accept = True
                    self.lowest_dist = self.current_dist
                    self.time = self.current_time
                    #print(f"time={self.current_time}, dist={self.lowest_dist}")
                        
            else:
                # if self.force_accept:
                    # print("FOUND FINISH")
                    # response.decision = BFEvaluationDecision.ACCEPT
                    # self.lowest_dist = 0
                    
                # else:
                if self.do_accept:
                    response.decision = BFEvaluationDecision.ACCEPT
                    print(f"closer at {self.time}: {self.lowest_dist=}")
                else:
                    response.decision = BFEvaluationDecision.REJECT
                
                self.force_accept = False
                self.do_accept = False
            
        # if self.force_accept:
            # response.decision = BFEvaluationDecision.ACCEPT
            # self.lowest_time = self.current_time
            # self.lowest_dist = 100000
            
            # self.do_accept = False
            # self.force_accept = False
            # return response
            
        # if self.do_accept:
            # self.eval_time = self.current_time + eval_after_in_ms
            
        # if self.do_reject:
            # response.decision = BFEvaluationDecision.REJECT
            
        # self.do_accept = False
        # self.do_reject = False
        # self.force_accept = False
        return response

    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        if current == 2:
            state = iface.get_simulation_state()
            if self.phase == BFPhase.INITIAL:
                self.lowest_time = state.get_time() - 2610
                self.lowest_dist = compute_dist_2_points(position_optimized, state.get_position())
                
                self.eval_time = -1
            elif self.phase == BFPhase.SEARCH:
                if state.get_position()[1] > 50:
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
