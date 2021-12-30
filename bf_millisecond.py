
from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

from enum import Enum, auto
import math
import numpy
import sys
from dataclasses import dataclass

class Orientation(Enum):
    Z_UP = 0
    X_DOWN = 1
    Z_DOWN = 2
    X_UP = 3

@dataclass
class ForcedFinishInfo():
    orientation : Orientation
    reversed : bool
    backwards : bool

NB_CP = 2
USE_FFI = False
FFI = ForcedFinishInfo(Orientation.Z_DOWN, False, False)

MIN_OFFSET = -0.17
MAX_OFFSET = 1.08
MIN_OFFSET_BW = -0.4
MAX_OFFSET_BW = 1.3

fin_yaw_z_up = 0
fin_yaw_x_dn = 1.57
fin_yaw_z_dn = 3.14
fin_yaw_x_up = -1.57

# diff par rapport à abs(car_yaw - fin_yaw) = 0
fin_yaw_offset = {}
fin_yaw_offset["0.0"] = 0
fin_yaw_offset["0.1"] = -0.07
fin_yaw_offset["0.2"] = -0.13
fin_yaw_offset["0.3"] = -0.16
fin_yaw_offset["0.4"] = -0.17
fin_yaw_offset["0.5"] = -0.16
fin_yaw_offset["0.6"] = -0.13
fin_yaw_offset["0.7"] = -0.07
fin_yaw_offset["0.8"] = 0
fin_yaw_offset["1.6"] = 1.08
fin_yaw_offset["3.1"] = 0.21
# TODO

# fin x/z
# fin up/down
# car crossing regular/from behind
# car crossing with front/back of car
 
# x/z going up
fin_up_yaw_0 = 9.648

# x/z going down
fin_dw_yaw_0 = 22.35
#A07 : 374.381 < z < 374.429

# x/z going up reversed
fin_up_rev_yaw_0 = 14.35

# x/z going down reversed
fin_dw_rev_yaw_0 = 17.65

# approx nulles
car_length = 4
car_diag = 4.32
car_width = 1.84

front_car = 2.1
back_car = 1.9
diag_front_car = 2.26
diag_back_car = 2.06
side_car = 0.92

