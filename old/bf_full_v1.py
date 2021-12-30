from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
import sys
import signal
import time

import math
import numpy as np

CUSTOM = -1

# Eval target
TIME = 0
CP = 1
TRIGGER = 2
target = TIME

eval_time_min = 8400 # target time
# eval_time_max = 8400 # target time
eval_time_max = eval_time_min # target time
CP_NUMBER = -1 # target CP
TRIGGER_POS = [0, 0, 0, 100, 10, 100] # target trigger

# Parameter to optimize
DISTANCE = 0
VELOCITY = 1
PITCH = 2
parameter = VELOCITY

MAX = 0
MIN = 1
CLOSEST_TO = 2
POINT_POS = [94, 49, 653] # opti distance
POINT_POS = [136, 50, 610] # opti distance

# Other
# eval_cps = -1
eval_trigger = False

# Restore base run after x iterations
restore_after_iterations = -1

# Min diff to consider an improvement worthy
min_diff = 0

class MainClient(Client):
    def __init__(self) -> None:
        self.best = -1
        self.time = -1
        self.do_accept = False
        self.do_reject = False
        self.force_accept = False
        self.past_eval = False
        self.cp_count = 0
        self.phase = BFPhase.INITIAL

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller bruteforce')
        iface.execute_command('set bf_search_forever true')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        self.current_time = info.time
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING
        
        if self.phase == BFPhase.INITIAL:
            if self.is_eval_time():
                state = iface.get_simulation_state()
                if self.is_better(state):
                    if self.condition(state):
                        self.best = self.current
                        self.time = self.current_time
                
            # elif self.current_time == eval_time_max + 10:
            elif self.is_past_eval_time():
                print(f"base at {self.time}: {self.best=}")
                
        else:
            if self.is_eval_time():
                state = iface.get_simulation_state()
                if self.is_better(state, min_diff):
                    if self.condition(state):
                        self.do_accept = True
                        self.best = self.current
                        self.time = self.current_time
                # else:
                    # print(f"not better at {self.current_time}: {self.current=}")
                self.past_eval = True
                        
            elif self.is_past_eval_time():
                # print("yo")
                if self.do_accept:
                    response.decision = BFEvaluationDecision.ACCEPT
                    # print(f"better at {self.time}: {self.best=}")
                else:
                    response.decision = BFEvaluationDecision.REJECT
                
                self.force_accept = False
                self.do_accept = False
                self.past_eval = False

        return response

    def is_better(self, state, min_diff=0):
        # if self.best == -1:
        #     return True

        if parameter == DISTANCE:
            return self.is_closer(state, min_diff)
        if parameter == VELOCITY:
            if self.best < 999:
                return self.is_faster(state, min_diff)
            else:
                return compute_velocity(state) > 999 and abs(state.velocity[2]) < 5
        if parameter == CUSTOM:
            # return self.is_earlier(state, min_diff)
            self.current = abs(state.position[0] - 375) + abs(state.position[2] - 808)
            self.current = abs(get_pitch(state) - 90)
            if self.best == -1:
                return True
            return self.current < self.best + min_diff

        return False
        
    def is_faster(self, state, min_diff=0):
        self.current = compute_velocity(state)
        self.current = min(self.current, 1000)
        if self.best == -1:
            return True
        return self.current > self.best + min_diff
    
    def is_closer(self, state, min_diff=0):
        self.current = compute_dist_2_points(POINT_POS, state.position)
        if self.best == -1:
            return True
        return self.current < self.best - min_diff
    
    def is_earlier(self, state, min_diff=0):
        self.current = self.current_time
        if self.best == -1:
            return True
        return self.current < self.best - min_diff

    def condition(self, state):
        # return abs(get_yaw(state) + 90) < 15 and abs(get_pitch(state) - 90) < 10 and abs(get_roll(state)) < 30 and compute_velocity(state) > 450
        return state.position[0] < 129 and compute_velocity(state) > 570 and state.velocity[0] < 0 and state.velocity[2] > -state.velocity[0]
        return True
    
    def is_eval_time(self):
        ret = True
        if eval_time_min != -1:
            if self.current_time < eval_time_min:
                ret = False
        if eval_time_max != -1:
            if eval_time_max < self.current_time:
                ret = False
        if CP_NUMBER != -1:
            if CP_NUMBER > self.cp_count:
                ret = False
        if eval_trigger:
            # check pos in trigger
            if CP_NUMBER < self.cp_count:
                ret = False
        
        # if not self.condition(state):
        #     ret = False
        return ret

    def is_past_eval_time(self):
        # print("yoyo")
        # if eval_time_max != -1:
        #     if eval_time_max < self.current_time:
        #         return True
        # if CP_NUMBER != -1:
        #     if CP_NUMBER == self.cp_count:
        #         return True
        return self.current_time == eval_time_max + 10
            
    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        self.cp_count = current


def compute_dist_2_points(pos1, pos2):
    return (pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2

def compute_velocity(state):
    vel_mph = np.linalg.norm(state.velocity)
    return vel_mph * 3.6

def get_yaw(state):
    yaw_rad = state.yaw_pitch_roll[0]
    return yaw_rad * 180 / 3.14

def get_pitch(state):
    pitch_rad = state.yaw_pitch_roll[1]
    return pitch_rad * 180 / 3.14
    
def get_roll(state):
    roll_rad = state.yaw_pitch_roll[2]
    return roll_rad * 180 / 3.14

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
