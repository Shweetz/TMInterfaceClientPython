
from dataclasses import dataclass
from enum import IntEnum
import os
import random
import struct
import sys
import time

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME

TRIGGER = [511, 88, 706, 479, 92, 670]

class MainClient(Client):
    def __init__(self) -> None:
        self.x = 0
        self.y = 0
        self.z = 0

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        print(f"Visualizing trigger {TRIGGER}")

    def on_run_step(self, iface, _time):
        self.state = iface.get_simulation_state()

        if _time % 100 == 0:
            self.randomize_position()

        self.place_car(iface)

    def randomize_position(self):
        self.x = random.choice([TRIGGER[0], TRIGGER[3]])
        self.y = random.choice([TRIGGER[1], TRIGGER[4]])
        self.z = random.choice([TRIGGER[2], TRIGGER[5]])

    def place_car(self, iface):
        self.state.position = [self.x, self.y, self.z]
        self.state.velocity = [0, 0, 0]
        iface.rewind_to_state(self.state)
    
    def get_angular_velocity(self, state):
        ax = struct.unpack('f', state.dyna[536:540])[0]
        ay = struct.unpack('f', state.dyna[540:544])[0]
        az = struct.unpack('f', state.dyna[544:548])[0]
        return ([ax, ay, az])
    
    def set_angular_velocity(self, state, angular_velocity):
        state.dyna[536:540] = list(struct.pack('f', angular_velocity[0]))
        state.dyna[540:544] = list(struct.pack('f', angular_velocity[1]))
        state.dyna[544:548] = list(struct.pack('f', angular_velocity[2]))


def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""Ideas:
- not rewind to time 0 => rewind to lowest_poss => rewind to 1st change
"""
