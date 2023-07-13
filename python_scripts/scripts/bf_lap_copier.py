
from dataclasses import dataclass
from enum import IntEnum
import os
import math
import numpy
import random
import struct
import sys
import time

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import SIMULATION_WHEELS_SIZE, ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME
from tminterface.eventbuffer import Event

class ChangeType(IntEnum):
    STEER_DIFF = 0
    TIMING = 1

@dataclass
class Change:
    input : str
    change_type : ChangeType
    proba : float
    start_time : int
    end_time : int
    diff : int

    def __str__(self):
        return f"rule: From {self.start_time} to {self.end_time}ms, change {self.change_type.name} for {self.input} with max diff of {self.diff} and modify_prob={self.proba}"


"""Stuff to add"""

#Randomise bruteforce parameters on each attempt
#If bruteforce range gets extended more than 2 times, need to try with something different (return to previous timestep with more strict tolerance?)
#LOCK_BASE_RUN for at least one attempt
#Filling inputs when solution is close, or fill inputs and do extra bruteforce for the best solution before moving onto next timestep?
    #Want to avoid filling inputs unless absolutely necessary
#Flexible start state, to save time
#Extend max_iter_wait if the solution is close?
#The car prefers to sit behind the correct position because this is easier... is it possible to bias towards solutions that are ahead using velocities?
    #I.e., find the velocity direction, and bias towards positions that are ahead.
    #But is it always advantageous to be ahead?
#Perhaps we need to tolerance to grow more strict over time to stop the solution from slowly falling behind
#Maybe should remove tolerance[2], just let bruteforce reach the end for higher accuracy. Why not if it's easy?
#Check number of inputs in bruteforce range, increase range to include enough inputs if necessary
#When it reaches the finish, just bruteforce for the finish instead of some time
#Search ahead to find the best matching spot and skip the timesteps inbetween?

"""START OF PARAMETERS (you can change here)"""

LAP_TIMES = [41.07, 38.08]
TIME_STEP = 0.1 #secs
MAX_ATTEMPTS = 3
MAX_ITER_WAIT = 500

MOD_PROB = 0.07
MAX_STEERDIFF = 30000
MAX_TIMEDIFF = 30
BRUTE_RANGE = 300 #ms
TOLERANCES = [2.0, 0.8, 0.4]

INITIAL_STEP = 1
BASE_TIME = round((math.ceil((LAP_TIMES[0]+0.01+(INITIAL_STEP-1)*TIME_STEP)/TIME_STEP)*TIME_STEP)*1000)
TIME_MAX = BASE_TIME + LAP_TIMES[1]*1000
TIME_MIN = TIME_MAX

rules = []
rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=MOD_PROB, start_time=(TIME_MAX-BRUTE_RANGE-500), end_time=TIME_MAX, diff=MAX_STEERDIFF))
rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,     proba=MOD_PROB, start_time=(TIME_MAX-BRUTE_RANGE-500), end_time=TIME_MAX, diff=MAX_TIMEDIFF))
rules.append(Change(BINARY_ACCELERATE_NAME, ChangeType.TIMING,proba=MOD_PROB, start_time=(TIME_MAX-BRUTE_RANGE-500), end_time=TIME_MAX, diff=MAX_TIMEDIFF))
rules.append(Change(BINARY_BRAKE_NAME, ChangeType.TIMING,     proba=MOD_PROB, start_time=(TIME_MAX-BRUTE_RANGE-500), end_time=TIME_MAX, diff=MAX_TIMEDIFF))

"""END OF PARAMETERS"""

