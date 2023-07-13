from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.util import mat3_to_quat
# from tminterface.util import mat3_to_quat, euler_to_quaternion, quaternion_to_rotation_matrix

import math
import numpy as np
import sys

MIN_TIME = 8000 
MAX_TIME = 9000 

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        self.last_quat = None

    def on_run_step(self, iface, _time):
        state = iface.get_simulation_state()

        if MIN_TIME - 100 == _time:
            x, y, z = state.position
            state.position = [x, y + 10, z]
            # iface.rewind_to_state(state)

        if MIN_TIME <= _time <= MAX_TIME:
            # state.rotation_matrix = [[1, 0, 0], [0, 1.1, 0], [0, 0, 1]]
            # state.dyna.current_state.quat = mat3_to_quat(state.rotation_matrix)
            # iface.rewind_to_state(state)
            y, p, r = state.yaw_pitch_roll
            ypr = [y, p + 0.01, r]
            qua = euler_to_quaternion(*ypr)
            rot = quaternion_to_rotation_matrix(qua)
            # if self.last_quat is not None:
            #     state.dyna.previous_state.quat = self.last_quat
            #     state.dyna.previous_state.rotation = self.last_rota
            state.dyna.current_state.quat = qua
            state.dyna.current_state.rotation = rot
            iface.rewind_to_state(state)
            
            self.last_quat = qua
            self.last_rota = rot

        # self.last_quat = state.dyna.current_state.quat
        # self.last_rota = state.dyna.current_state.rotation


def euler_to_quaternion(yaw, pitch, roll):
    cy = np.cos(yaw * 0.5)
    sy = np.sin(yaw * 0.5)
    cp = np.cos(pitch * 0.5)
    sp = np.sin(pitch * 0.5)
    cr = np.cos(roll * 0.5)
    sr = np.sin(roll * 0.5)

    q = np.zeros(4)
    q[0] = cr * cp * cy + sr * sp * sy
    q[1] = sp * cy * cr - cp * sy * sr
    q[2] = cr * sy * cp + sr * cy * sp
    q[3] = cy * cp * sr - sy * sp * cr
    return q

def quaternion_to_rotation_matrix(q):
    R = np.zeros((3, 3))

    R[0, 0] = 1 - 2 * (q[2]**2 + q[3]**2)
    R[0, 1] = 2 * (q[1] * q[2] - q[3] * q[0])
    R[0, 2] = 2 * (q[1] * q[3] + q[2] * q[0])

    R[1, 0] = 2 * (q[1] * q[2] + q[3] * q[0])
    R[1, 1] = 1 - 2 * (q[1]**2 + q[3]**2)
    R[1, 2] = 2 * (q[2] * q[3] - q[1] * q[0])

    R[2, 0] = 2 * (q[1] * q[3] - q[2] * q[0])
    R[2, 1] = 2 * (q[2] * q[3] + q[1] * q[0])
    R[2, 2] = 1 - 2 * (q[1]**2 + q[2]**2)

    return R

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