@dataclass
class Finish:
    orientation : Orientation
    reversed : bool
    backwards : bool
    
    # def __init__(self, orientation: Orientation, yaw: float):
    #     self.orientation = orientation
    #     self.yaw = yaw
    #     self.compute_coord()

    crossed = False
    
    def compute_dist_car_fin(self, prev_car):
        car_yaw = prev_car.yaw_rad
        self.crossed = False

        # self.placement
        if self.orientation == Orientation.Z_UP or self.orientation == Orientation.X_UP:
            self.placement = fin_up_yaw_0
        if self.orientation == Orientation.X_DOWN or self.orientation == Orientation.Z_DOWN: 
            self.placement = fin_dw_yaw_0

        # self.yaw
        if self.orientation == Orientation.Z_UP:
            self.yaw = 0
        if self.orientation == Orientation.X_DOWN:
            self.yaw = 1.57
        if self.orientation == Orientation.Z_DOWN: 
            self.yaw = 3.14
        if self.orientation == Orientation.X_UP: 
            self.yaw = -1.57
        if self.reversed:
            self.yaw += 3.14
        if self.backwards:
            self.yaw += 3.14

        yaw_diff = abs(car_yaw + self.yaw)
        print(yaw_diff)
        while yaw_diff > 1.6:
            yaw_diff = abs(yaw_diff - 3.14)
        yaw_rounded = round(yaw_diff*10)/10
        
        print(yaw_rounded)

        if self.orientation == Orientation.Z_UP:
            self.dist_to_car = fin_up_yaw_0 - prev_car.z % 32
        if self.orientation == Orientation.X_DOWN:
            self.dist_to_car = prev_car.x % 32 - fin_dw_yaw_0
        if self.orientation == Orientation.Z_DOWN: 
            self.dist_to_car = prev_car.z % 32 - fin_dw_yaw_0
        if self.orientation == Orientation.X_UP:
            self.dist_to_car = fin_up_yaw_0 - prev_car.x % 32

        self.dist_to_car += fin_yaw_offset[str(yaw_rounded)]

        # if self.orientation == Orientation.Z_UP or self.orientation == Orientation.X_UP:
        #     self.dist_to_car = fin_up_yaw_0 + fin_yaw_offset[str(yaw_rounded)]
        # if self.orientation == Orientation.X_DOWN or self.orientation == Orientation.Z_DOWN: 
        #     self.dist_to_car = fin_dw_yaw_0 - fin_yaw_offset[str(yaw_rounded)]
        # if yaw_rounded <= 0.8:
        #     if self.orientation == Orientation.Z_UP or self.orientation == Orientation.X_UP:
        #         self.dist_to_car = fin_up_yaw_0 + fin_yaw_offset[str(yaw_rounded)]
        #     if self.orientation == Orientation.X_DOWN or self.orientation == Orientation.Z_DOWN: 
        #         self.dist_to_car = fin_dw_yaw_0 - fin_yaw_offset[str(yaw_rounded)]
        # else:
        #     print(f"{yaw_rounded=}")
        #     self.dist_to_car = fin_up_yaw_0
        
        print(self.dist_to_car)

        return self.dist_to_car
    
    def compute_fin_time(self, prev_car, _time):
        if self.orientation == Orientation.Z_UP or self.orientation == Orientation.Z_DOWN:
            dist_car_fin = self.compute_dist_car_fin(prev_car)

            return (_time-10)/1000 + dist_car_fin / abs(prev_car.vel_z)
            
        if self.orientation == Orientation.X_UP or self.orientation == Orientation.X_DOWN:
            dist_car_fin = self.compute_dist_car_fin(prev_car)

            return (_time-10)/1000 + dist_car_fin / abs(prev_car.vel_x)

class Car:
    def update(self, state):
        self.x, self.y, self.z = state.position
        self.yaw_rad, self.pitch_rad, self.roll_rad = state.yaw_pitch_roll
        self.vel_x, self.vel_y, self.vel_z = state.velocity
        self.speed_mph = numpy.linalg.norm(state.velocity)

        self.yaw_deg   = self.yaw_rad   * 180 / math.pi
        self.pitch_deg = self.pitch_rad * 180 / math.pi
        self.roll_deg  = self.roll_rad  * 180 / math.pi
        self.speed_kmh = self.speed_mph * 3.6