class MainClient(Client):
    def __init__(self) -> None:
        self.state_min_change = None
        self.restart_state = None
        self.base1_buffer = None
        self.base2_buffer = None
        self.current_buffer = None
        self.nb_iterations = 0
        
        self.best = 10000
        self.cp_count = 0
        self.last_improvement = 0
        self.attempts_counter = 1
        self.scores = [0 for x in range(MAX_ATTEMPTS)]
        self.timestepbest = 10000
        self.timestepbuffer = None
        self.current_timestep = INITIAL_STEP
        
        self.rules = rules
        self.base_time = BASE_TIME
        self.time_max = TIME_MAX
        self.time_min = TIME_MIN
        self.brute_range = BRUTE_RANGE
        self.mod_prob = MOD_PROB
        self.bf_times = []
        self.bf_counter = 0
        self.min_bf_time = TIME_MAX-BRUTE_RANGE-500
        
        self.debug = None

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        print(f'TIMESTEP = {TIME_STEP}, MAX_ATTEMPS = {MAX_ATTEMPTS}')

    def on_simulation_begin(self, iface):
        iface.remove_state_validation()

        self.base1_buffer = iface.get_event_buffer()
        self.base2_buffer = iface.get_event_buffer()
        self.current_buffer = iface.get_event_buffer()
        self.timestepbuffer = iface.get_event_buffer()
        
        self.lowest_time = self.base1_buffer.events_duration
        print(f"Base run time: {self.lowest_time}")
        
        if not (self.time_min <= self.time_max <= self.lowest_time):
            print("ERROR: MUST HAVE 'self.time_min <= self.time_max <= REPLAY_TIME'")
    
    def on_simulation_step(self, iface: TMInterface, _time: int):
        
        #Current time in iteration
        self.current_time = _time
        
        #Earliest state needed for reaching base_time and getting Target values
        if not self.restart_state and self.current_time == self.base_time - 10:
            self.restart_state = iface.get_simulation_state()
        
        #State just before self.time_min to go back to each iteration
        if not self.state_min_change and self.current_time == 77000:
            self.state_min_change = iface.get_simulation_state()
        
        #Obtain information about wheels touching ground for first two laps
        if self.current_timestep == INITIAL_STEP and self.nb_iterations == 0 and self.current_time <= 1000*(LAP_TIMES[0]+LAP_TIMES[1]) and self.current_time >= 0:
            state = iface.get_simulation_state()
            car.update(state)
            
            if car.wheels > 0:
                self.bf_times.insert(self.bf_counter, self.current_time)
                self.bf_counter += 1
        
        #Find car state at corresponding moment in Lap 2
        if self.current_time == self.base_time and self.best == 10000:
            state = iface.get_simulation_state()
            self.TarPos = state.position
            self.TarVel = state.velocity
            self.TarYaw, self.TarPit, self.TarRol = state.yaw_pitch_roll
            print(f"Target position: {self.TarPos}")
        
        #Check if solution is better
        if self.time_min <= self.current_time <= self.time_max:
            
            state = iface.get_simulation_state()
            car.update(state)
            
            if self.is_better(state):
                
                self.best = self.current
                self.last_improvement = self.nb_iterations
                self.base1_buffer = self.current_buffer.copy()
                self.base1_buffer.events = [Event(ev.time, ev.data) for ev in self.current_buffer.events]
                
                print(f"Time: {self.current_time}, Score: {self.best}, Iteration: {self.last_improvement}")
                
                if self.current < self.timestepbest:
                    self.timestepbest = self.current
                    
                    self.timestepbuffer.clear()
                    self.timestepbuffer = self.current_buffer.copy()
                    self.timestepbuffer.events = [Event(ev.time, ev.data) for ev in self.current_buffer.events]
                
                if self.timestepbest < TOLERANCES[2]:
                    self.start_new_attempt(iface)
                else:
                    self.start_new_iteration(iface)
        
        #If not better, start new iteration
        if self.time_max < self.current_time:
            self.start_new_iteration(iface)
    
    def is_better(self, state=""):
        
        PosDiff = abs(car.x - self.TarPos[0])*5 + abs(car.y - self.TarPos[1]) + abs(car.z - self.TarPos[2])*5
        VelDiff = abs(car.vel_x - self.TarVel[0])*5 + abs(car.vel_y - self.TarVel[1]) + abs(car.vel_z - self.TarVel[2])*5
        OriDiff = abs(car.yaw_rad - self.TarYaw)*30 + abs(car.pitch_rad - self.TarPit)*30 + abs(car.roll_rad - self.TarRol)*30
        
        self.current = PosDiff + VelDiff + OriDiff
        
        if self.best == -1:
            return True
        elif self.best < 2.0:
            min_diff = 0.01
        elif self.best < 5.0:
            min_diff = 0.1
        elif self.best < 30.0:
            min_diff = 1.0
        else:
            min_diff = 5.0
        
        return self.current < self.best - min_diff
    
    def start_new_iteration(self, iface):
        
        if self.nb_iterations - self.last_improvement > MAX_ITER_WAIT:
            self.start_new_attempt(iface)
            
        else:
            self.cp_count = -1
            if not self.state_min_change:
                print("no self.state_min_change to rewind to")
                sys.exit()
            
            self.randomize_inputs()
            iface.set_event_buffer(self.current_buffer)
            
            if self.nb_iterations == 0 and self.attempts_counter == 1:
                iface.rewind_to_state(self.restart_state)
            else:
                iface.rewind_to_state(self.state_min_change)
            
            self.nb_iterations += 1
            if self.nb_iterations % 1000 == 0:
                print(f"{self.nb_iterations=}")
            
    
    def start_new_attempt(self, iface):
        
        if self.attempts_counter > 0:
            self.scores[self.attempts_counter-1] = self.best
        
        self.attempts_counter += 1
        
        if self.timestepbest < TOLERANCES[1]:
            print(f"{self.scores}")
            self.save_result(f"{self.timestepbest}", iface)
            self.time_step_failed = 0
            self.start_next_time_step(iface)
            
        elif self.attempts_counter > MAX_ATTEMPTS:
            if self.timestepbest < TOLERANCES[0]:
                print(f"{self.scores}")
                self.save_result(f"{self.timestepbest}", iface)
                self.time_step_failed = 0
                self.start_next_time_step(iface)
            else:
                self.time_step_failed = 1
                self.start_next_time_step(iface)
            
        else:
            self.best = 10000
            self.last_improvement = 0
            self.nb_iterations = 0
            self.current = 10000
            
            self.base1_buffer = self.base2_buffer.copy()
            self.base1_buffer.events = [Event(ev.time, ev.data) for ev in self.base2_buffer.events]
            
            print(f"Attempt number: {self.attempts_counter}")
            
            self.start_new_iteration(iface)
    
    def start_next_time_step(self, iface):
        
        self.attempts_counter = 0
        
        if self.time_step_failed == 0:
            self.base2_buffer = self.timestepbuffer.copy()
            self.base2_buffer.events = [Event(ev.time, ev.data) for ev in self.timestepbuffer.events]
            
            self.current_timestep += 1
            self.brute_range = BRUTE_RANGE
            self.mod_prob = MOD_PROB
        else:
            self.brute_range += 500
            self.mod_prob = self.mod_prob*0.7
        
        self.scores = [0 for x in range(MAX_ATTEMPTS)]
        self.timestepbest = 10000
        self.timestepbuffer.clear()
        
        self.base_time = round((math.ceil((LAP_TIMES[0]+0.01+(self.current_timestep-1)*TIME_STEP)/TIME_STEP)*TIME_STEP)*1000)
        self.time_max = round(self.base_time + LAP_TIMES[1]*1000)
        self.time_min = round(self.time_max)
        
        wheel_ind = round(next(i for i,v in enumerate(self.bf_times) if v >= self.base_time) - self.brute_range/10)
        self.min_bf_time = round(self.bf_times[wheel_ind] + LAP_TIMES[1]*1000)
        
        self.rules = []
        self.rules.append(Change(ANALOG_STEER_NAME, ChangeType.STEER_DIFF, proba=self.mod_prob, start_time=self.min_bf_time, end_time=self.time_max, diff=MAX_STEERDIFF))
        self.rules.append(Change(ANALOG_STEER_NAME, ChangeType.TIMING,     proba=self.mod_prob, start_time=self.min_bf_time, end_time=self.time_max, diff=MAX_TIMEDIFF))
        self.rules.append(Change(BINARY_ACCELERATE_NAME, ChangeType.TIMING,proba=self.mod_prob, start_time=self.min_bf_time, end_time=self.time_max, diff=MAX_TIMEDIFF))
        self.rules.append(Change(BINARY_BRAKE_NAME, ChangeType.TIMING,     proba=self.mod_prob, start_time=self.min_bf_time, end_time=self.time_max, diff=MAX_TIMEDIFF))
        
        print(f"\nCurrent time step: {self.current_timestep}, Lap 2 time: {self.base_time}, Bruteforce range: {self.min_bf_time} - {self.time_max}")
        self.start_new_attempt(iface)
    
    def randomize_inputs(self):
        
        # Restore best inputs in current attempt
        self.current_buffer = self.base1_buffer.copy()
        self.current_buffer.events = [Event(ev.time, ev.data) for ev in self.base1_buffer.events]
        
        # if self.current_timestep > 1 and self.nb_iterations < 5:
            # print(f"{self.nb_iterations}, {self.cp_count}, {self.last_improvement}, {self.best}, {self.current}, {self.attempts_counter}")
        
        # Apply rules to self.current_buffer.events
        if self.nb_iterations > 1:
            for rule in self.rules:
                events = self.current_buffer.find(event_name=rule.input)
                last_steer = 0
                for event in events:
                    event_realtime = event.time - 100010
                    
                    if rule.start_time <= event_realtime <= rule.end_time:
                        
                        if random.random() < rule.proba:
                            if rule.change_type == ChangeType.STEER_DIFF:
                                event.analog_value = event.analog_value + random.randint(-rule.diff, rule.diff)
                                event.analog_value = min(event.analog_value, 65536)
                                event.analog_value = max(event.analog_value, -65536)
                            
                            if rule.change_type == ChangeType.TIMING:
                                event.time += random.randint(-rule.diff/10, rule.diff/10)*10

                    if ANALOG_STEER_NAME == self.base1_buffer.control_names[event.name_index]:
                        last_steer = event.analog_value
    
    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        self.cp_count = current
        iface.prevent_simulation_finish()
    
    def save_result(self, result_name, iface):
        res_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + "resultbest.txt"
        with open(res_file, "w") as f:
            f.write(f"# Current time: {self.time_max}, Score: {self.timestepbest}, Time step: {self.current_timestep}\n")
            f.write("0 speed 100")
            f.write("77000 speed 1")
            f.write(self.timestepbuffer.to_commands_str())
    
