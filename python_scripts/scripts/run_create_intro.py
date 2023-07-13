from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.util import mat3_to_quat
# from tminterface.util import mat3_to_quat, euler_to_quaternion, quaternion_to_rotation_matrix

import math
import numpy as np
import sys

#StarIslandD3 by Kimura
MIN_TIME = 11000
MAX_TIME = 14500
MIN = [1859, 42, 1678]
MAX = [1893, 55, 1716]

DIFF = MAX_TIME - MIN_TIME

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        self.recording = True
        self.states = []
        self.state_index = 0
        print(f"{self.recording=}")
        self.ax = 0
        self.bx = 0

    def on_run_step(self, iface, _time):
        state = iface.get_simulation_state()

        if MIN_TIME - 100 == _time:
            x, y, z = state.position
            state.position = [x, y + 10, z]
            # iface.rewind_to_state(state)

        if MIN_TIME <= _time < MAX_TIME:
            # x, y, z = state.position
            # state.position = [x, y + 10, z]

            # y, p, r = state.yaw_pitch_roll
            # ypr = [y, p, r]
            # qua = euler_to_quaternion(*ypr)
            # rot = quaternion_to_rotation_matrix(qua)
            # state.dyna.current_state.quat = qua
            # state.dyna.current_state.rotation = rot

            # iface.rewind_to_state(state)

            if self.recording:
                self.states.append(state)
            else:
                if self.state_index < len(self.states):
                    state = self.states[self.state_index]

                    x, y, z = state.position
                    state.position = [self.ax * x + self.bx, self.ay * y + self.by, self.az * z + self.bz]

                    vx, vy, vz = state.dyna.current_state.linear_speed
                    # state.velocity = [self.ax * vx, self.ay * vy, self.az * vz] API bug
                    state.dyna.current_state.linear_speed = [self.ax * vx, self.ay * vy, self.az * vz]

                    avx, avy, avz = state.dyna.current_state.angular_speed
                    state.dyna.current_state.angular_speed = [self.ax * avx, self.ay * avy, self.az * avz]
                    
                    iface.rewind_to_state(state)

                    # Why these?
                    # state.position = [x, y, z]
                    # state.dyna.current_state.linear_speed = [vx, vy, vz]
                    # state.dyna.current_state.angular_speed = [avx, avy, avz]

                    self.state_index += 1

        if MAX_TIME == _time:
            self.state_index = 0
            self.recording = False
            # print(f"{self.recording=}")
            min_x, min_y, min_z = [int(a) for a in self.states[0].position]
            max_x, max_y, max_z = [int(a) for a in self.states[0].position]
            # min_x, min_y, min_z = self.states[0].position
            # max_x, max_y, max_z = self.states[0].position

            for state in self.states:
                x, y, z = [int(a) for a in state.position]
                # print(f"{x}, {y}, {z}")
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
                if z < min_z: min_z = z
                if z > max_z: max_z = z
            
            print(f"{self.recording=}, {min_x=}, {max_x=}, {min_y=}, {max_y=}, {min_z=}, {max_z=}")
            self.ax = (MAX[0] - MIN[0]) / (max_x - min_x)
            self.bx = MIN[0] - min_x * self.ax
            self.ay = (MAX[1] - MIN[1]) / (max_y - min_y)
            self.by = MIN[1] - min_y * self.ay
            self.az = (MAX[2] - MIN[2]) / (max_z - min_z)
            self.bz = MIN[2] - min_z * self.az
            # print(f"{self.ay=}")
            # print(f"{self.by=}")


        # if MAX_TIME <= _time <= MAX_TIME + DIFF and self.state_index < len(self.states):
        #     state = self.states[self.state_index]

        #     x, y, z = state.position
        #     state.position = [x, y + 10, z]
        #     iface.rewind_to_state(state)

        #     self.state_index += 1


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