class MainClient(Client):
    def __init__(self) -> None:
        self.cp_count = -1
        self.cars = {}
        self.finish = Finish(Orientation.Z_UP, False, False)
        # self.finish.compute_coord()

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    # def on_simulation_begin(self, iface):
    #     self.lowest_time = iface.get_event_buffer().events_duration

    def on_run_step(self, iface, _time):
        if _time <= 0:
            return

        state = iface.get_simulation_state()
        # state.velocity = [100, 0, 0]
        # iface.rewind_to_state(state)

        car = Car()
        car.update(state)
        self.cars[_time] = car

        if self.cp_count == NB_CP:
        # if self.finish.crossed:
            # prev_car
            prev_car = self.cars.get(_time-10)
            if not prev_car:
                return

            print(f"{_time-10}: {prev_car.z=}, {prev_car.vel_z=}")
            print(f"{_time}: {car.z=}")

            if USE_FFI:
                finish_info = FFI
            else:
                finish_info = self.guess_ffi(car, prev_car)

            self.finish = Finish(*finish_info)
            # dist_to_fin
            # dist_to_fin = self.finish.compute_dist_car_fin(prev_car.yaw_rad) - (prev_car.z % 32)

            # fin_time
            # fin_time = (_time-10)/1000 + dist_to_fin/prev_car.vel_z

            fin_time = self.finish.compute_fin_time(prev_car, _time)

            # print((_time-10)/1000)
            print(fin_time, math.floor(fin_time*1000)/1000)

            # reset
            self.cp_count = -1
            self.finish.crossed = False
            print()

    def guess_ffi(self, car, prev_car):
        # find correct finish orientation
        min_x = min(car.x, prev_car.x) % 32
        max_x = max(car.x, prev_car.x) % 32
        min_z = min(car.z, prev_car.z) % 32
        max_z = max(car.z, prev_car.z) % 32

        orientation = Orientation.Z_UP
        if min_z < fin_up_yaw_0 + MAX_OFFSET and fin_up_yaw_0 + MIN_OFFSET < max_z:
            orientation = Orientation.Z_UP
            print("FIN Z UP")
        if min_x < fin_dw_yaw_0 + MAX_OFFSET and fin_dw_yaw_0 + MIN_OFFSET < max_x:
            orientation = Orientation.X_DOWN
            print("FIN X DOWN")
        if min_z < fin_dw_yaw_0 + MAX_OFFSET and fin_dw_yaw_0 + MIN_OFFSET < max_z:
            orientation = Orientation.Z_DOWN
            print("FIN Z DOWN")
        if min_x < fin_up_yaw_0 + MAX_OFFSET and fin_up_yaw_0 + MIN_OFFSET < max_x:
            orientation = Orientation.X_UP
            print("FIN X UP")
        if min_z < fin_up_rev_yaw_0 + MAX_OFFSET_BW and fin_up_rev_yaw_0 + MIN_OFFSET_BW < max_z:
            orientation = Orientation.Z_UP
            print("FIN Z UP REV")
        if min_x < fin_dw_rev_yaw_0 + MAX_OFFSET_BW and fin_dw_rev_yaw_0 + MIN_OFFSET_BW < max_x:
            orientation = Orientation.X_DOWN
            print("FIN X DOWN REV")
        if min_z < fin_dw_rev_yaw_0 + MAX_OFFSET_BW and fin_dw_rev_yaw_0 + MIN_OFFSET_BW < max_z:
            orientation = Orientation.Z_DOWN
            print("FIN Z DOWN REV")
        if min_x < fin_up_rev_yaw_0 + MAX_OFFSET_BW and fin_up_rev_yaw_0 + MIN_OFFSET_BW < max_x:
            orientation = Orientation.X_UP
            print("FIN X UP REV")

        # find if car crossed finish the intended direction (not from behind)
        reversed = False
        if orientation == Orientation.Z_UP and prev_car.vel_z < 0:
            reversed = True
            print("Crossing reversed")
        if orientation == Orientation.X_DOWN and prev_car.vel_x > 0:
            reversed = True
            print("Crossing reversed")
        if orientation == Orientation.Z_DOWN and prev_car.vel_z > 0:
            reversed = True
            print("Crossing reversed")
        if orientation == Orientation.X_UP and prev_car.vel_x < 0:
            reversed = True
            print("Crossing reversed")

        # find if car crossed backwards
        backwards = False
        if orientation == Orientation.Z_UP or orientation == Orientation.Z_DOWN:
            if abs(prev_car.yaw_rad) < math.pi/2 and prev_car.vel_z < 0:
                backwards = True
            if abs(prev_car.yaw_rad) > math.pi/2 and prev_car.vel_z > 0:
                backwards = True
        if orientation == Orientation.X_DOWN or orientation == Orientation.X_UP:
            if prev_car.yaw_rad * prev_car.vel_x < 0:
                backwards = True
            # if orientation == Orientation.Z_UP and abs(prev_car.yaw_rad) > math.pi/2:
            #     print("Crossing backwards")
            # if orientation == Orientation.X_DOWN and prev_car.yaw_rad > 0:
            #     print("Crossing backwards")
            # if orientation == Orientation.Z_DOWN and abs(prev_car.yaw_rad) < math.pi/2:
            #     print("Crossing backwards")
            # if orientation == Orientation.X_UP and prev_car.yaw_rad < 0:
            #     print("Crossing backwards")
        
        return [orientation, reversed, backwards]

    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        self.cp_count = current
        if current == target:
            self.finish.crossed = True

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
