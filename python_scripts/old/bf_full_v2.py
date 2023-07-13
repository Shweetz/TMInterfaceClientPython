# strategy = ""
# def is_earlier(): pass
# def is_closer(): pass
# def is_faster(): pass
# def a():
#     if strategy == "distance":
#         return is_earlier() or is_closer()

#     if strategy == "distance,velocity":
#         return is_earlier() or is_faster()

#     if strategy == "velocity":
#         return is_faster()

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

eval_time_min = 10500 # target time
# eval_time_max = 9000 # target time
eval_time_max = eval_time_min # target time
CP_NUMBER = 8 # target CP
TRIGGER_POS = [0, 0, 0, 100, 10, 100] # target trigger

# Parameter to optimize
TIME = 0
DISTANCE = 1
VELOCITY = 2
PITCH = 3
parameter = CUSTOM

MAX = 0
MIN = 1
CLOSEST_TO = 2
# POINT_POS = [94, 49, 653] # opti distance
POINT_POS = [504, 103, 507] # opti distance

# Other
# Restore base run after x iterations
restore_after_iterations = -1

# Min diff to consider an improvement worthy
min_diff = 0

class MainClient(Client):
    def __init__(self) -> None:
        self.best = -1
        self.time = -1
        self.cp_count = 0
        self.phase = BFPhase.INITIAL

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration

    # def on_run_step(self, iface, _time):
    #     if _time > 1000: 
    #         state = iface.get_simulation_state()
    #         vel_x = state.velocity[0]
    #         vel_z = state.velocity[2]
    #         a = abs(vel_x) / (abs(vel_x) + abs(vel_z))
    #         b = a * 3.14 / 2
    #         # if vel_z < 0:
    #         #     b = -b
    #         if vel_z < 0 and vel_x > 0:
    #             b = - b - 3.14
    #         if vel_z < 0 and vel_x < 0:
    #             b = - b + 3.14
            # print(b)
            # print(f"{_time}: {math.atan2(vel_x, vel_z)}")

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

            if self.is_past_eval_time():
                print(f"base at {self.time}: {self.best=}")
                
        elif self.phase == BFPhase.SEARCH:
            if self.is_eval_time():
                state = iface.get_simulation_state()
                if self.is_better(state, min_diff):
                    if self.condition(state):
                        response.decision = BFEvaluationDecision.ACCEPT
                # else:
                    # print(f"not better at {self.current_time}: {self.current=}")
                        
            if self.is_past_eval_time():
                if response.decision != BFEvaluationDecision.ACCEPT:
                    response.decision = BFEvaluationDecision.REJECT

        return response

    def is_better(self, state, min_diff=0):
        if parameter == TIME:
            return self.is_earlier(state, min_diff)

        if parameter == DISTANCE:
            # return self.is_further(state, min_diff, axis="xz")
            return self.is_closer(state, min_diff)

        if parameter == VELOCITY:
            if self.best < 999:
                return self.is_faster(state, min_diff)
            else:
                return get_vel_kmh(state) > 999 and abs(state.velocity[2]) < 5
                
        if parameter == CUSTOM:
            # self.current = abs(state.position[0] - 375) + abs(state.position[2] - 808)
            # self.current = abs(get_pitch_deg(state) - 90)
            # self.current = state.position[0]
            self.current = state.position[1]
            if self.best == -1:
                return True
            return self.current < self.best - min_diff

        return False
        
    def is_faster(self, state, min_diff=0):
        self.current = get_vel_kmh(state)
        self.current = min(self.current, 1000)
        if self.best == -1:
            return True
        return self.current > self.best + min_diff
    
    def is_closer(self, state, min_diff=0):
        self.current = get_dist_2_points(POINT_POS, state.position)
        if self.best == -1:
            return True
        return self.current < self.best - min_diff
    
    def is_further(self, state, min_diff=0, axis="xyz"):
        self.current = get_dist_2_points(POINT_POS, state.position, axis)
        if self.best == -1:
            return True
        return self.current > self.best + min_diff
    
    def is_earlier(self, state, min_diff=0):
        self.current = self.current_time
        if self.best == -1:
            return True
        return self.current < self.best - min_diff

    def condition(self, state):
        return self.cp_count == 1 and abs(get_pitch_deg(state)) < 30 and state.position[2] < 515
        return state.position[1] > 70 and state.position[2] < 400
        return abs(get_yaw_deg(state) + 90) < 15 and abs(get_pitch_deg(state) - 90) < 10 and abs(get_roll_deg(state)) < 30 and get_vel_kmh(state) > 450
        return state.position[0] < 129 and get_vel_kmh(state) > 570 and state.velocity[0] < 0 and state.velocity[2] > -state.velocity[0]
        return get_pitch_deg(state) > 0
        return 40 < state.position[1] < 43 and 550 < state.position[2]
        return self.cp_count == 8
        return state.position[0] > 400 and abs(get_pitch_deg(state) - 90) < 10
        return True
    
    def is_eval_time(self):
        if target == TIME:
            if eval_time_min <= self.current_time <= eval_time_max:
                return True

        if target == CP:
            if CP_NUMBER <= self.cp_count:
                return True

        if target == TRIGGER:
            # TODO
            return True
        
        return False
    
    # def is_eval_time_old(self):
    #     ret = True
    #     if target == TIME:
    #         if self.current_time < eval_time_min or eval_time_max < self.current_time:
    #             ret = False
    #     if target == CP:
    #         if CP_NUMBER > self.cp_count:
    #             ret = False
    #     if target == TRIGGER:
    #         # TODO
    #         pass
        
    #     return ret

    def is_past_eval_time(self):
        # print("yoyo")
        # if eval_time_max != -1:
        #     if eval_time_max < self.current_time:
        #         return True
        # if CP_NUMBER != -1:
        #     if CP_NUMBER == self.cp_count:
        #         return True
        if target == TIME:
            if self.current_time == eval_time_max:
                return True
        if target == CP:
            if CP_NUMBER <= self.cp_count:
                self.cp_count = 0
                return True
        if target == TRIGGER:
            return self.is_eval_time()
        
        return False
            
    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        self.cp_count = current


def get_dist_2_points(pos1, pos2, axis="xyz"):
    dist = 0
    if "x" in axis:
        dist += (pos2[0]-pos1[0]) ** 2
    if "y" in axis:
        dist += (pos2[1]-pos1[1]) ** 2
    if "z" in axis:
        dist += (pos2[2]-pos1[2]) ** 2
    return dist

def get_vel_kmh(state):
    vel_mph = np.linalg.norm(state.velocity)
    return vel_mph * 3.6

def get_yaw_deg(state):
    yaw_rad = state.yaw_pitch_roll[0]
    return yaw_rad * 180 / 3.14

def get_pitch_deg(state):
    math.pi
    pitch_rad = state.yaw_pitch_roll[1]
    return pitch_rad * 180 / 3.14
    
def get_roll_deg(state):
    roll_rad = state.yaw_pitch_roll[2]
    return roll_rad * 180 / 3.14

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
