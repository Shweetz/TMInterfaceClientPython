from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time
import struct
import math

### parameters
#7-8 inputs

target = "eval_time"
target_value = 2 # cp target
target_value = (5000, 6000) # eval min/max
target_value = 8500 # eval time
position_optimized = -1 # speed optimization
position_optimized = [800, 27, 823]
position_optimized = "max pitch" # ramm
restore_after_iterations = -1
min_diff = 0.1

if type(target_value) == int:
    eval_time_min = target_value
    eval_time_max = target_value

import numpy as np
import types
from scipy.spatial.transform import Rotation as R

# i put this method outside the MainClient class, its used for some magic patching later
def get_rotation_matrix(state) -> list:
    x1 = struct.unpack('f', state.dyna[464:468])[0]
    y1 = struct.unpack('f', state.dyna[468:472])[0]
    z1 = struct.unpack('f', state.dyna[472:476])[0]

    x2 = struct.unpack('f', state.dyna[476:480])[0]
    y2 = struct.unpack('f', state.dyna[480:484])[0]
    z2 = struct.unpack('f', state.dyna[484:488])[0]

    x3 = struct.unpack('f', state.dyna[488:492])[0]
    y3 = struct.unpack('f', state.dyna[492:496])[0]
    z3 = struct.unpack('f', state.dyna[496:500])[0]

    r1 = np.array([x1, x2, x3])
    r2 = np.array([y1, y2, y3])
    r3 = np.array([z1, z2, z3])

    m = np.array([r1, r2, r3])

    # m = m.transpose()
    r = R.from_matrix(m)
  
    return r.as_euler("yxz", True)
    
def compute_dist_2_points(pos1, pos2):
    return (pos2[0]-pos1[0]) ** 2 + (pos2[1]-pos1[1]) ** 2 + (pos2[2]-pos1[2]) ** 2

class MainClient(Client):
    def __init__(self) -> None:
        self.best = 0
        # self.eval_time = -1
        self.do_accept = False
        # self.do_reject = False
        # self.force_accept = False
        self.phase = BFPhase.INITIAL

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        # iface.execute_command('set controller bruteforce')
        # iface.execute_command('set bf_search_forever true')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        self.current_time = info.time - 2610
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING
        
        if self.phase == BFPhase.INITIAL:
            response.decision = BFEvaluationDecision.DO_NOTHING
            
            if eval_time_min <= self.current_time <= eval_time_max:
                state = iface.get_simulation_state()
                pitch = get_rotation_matrix(state)[1]
                if pitch < self.best or self.best == 0:
                    self.best = pitch
                    self.time = self.current_time
                
            elif self.current_time == eval_time_max + 10:
                print(f"base at {self.time}: {self.best=}")
                
        else:
            if eval_time_min <= self.current_time <= eval_time_max:
                state = iface.get_simulation_state()
                pitch = get_rotation_matrix(state)[1]
                # print(f"{pitch=}")
                if pitch < self.best - min_diff:
                    self.do_accept = True
                    self.best = pitch
                    self.time = self.current_time
                        
            elif eval_time_max < self.current_time:
                if self.do_accept:
                    response.decision = BFEvaluationDecision.ACCEPT
                    print(f"closer at {self.time}: {self.best=}")
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
