from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time

# import math

def compute_dist_2_points(pos1, pos2):
    return (pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2

class Trigger():
    def __init__(self, x1, y1, z1, x2, y2, z2) -> None:
        self.x1 = x1
        self.y1 = y1
        self.z1 = z1
        self.x2 = x2
        self.y2 = y2
        self.z2 = z2
        self.center = [(x1+x2) / 2, (y1+y2) / 2, (z1+z2) / 2]
    
    def is_triggered(self, pos):
        x, y, z = pos
        if self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2 and self.z1 <= z <= self.z2:
            return True
        else:
            return False

# trigger = Trigger(876, 15, 780, 900, 17, 800) # B08 1st drop
# position_optimized = (960, 9, 552)
# min_time = 9000

trigger = Trigger(690, 8, 370, 704, 10, 379) # B08 left before cp
position_optimized = (617, 9, 379)
min_time = 13800

# position_optimized = -1

class MainClient(Client):
    def __init__(self) -> None:
        self.current_time = 0
        self.do_accept = -1
        self.lowest_time = 100000
        self.lowest_dist = 100000
        self.current_speed = 0
        self.lowest_speed = 0
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
        
        if self.current_time < min_time:
            return response
            
        state = iface.get_simulation_state()
        pos = state.get_position()
        if trigger.is_triggered(pos):
            # print("trig")
            self.current_time = state.get_time()
            
            # if self.phase == BFPhase.SEARCH:
            if self.current_time < self.lowest_time:
                response.decision = BFEvaluationDecision.ACCEPT
                print(f"time={self.current_time}")
                self.lowest_time = self.current_time
                if position_optimized == -1:
                    self.lowest_dist = compute_dist_2_points(pos, trigger.center)
                else:
                    self.lowest_dist = compute_dist_2_points(pos, position_optimized)
                
            elif self.current_time == self.lowest_time:
                if position_optimized == -1:
                    self.current_dist = compute_dist_2_points(pos, trigger.center)
                else:
                    self.current_dist = compute_dist_2_points(pos, position_optimized)
                    
                if self.current_dist < self.lowest_dist:
                    self.lowest_dist = self.current_dist
                    response.decision = BFEvaluationDecision.ACCEPT
                    print(f"dist={self.current_dist}")
                else:
                    response.decision = BFEvaluationDecision.REJECT
            else:
                response.decision = BFEvaluationDecision.REJECT

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
