
import math
from tminterface.structs import BFEvaluationDecision
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

from scipy.spatial.transform import Rotation
import numpy as np
import sys

RAMM_TIME = 1000

class MainClient(Client):
    def __init__(self) -> None:
        # self.cp_count = -1
        self.lowest_time = -1
        # self.best_time = -1
        # self.base_velocity = None
        # self.finish_crossed = False
        # # self.nb_rewinds = 0
        # self.min_coeff = 0
        # self.max_coeff = 1
        # self.best_precise_time = -1
        # self.time_with_speed_coeff = -1
        # self.printed = False
        # self.simulation = False
        # self.states = []
        # self.bf_response = BFEvaluationDecision.DO_NOTHING

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_run_step(self, iface, _time):
        if _time == RAMM_TIME:
            state = iface.get_simulation_state()

            x, y, z = state.position
            y += 1
            state.position = [x, y, z]

            yaw, pitch, roll = state.yaw_pitch_roll

            pitch += 90 / 180 * math.pi
            roll += 30 / 180 * math.pi


            # state.yaw_pitch_roll = [yaw, pitch, roll]
            # from scipy.spatial.transform import Rotation as R

            # mat = state.rotation_matrix
            state.rotation_matrix = ypr_to_mat3([yaw, pitch, roll])
            iface.rewind_to_state(state)

def mat3_to_ypr(m: np.array):
    return Rotation.from_matrix(m.transpose()).as_euler('yxz', True)

def ypr_to_mat3(ypr: np.array):
    return Rotation.from_euler('yxz', ypr, True).as_matrix().transpose()

# Calculates Rotation Matrix given euler angles.
# def eulerAnglesToRotationMatrix(theta) :

#     R_x = np.array([[1,         0,                  0                   ],
#                     [0,         math.cos(theta[0]), -math.sin(theta[0]) ],
#                     [0,         math.sin(theta[0]), math.cos(theta[0])  ]
#                     ])

#     R_y = np.array([[math.cos(theta[1]),    0,      math.sin(theta[1])  ],
#                     [0,                     1,      0                   ],
#                     [-math.sin(theta[1]),   0,      math.cos(theta[1])  ]
#                     ])

#     R_z = np.array([[math.cos(theta[2]),    -math.sin(theta[2]),    0],
#                     [math.sin(theta[2]),    math.cos(theta[2]),     0],
#                     [0,                     0,                      1]
#                     ])

#     R = np.dot(R_z, np.dot( R_y, R_x ))
#     print(R)
#     return R

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""
Old stuff

# MUST GIVE INPUTS TIME FOR ON_RUN_STEP
# INPUTS_TIME = 26200
# print(f"Base time={INPUTS_TIME/1000}")

# state = iface.get_simulation_state()
# state.velocity = [100, 0, 0]
# iface.rewind_to_state(state)
"""
