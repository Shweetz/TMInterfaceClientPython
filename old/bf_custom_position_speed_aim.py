from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time

import math

##### BF settings
# Time frame from 90000 to 95090 (54090 steer -65536)

target = 54250
# x = 582.421
# y = 87.781
# z = 522.255
# velx = -152.335
# vely = 38.378
# velz = -4.099
# aimx = 0.999
# aimy = -0.033
# aimz = -0.023

eval_time_min = 95100
eval_time_max = 95300
        
def compute_dist_2_points(pos1, pos2):
    return math.sqrt((pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2)
        
def compute_vel_2_points(pos1, pos2):
    return (pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2
    
def compute_aim_2_points(pos1, pos2):
    return (pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2
    
def compute_dist_speed_aim(pos_diff, speed_diff, aim_diff):
    return pos_diff*5 + speed_diff*10 + aim_diff*100

class MainClient(Client):
    def __init__(self) -> None:
        self.position_optimized = [582.421, 87.781, 522.255]
        self.velocity_optimized = [-152.335, 38.378, -4.099]
        self.aim_dire_optimized = [0.999, -0.033, -0.023]
        self.lowest = 10000000
        self.do_accept = False
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
        
        state = iface.get_simulation_state()
        
        if self.phase == BFPhase.INITIAL:
            if self.current_time == target:
                self.position_optimized = state.get_position()
                self.velocity_optimized = state.get_velocity()
                self.aim_dire_optimized = state.get_aim_direction()
                response.decision = BFEvaluationDecision.CONTINUE
        
        else:
            if self.current_time < eval_time_min:
                pass
                
            elif self.current_time <= eval_time_max:
                pos_diff = compute_dist_2_points(self.position_optimized, state.get_position())
                vel_diff = compute_vel_2_points(self.velocity_optimized, state.get_velocity())
                aim_diff = compute_aim_2_points(self.aim_dire_optimized, state.get_aim_direction())
                self.current = compute_dist_speed_aim(pos_diff, vel_diff, aim_diff)
                
                if self.current < self.lowest:
                    self.lowest = self.current
                    self.do_accept = True
                    self.pos_diff = pos_diff
                    self.vel_diff = vel_diff
                    self.aim_diff = aim_diff
                    self.time = self.current_time
                    
            else:
                if self.do_accept:
                    response.decision = BFEvaluationDecision.ACCEPT
                    print(f"closer at {self.time}: {self.lowest=}, {self.pos_diff=}, {self.vel_diff=}, {self.aim_diff=}")
                else:
                    response.decision = BFEvaluationDecision.REJECT
                    
                self.do_accept = False
                
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
