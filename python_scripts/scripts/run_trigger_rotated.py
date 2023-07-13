TRIGGER = [523, 9, 458, 550, 20, 490]
TRIGGER_ANGLE = 90

import math
import sys

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

class MainClient(Client):
    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_run_step(self, iface, _time):
        state = iface.get_simulation_state()
        print(distance_to_trigger(state))

def to_rad(deg):
    return deg / 180 * math.pi

def to_deg(rad):
    return rad * 180 / math.pi

def distance_to_trigger(pos):
    x, y, z = pos
    x1, y1, z1, x2, y2, z2 = TRIGGER

    # change center: trigger point is new 0,0
    x_mid = x - min(x1,x2)
    z_mid = z - min(z1,z2)

    # print(x_mid)
    # print(z_mid)

    # transpose with target direction
    angle = to_rad(TRIGGER_ANGLE)

    x_new = x_mid * math.cos(angle) - z_mid * math.sin(angle)
    z_new = x_mid * math.sin(angle) + z_mid * math.cos(angle)

    # print(x_new)
    # print(z_new)

    x_size = max(x1,x2) - min(x1,x2)
    z_size = max(z1,z2) - min(z1,z2)

    # if 0 < x_new < x_size and 0 < z_new < z_size and min(y1,y2) < y < max(y1,y2):
    #     return 0
    
    print(x_new, x_size, z_new, z_size)

    dist = 0
    if x_new < 0     : dist += abs(x_new)          ** 2
    if x_new > x_size: dist += abs(x_new - x_size) ** 2
    if z_new < 0     : dist += abs(z_new)          ** 2
    if z_new > z_size: dist += abs(z_new - z_size) ** 2
    if y < min(y1,y2): dist += abs(y - min(y1,y2)) ** 2
    if y > max(y1,y2): dist += abs(y - max(y1,y2)) ** 2

    return math.sqrt(dist)


def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    # main()
    TRIGGER = [523, 9, 458, 550, 20, 490]
    TRIGGER_ANGLE = -20
    print(distance_to_trigger([523, 10, 491]))
    
#     TRIGGER = [523, 9, 458, 550, 20, 490]
# TRIGGER_ANGLE = 90
# 550 -> 494