class Car():
    def update(self, state):
        self.state = state
        
        self.position = state.position
        self.x, self.y, self.z = state.position
        self.yaw_rad, self.pitch_rad, self.roll_rad = state.yaw_pitch_roll
        self.vel_x, self.vel_y, self.vel_z = state.velocity
        self.speed_mph = numpy.linalg.norm(state.velocity)

        self.yaw_deg   = self.yaw_rad   * 180 / math.pi
        self.pitch_deg = self.pitch_rad * 180 / math.pi
        self.roll_deg  = self.roll_rad  * 180 / math.pi
        self.speed_kmh = self.speed_mph * 3.6
        
        self.wheels=self.get_nb_wheels_on_ground()

        self.stunts_score = int.from_bytes(state.player_info[724:724+4], byteorder='little')
        if self.stunts_score > 1000000:
            self.stunts_score = 0
    
    def get_nb_wheels_on_ground(self):
        nb_wheels_on_ground = 0
        
        for i in range(4):
            current_offset = (SIMULATION_WHEELS_SIZE // 4) * i
            hasgroundcontact = struct.unpack('i', self.state.simulation_wheels[current_offset+292:current_offset+296])[0]
            if hasgroundcontact:
                nb_wheels_on_ground += 1

        return nb_wheels_on_ground

car = Car()

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
