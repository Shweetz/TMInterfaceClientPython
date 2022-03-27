from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client

import datetime
import os
import math
import shutil
import signal
import sys
import time

"""
for this script, you need a base run that is not a uber but close to it (uber setup)

then you need to set 
position_optimized to where you want to go
min_velocity_for_uber which is the velocity (m/s) you can only reach with a uber

what it does is try to find uber (it thinks it ubered when the car is faster than min_velocity_for_uber)
when it does, it keeps that as improvement and will then try to get as close as possible to position_optimized
after X iterations (where X is max_iterations_for_uber), it will restore base run (uber setup) and try again

every improvement will be saved in a new file and you will have a lot of inputs files to check
there will be uber_XXX.txt (where XXX is the velocity) and closer_YYY (where YYY is the squared distance to position_optimized) 
"""

res_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + "result.txt"
position_optimized = [600, 68, 693]
target_cp_number = 1
min_dist_diff = 0
eval_time_min = 10000
eval_time_max = 10700
min_velocity_for_uber = 150
max_iterations_for_uber = 10000

def compute_dist_2_points(pos1, pos2):
    return (pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2

def compute_velocity(vel):
    return math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2)

class MainClient(Client):
    def __init__(self) -> None:
        self.lowest_time = 1000000
        self.lowest_dist = 1000000
        self.current_time = 1000000
        self.current_dist = 1000000
        # self.eval_time = -1
        self.do_accept = False
        self.do_reject = False
        self.force_accept = False
        self.phase = BFPhase.INITIAL
        self.goal = ""
        self.iterations = 0
        self.iterations_after_uber = 0
        self.save = ""
        self.is_base_run_saved = False

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        # iface.execute_command('set controller bruteforce')
        # iface.execute_command('set bf_search_forever true')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        self.current_time = info.time
        self.phase = info.phase
            
        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING
        
        ###########
        # INITIAL #
        ###########
        if self.phase == BFPhase.INITIAL:
            response.decision = BFEvaluationDecision.CONTINUE
            
            if self.current_time < eval_time_min - 10:
                pass
                
            elif self.current_time == eval_time_min - 10:
            
                if not self.is_base_run_saved:
                    self.save_base_run(iface)
                
                if self.goal == "find_uber":
                    self.velocity = 0
                    self.lowest_dist = 1000000
                # self.lowest_dist = 1000000
            
            elif self.current_time <= eval_time_max:
                state = iface.get_simulation_state()
                    
                if self.goal == "find_uber":
                    self.current_velocity = compute_velocity(state.velocity)
                    if self.current_velocity > self.velocity:
                        self.velocity = self.current_velocity
                        self.vel_time = self.current_time
                        
                    self.current_dist = compute_dist_2_points(position_optimized, state.position)
                    if self.current_dist < self.lowest_dist - min_dist_diff:
                        self.lowest_dist = self.current_dist
                        self.dist_time = self.current_time
                        
                elif self.goal == "improve_uber":
                    self.current_dist = compute_dist_2_points(position_optimized, state.position)
                    if self.current_dist < self.lowest_dist - min_dist_diff:
                        self.lowest_dist = self.current_dist
                        self.dist_time = self.current_time
                    
            elif self.current_time == eval_time_max + 10:
                if self.goal == "find_uber":
                    print(f"FOUND UBER: {self.velocity=} at {self.vel_time}")
                    print(f"base closer at {self.dist_time}: {self.lowest_dist=}")
                    
                    self.save_result(f"uber_{self.velocity}")
                    
                    self.goal = "improve_uber"
                    self.iterations_after_uber = 0
                    
                elif self.goal == "improve_uber":
                    print(f"closer at {self.dist_time}: {self.lowest_dist=}")
                    
                    self.save_result(f"closer_{self.lowest_dist}")
                    
                elif self.goal == "":
                    self.goal = "find_uber"
            
            if self.force_accept:
                self.finish_time = iface.get_event_buffer().events_duration
                self.save_result(f"FINISH_{self.finish_time}")
                self.force_accept = False
                
        ##########
        # SEARCH #
        ##########
        elif self.phase == BFPhase.SEARCH:
            if self.current_time < eval_time_min:
                pass
                
            elif self.current_time <= eval_time_max:
                if self.goal == "find_uber":
                    state = iface.get_simulation_state()
                    self.current_velocity = compute_velocity(state.velocity)
                    
                    # if not self.do_accept and self.current_velocity > min_velocity_for_uber:
                        # self.do_accept = True
                    
                    # if self.do_accept:
                        # if self.current_velocity > self.velocity:
                            # self.velocity = self.current_velocity
                            # self.vel_time = self.current_time
                            
                        # self.current_dist = compute_dist_2_points(position_optimized, state.get_position())
                        # if self.current_dist < self.lowest_dist - min_dist_diff:
                            # self.lowest_dist = self.current_dist
                            # self.dist_time = self.current_time
                            
                    if self.current_velocity > min_velocity_for_uber:        
                        response.decision = BFEvaluationDecision.ACCEPT
                    
                elif self.goal == "improve_uber":                    
                    state = iface.get_simulation_state()
                    self.current_dist = compute_dist_2_points(position_optimized, state.position)
                    if self.current_dist < self.lowest_dist - min_dist_diff:
                        response.decision = BFEvaluationDecision.ACCEPT
                        #print(f"dist_time={self.current_time}, dist={self.lowest_dist}")
                        
            else:
                response.decision = BFEvaluationDecision.REJECT
                # if self.goal == "find_uber":
                    # if self.do_accept:
                        # response.decision = BFEvaluationDecision.ACCEPT
                    # else:
                        # response.decision = BFEvaluationDecision.REJECT
                    
                if self.goal == "improve_uber":
                    # if self.do_accept:
                        # response.decision = BFEvaluationDecision.ACCEPT
                    # else:
                        # response.decision = BFEvaluationDecision.REJECT
                    
                    if self.iterations_after_uber % 1000 == 0:
                        print(f"{self.iterations_after_uber=}")                    
                    self.iterations_after_uber += 1
                    
                if self.iterations % 100 == 0:
                    print(f"{self.iterations=}")            
                self.iterations += 1
                
                # self.force_accept = False
                # self.do_accept = False
            
                if self.iterations_after_uber > max_iterations_for_uber:
                    print("too many iterations, restoring base run")
                    print("=======================================")
                    self.iterations_after_uber = 0
                    self.goal = ""
                    self.load_base_run(iface)
                    response.decision = BFEvaluationDecision.ACCEPT
                    
        if self.force_accept:
            print("FOUND FINISH")
            response.decision = BFEvaluationDecision.ACCEPT
                        
        return response
    
    # Check if finish is found
    # def on_checkpoint_count_changed(self, iface, current: int, target: int):
    #     if current == target_cp_number:
    #         state = iface.get_simulation_state()
    #         if self.phase == BFPhase.SEARCH:
    #             self.force_accept = True
                
    #             # Condition to filter fake finishes
    #             # print(f"{state.get_position()[1]}")
    #             if state.get_position()[1] < 50:
    #                 self.force_accept = False
    
    def save_base_run(self, iface):
        self.is_base_run_saved = True
        self.base_run = iface.get_event_buffer()
    
    def load_base_run(self, iface):
        iface.set_event_buffer(self.base_run)
        
    def save_result(self, result_name):
        date = datetime.datetime.now()
        date = date.strftime("%Y%m%d_%H%M%S")
        dest = res_file.replace("result.txt", f"{date}_{result_name}.txt")
        shutil.copy2(res_file, dest)
        
def main():
    server_name = 'TMInterface1'
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
