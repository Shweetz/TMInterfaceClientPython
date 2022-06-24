import math
import os
import random
import sys
import time

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME, BINARY_RESPAWN_NAME, BINARY_RACE_FINISH_NAME
from tminterface.eventbuffer import EventBufferData
from tminterface.commandlist import CommandList, InputCommand, InputType

from SUtil import Input, Change, Rule, Eval, Optimize, MinMax, Car, Goal, get_dist_2_points, ms_to_sec, sec_to_ms, add_events_in_buffer, to_sec
from save_load_state import load_state, save_state

rules = []

"""START OF PARAMETERS (you can change here)"""

LOAD_INPUTS_FROM_FILE = ""
LOAD_REPLAY_FROM_STATE = ""
LOCK_BASE_RUN = False

##### RULES ######

FILL_INPUTS = True
start = "0"
end   = "7.30"
# end   = "17.97"
# TIME_BEFORE = -500
# TIME_AFTER  = 0
TIME_BEFORE = 0
TIME_AFTER  = 0

if FILL_INPUTS:
    proba = 0.01
else:
    proba = 0.5
    rules.append(Rule(Input.STEER, Change.TIMING, proba=proba, start_time=start, end_time=end, diff=50))

rules.append(Rule(Input.STEER, Change.STEER_, proba=proba, start_time=start, end_time=end, diff=2000))
# rules.append(Rule(Input.STEER, Change.STEER_, proba=proba, start_time="1:16.00", end_time=end, diff=65536))
# rules.append(Rule(Input.UP___, Change.TIMING, proba=0.1, start_time=start, end_time=end, diff=50))
# rules.append(Rule(Input.DOWN_, Change.TIMING, proba=0.1, start_time=start, end_time=end, diff=50))

##### eval & parameter #####

eval = Eval.TIME
parameter = Optimize.CUSTOM

# eval == Eval.TIME:
TIME = end
TIME_MIN = int(sec_to_ms(TIME)) + TIME_BEFORE
TIME_MAX = int(sec_to_ms(TIME)) + TIME_AFTER

# eval == Eval.CP:
CP_NUMBER = 32

# parameter == Optimize.DISTANCE:
# POINT_POS = [495, 73, 80] # multilap
# POINT_POS = [64, 95, 547] # landing first ground cp
# POINT_POS = [784, 24, 931] # last ground cp bugcp
# POINT_POS = [784, 26, 942] # last ground cp not bugcp
# POINT_POS = [48, 50, 304] # 2nd to last ring
# POINT_POS = [50, 30, 150] # flat between last 2 rings
# POINT_POS = [50, 26, 100] # nb flat before last ring
# POINT_POS = [78, 75, 81] # last ring
# POINT_POS = [20, 65, 547]

POINT_POS = [495, 73, 80] # multilap

##### OTHER STUFF #####

# Min diff to consider an improvement worthy
min_diff = 0

p = 0.5
steer_equal_last_input_proba = p # proba to make a steer equal to last steer
steer_zero_proba = p # proba to set steer to 0 instead of changing direction left/right
steer_full_proba = p

FORMAT_DECIMAL = True

"""END OF PARAMETERS"""

for rule in rules:
    rule.init()

lowest_poss_change = min([c.start_time for c in rules])
highest_poss_change = max([c.end_time for c in rules])

if not lowest_poss_change <= highest_poss_change:
    print("ERROR: MUST HAVE 'lowest_poss_change <= highest_poss_change'")


class MainClient(Client):
    def __init__(self) -> None:
        self.state_min_change = None
        self.pre_rewind_buffer = None
        self.begin_buffer = None
        self.current_buffer = None
        self.nb_iterations = 0
        self.cp_count = 0
        self.force_reject = False
        self.car = None
        self.best_car = None

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller none')
        print(f"Randomizing inputs between {lowest_poss_change} and {highest_poss_change}")
        iface.execute_command("load result.txt")
        for rule in rules:
            print(rule)

    def on_deregistered(self, iface: TMInterface) -> None:
        print(f'Deregistered from {iface.server_name}')

    def on_simulation_begin(self, iface):
        iface.remove_state_validation()

        self.begin_buffer = iface.get_event_buffer()
        self.lowest_time = self.begin_buffer.events_duration

        if eval == Eval.TIME:
            if not (TIME_MIN <= TIME_MAX <= self.lowest_time):
                print("ERROR: MUST HAVE 'TIME_MIN <= TIME_MAX <= REPLAY_TIME'")

            iface.set_simulation_time_limit(TIME_MAX + 10)

        # Fill begin_buffer
        if LOAD_INPUTS_FROM_FILE:
            self.pre_rewind_buffer = EventBufferData(self.lowest_time)
            self.pre_rewind_buffer.control_names = self.begin_buffer.control_names
            self.load_inputs_from_file()
            # print(f"{len(self.begin_buffer.events)=}")
            # if not LOAD_REPLAY_FROM_STATE:
            # iface.set_event_buffer(self.begin_buffer) # COMMENT FOR PARTIAL BUFFER AND DELETE FOR RUN/SIMU STATES

            # print(f"buffer 1: len={len(self.pre_rewind_buffer.events)}")
            # print(self.pre_rewind_buffer.to_commands_str())
            # print(f"buffer 2: len={len(self.begin_buffer.events)}")
            # print(self.begin_buffer.to_commands_str())

        # else:
        #     # input command sorted
        #     # dichotomy dans les input command
        #     # trouver l'index de séparation
        #     # prerewind = [:i] et begin = [i:]
        #     self.pre_rewind_buffer = EventBufferData(self.lowest_time)
        #     self.pre_rewind_buffer.control_names = self.begin_buffer.control_names

        if FILL_INPUTS:
            self.fill_inputs(lowest_poss_change, highest_poss_change)

        self.current_buffer = EventBufferData(self.lowest_time)
        self.current_buffer.control_names = self.begin_buffer.control_names
        self.current_buffer = self.begin_buffer.copy() # copy avoids timeout?
        
        # print("aaa")
        # print(load_state(os.path.expanduser('~/Documents') + "/TMInterface/States/" + "zaz.bin").time)
        # print(load_state(os.path.expanduser('~/Documents') + "/TMInterface/States/" + "state1.98.bin").time)
        # print("on_simulation_begin end")
        pass
        
    def on_simulation_step(self, iface: TMInterface, _time: int):
        # print("on_simulation_step start")
        self.race_time = _time

        # if _time == 2000:
        #     iface.set_input_state(sim_clear_buffer=False, accelerate=False)
        # if _time == 2010:
        #     iface.set_input_state(sim_clear_buffer=False, accelerate=True)

        if not self.state_min_change:
            # buffer = iface.get_event_buffer()
            # events = buffer.find(time=self.race_time)
            # for event in events:
            #     print(f"{event.time - 100010} - {event.analog_value}")
                
            if _time == 0 and LOAD_REPLAY_FROM_STATE:
                self.load_replay_from_state(iface)

            # if LOAD_INPUTS_FROM_FILE and not LOAD_REPLAY_FROM_STATE:
            #     if self.race_time % 10000 == 0:
            #         sys.stdout.write(f"\rSimulating base run... {int(self.race_time/1000)}sec")
            #         sys.stdout.flush()
            #     if self.race_time == lowest_poss_change - 10:
            #         print()
            #         print(f"Simulation done")
                    
            #         # This line sets base run as the inputs file instead of the replay
            #         # iface.set_event_buffer(self.begin_buffer)
            # else:
            #     # When loading inputs from a long replay, we can't load them all at the start because TMI timeout
            #     # So we load the inputs when they happen -> doesn't work with simu save state
            #     # events_at_time = self.begin_buffer.find(time=self.race_time)
            #     # for event in events_at_time:
            #     #     add_events_in_buffer(events_at_time, self.current_buffer)
            #     pass

            # if self.race_time == lowest_poss_change - 10:
            #     iface.set_event_buffer(self.begin_buffer) # COMMENT FOR PARTIAL BUFFER AND DELETE FOR RUN/SIMU STATES

            if self.race_time == lowest_poss_change - 10:
                # Store state to rewind to for every iteration, for now it is earliest possible input change
                # lowest_poss_change-10 because state contains inputs and we don't update state with 1st input
                self.state_min_change = iface.get_simulation_state()

                print(f"self.state_min_change created at {ms_to_sec(self.race_time)}")

                # self.state_file = os.path.expanduser('~/Documents') + "/TMInterface/States/" + "zaz.bin"
                # save_state(self.state_min_change, self.state_file)
                # iface.set_event_buffer(self.begin_buffer) # COMMENT FOR PARTIAL BUFFER AND DELETE FOR RUN/SIMU STATES

        if self.is_eval_time():
            # print("eval_time")
            state = iface.get_simulation_state()
            # state.timee = _time
            if self.is_better(state):
                # self.best_state = state
                self.best_car = self.car
                
                if self.nb_iterations == 0:
                    if LOAD_INPUTS_FROM_FILE:
                        # print() # after write/flush
                        # print(f"base = {self.race_time}")
                        pass
                else:
                    # print(f"FOUND IMPROVEMENT: {race_time}")
                    if not LOCK_BASE_RUN:
                        self.begin_buffer.events = self.current_buffer.events
                
                    # Save inputs to file
                    self.save_result()

        # Wait until the end of eval time before rewinding, in case an even better state is found later on
        if self.is_past_eval_time():

            # TMP TEST
            # self.save_result()
            # sys.exit()
            # print("past eval_time")
            self.start_new_iteration(iface)
        
    def is_better(self, state):
        self.car = Car(self.race_time)
        self.car.update(state)

        # if there's no best car, then it's base run
        base_run = not self.best_car
            
        if parameter == Optimize.TIME:
            return self.is_earlier(base_run, min_diff)

        if parameter == Optimize.DISTANCE:
            return self.is_closer(base_run, min_diff)

        if parameter == Optimize.VELOCITY:
            return self.is_faster(base_run, min_diff)

        if parameter == Optimize.CUSTOM:
            return self.is_custom(base_run, min_diff)

        return False

    def is_custom(self, base_run, min_diff=0):
        """Evaluates if the iteration is better when parameter == Optimize.CUSTOM"""
        # if base_run:
        #     car = self.best_car
        # else:
        #     car = self.car

        # condition
        # turtle
        # if not abs(self.car.pitch_deg) > math.pi/2:
        #     return False
        # if not abs(self.car.pitch_rad) + abs(self.car.roll_rad) < 1:
        #     return False
        # # print(self.car.y)
        # if not 280 < self.car.x:
        #     return False
        # if not 130 < self.car.y:
        #     return False
        # if not 725 < self.car.z < 733:
        #     return False
        # if not self.car.yaw_deg > 70:
        #     return False
        # if not self.cp_count >= 30:
        #     return False

        # self.car.custom = abs(car.pitch_deg - 90)
        # self.car.custom = self.car._time
        self.car.custom = - self.car.z
        # self.car.custom = get_dist_2_points(POINT_POS, self.car.position, "xz")
        # self.car.custom = self.car.get_speed("xz")
        
        if base_run:
            print(f"Base run custom = {self.car.custom}")
            return True
        elif self.car.custom > self.best_car.custom + min_diff:
            print(f"Improved custom = {self.car.custom}")
            return True

        return False

    def is_custom2(self, base_run, min_diff=0):
        """Evaluates if the iteration is better when parameter == Optimize.CUSTOM"""        
        # Goal 1: max car.y until car.y > 49
        # Goal 2: min car.x
        if base_run:
            print(f"Base run custom y = {self.car.y}")
            return True
        else:
            if self.best_car.y < 48.5:
                if self.car.y > self.best_car.y + min_diff:
                    print(f"Improved custom y = {self.car.y}")
                    return True
            else:
                if self.car.y > 48.5 and self.car.x < self.best_car.x - min_diff:
                    print(f"Improved custom x = {self.car.x}")
                    return True
                    
        return False

    def is_custom3(self, base_run, min_diff=0):
        """Evaluates if the iteration is better when parameter == Optimize.CUSTOM"""        
        # Goal 1: max car.y until car.y > 49
        # Goal 2: min car.x until car.x < 414
        # Goal 3: min time
        # condition
        # if not 138 < self.car.x:
        #     return False
        # if not 63 < self.car.y:
        #     return False
        if not 102 < self.car.z < 104:
            return False
        # if not self.cp_count >= 73:
        #     return False
            
        # if self.car_time == int(sec_to_ms("18:47.50")) and 55 < self.car.y:
        #     self.force_reject = True
        #     return False

        goals = []
        goals.append(Goal("x", MinMax.MIN, 0))
        goals.append(Goal("_time", MinMax.MIN, 0))

        if base_run:
            for goal in goals:
                print(f"Base run custom {goal.variable} = {getattr(self.car, goal.variable)}")
            return True
        else:
            for goal in goals:
                if goal.achieved(self.best_car):
                    if goal.achieved(self.car):
                        continue
                    else:
                        return False
                else:
                    if goal.closer(self.car, self.best_car, min_diff):
                        print(f"Improved custom {goal.variable} = {getattr(self.car, goal.variable)}")
                        return True
                    else:
                        return False
                    
        return False
        
    def is_custom4(self, base_run, min_diff=0):
        """Evaluates if the iteration is better when parameter == Optimize.CUSTOM"""

        # condition
        if not self.car.nb_wheels_on_ground > 0: # 0 wheel on ground
            return False
        if not self.cp_count >= CP_NUMBER:
            return False        
        if not  25 < self.car.x < 999:
            return False
        if not  25 < self.car.y < 30:
            return False
        # if not 0 < self.car.z < 600:
        #     return False
        # # if not 384 < (self.car.y * 2 + self.car.x) < 390:
        # #     return False
        # if not 450 < self.car.speed_kmh:
        #     return False
        # 0 384
        # 30 324
        # 60 264
        # if not self.cp_count >= 5:
        #     return False
        # if not self.car.vel_z < 0:
        #     return False
        # if not 200 < self.car.speed_kmh:
        #     return False

        slope_pitch = 0
        slope_roll = 0

        target_yaw = math.atan2(self.car.vel_x, self.car.vel_z) * 180/math.pi
        target_pitch = (math.pi/2 + math.cos(self.car.yaw_rad) * slope_pitch - math.sin(self.car.yaw_rad) * slope_roll) * 180/math.pi
        target_roll = (math.sin(self.car.yaw_rad) * slope_pitch + math.cos(self.car.yaw_rad) * slope_roll) * 180/math.pi
        # target_pitch = 90
        # target_roll = 0

        # self.current = self.car.speed_kmh - self.car.y - abs(self.car.pitch_deg - 90) - abs(self.car.roll_deg) - abs(self.car.yaw_deg - )
        self.car.custom = abs(self.car.yaw_deg - target_yaw) + abs(self.car.pitch_deg - target_pitch) + abs(self.car.roll_deg - target_roll)
        # if self.best == -1:
        #     return True
        # return self.current < self.best

        if base_run:
            print(f"Base run custom = {self.car.custom}")
            return True
        elif self.car.custom < self.best_car.custom - min_diff:
            print(f"Improved custom = {self.car.custom}")
            return True

        return False
        
    def is_custom5(self, base_run, min_diff=0):
        """Evaluates if the iteration is better when parameter == Optimize.CUSTOM"""

        # condition
        # if not self.cp_count >= CP_NUMBER:
        #     return False      

        self.car.distance = get_dist_2_points(POINT_POS, self.car.position, "xyz")

        if base_run:
            print(f"Base run distance = {math.sqrt(self.car.distance)} m")
            return True
        else:
            if self.get_nb_cp(self.car.state) < self.get_nb_cp(self.best_car.state):
                return False
            elif self.get_nb_cp(self.best_car.state) < CP_NUMBER:
                if self.get_nb_cp(self.car.state) >= CP_NUMBER:
                    print(f"Finished = {ms_to_sec(self.car._time - 10)}")
                    return True
                elif self.car.distance < self.best_car.distance - min_diff:
                    # if not 65 > self.car.y:
                    #     return False
                    print(f"Improved distance = {math.sqrt(self.car.distance)} m")
                    return True
            else:
                if self.get_nb_cp(self.car.state) >= CP_NUMBER:
                    if self.car._time < self.best_car._time - min_diff:
                        print(f"Improved time = {ms_to_sec(self.car._time - 10)}")
                        return True
        
        return False

    def is_earlier(self, base_run, min_diff=0):
        # if base_run:
        #     car = self.best_car
        # else:
        #     car = self.car

        # if self.best_car and self.car._time < self.best_car._time:
        #     print(f"FOUND IMPROVEMENT: {self.car._time}")
        #     return True

        # condition
        # if not self.car.x < 380:
        #     return False
        # if not 100 < self.car.z < 125:
        #     return False
        # if abs(self.car.pitch_rad) > 0.1:
        #     return False
        # if not 91.5 < self.car.y:
        #     return False
        # if not self.car.vel_x > 5:
        #     return False
        if not self.cp_count >= CP_NUMBER:
            return False  

        if base_run:
            print(f"Base run time = {ms_to_sec(self.car._time - 10)}")
            return True
        elif self.car._time < self.best_car._time - min_diff:
            print(f"Improved time = {ms_to_sec(self.car._time - 10)}")
            return True
        
        return False
    
    def is_closer(self, base_run, min_diff=0, axis="xyz"):
        # if base_run:
        #     car = self.best_car
        # else:
        #     car = self.car

        if not self.cp_count >= CP_NUMBER:
            return False        
        if 67 < self.car.x and 130 < self.car.z:
            return False       
        if not 25 < self.car.y:
            return False
        # if not 500 < self.car.speed_kmh:
        #     return False

        self.car.distance = get_dist_2_points(POINT_POS, self.car.position, axis)
        
        # min_diff = 0

        if base_run:
            print(f"Base run distance = {math.sqrt(self.car.distance)} m")
            return True
        elif self.car.distance < self.best_car.distance - min_diff:
            sqrt = math.sqrt(self.car.distance)
            if sqrt < math.sqrt(self.best_car.distance) - min_diff:
                print(f"Improved distance = {sqrt} m")
                return True
        
        return False
        
    def is_faster(self, base_run, min_diff=0):
        # if base_run:
        #     car = self.best_car
        # else:
        #     car = self.car

        self.car.velocity = min(self.car.speed_kmh, 1000)

        if base_run:
            print(f"Base run velocity = {self.car.velocity} kmh")
            return True
        elif self.car.velocity > self.best_car.velocity + min_diff:
            print(f"Improved velocity = {self.car.velocity} kmh")
            return True
        
        return False

    def is_eval_time(self):
        if eval == Eval.TIME:
            # print(self.current_time)
            if TIME_MIN <= self.race_time <= TIME_MAX:
                return True
        if eval == Eval.CP:
            if CP_NUMBER <= self.cp_count:
                return True
        
        return False

    def is_past_eval_time(self):
        if eval == Eval.TIME:
            if TIME_MAX <= self.race_time:
                return True

        if eval == Eval.CP:
            if CP_NUMBER <= self.cp_count or (self.best_car and self.race_time == self.best_car._time):
                # self.cp_count = 0
                return True
        
        if self.force_reject:
            self.force_reject = False
            return True
        
        return False

    def start_new_iteration(self, iface):
        # print("start_new_iteration")
        """Randomize and rewind"""
        self.randomize_inputs()
        iface.set_event_buffer(self.current_buffer)

        if not self.state_min_change:
            print("no self.state_min_change to rewind to")
            sys.exit()
        iface.rewind_to_state(self.state_min_change)

        # Recompute number of CPs
        self.cp_count = self.get_nb_cp(self.state_min_change)
        # Recomputation bug? Try -1, but need to investigate
        # self.cp_count = -1
        # print(f"{self.cp_count=}")

        self.nb_iterations += 1
        if self.nb_iterations in [1, 10, 100] or self.nb_iterations % 1000 == 0:
            print(f"{self.nb_iterations=}")

    def randomize_inputs(self):
        """Restore base run events (with deepcopy) and randomize them using rules.
        Deepcopy can't use EventBufferData.copy() because events is deepcopied but not the individual events"""
        
        # Restore events from base run (self.begin_buffer.events) in self.current_buffer.events using deepcopy
        self.current_buffer.clear()
        add_events_in_buffer(self.begin_buffer.events, self.current_buffer)
        # for event in self.begin_buffer.events:
        #     event_time = event.time - 100010
        #     event_name = self.begin_buffer.control_names[event.name_index]
        #     event_value = event.analog_value if "analog" in event_name else event.binary_value
        #     self.current_buffer.add(event_time, event_name, event_value)

        # Apply rules to self.current_buffer.events
        for rule in rules:
            # only inputs that match the rule (ex: steer)
            # try:
            #     print(rule.input)
            #     print(rule.input.name)
            #     print(rule.input.value)
            # except:
            #     pass
            events = self.current_buffer.find(event_name=rule.input.value)
            last_steer = 0
            for event in events:
                event_realtime = event.time - 100010
                # event in rule time
                if rule.start_time <= event_realtime <= rule.end_time:
                    # event proba
                    if random.random() < rule.proba:
                        # event type
                        if rule.change_type == Change.STEER_:
                            if random.random() < steer_equal_last_input_proba:
                                event.analog_value = last_steer
                            else:
                                new_steer = event.analog_value + random.randint(-rule.diff, rule.diff)
                                # if diff makes steer change direction (left/right), try 0
                                if (event.analog_value < 0 < new_steer or new_steer < 0 < event.analog_value) and random.random() < steer_zero_proba:
                                    event.analog_value = 0
                                else:
                                    event.analog_value = new_steer

                                # steer should stay in [-65536; 65536]
                                event.analog_value = min(event.analog_value, 65536)
                                event.analog_value = max(event.analog_value, -65536)
                                
                        if rule.change_type == Change.TIMING:
                            # ms -> 0.01
                            diff = random.randint(-rule.diff/10, rule.diff/10)
                            # 0.01 -> ms
                            event.time += diff*10
                            
                            # event.time shall stay in rule start/end time
                            event.time = min(event.time, rule.end_time + 100010)
                            event.time = max(event.time, rule.start_time + 100010)

                if Input.STEER.name == self.begin_buffer.control_names[event.name_index]:
                    last_steer = event.analog_value
        
    def fill_inputs(self, start_fill=0, end_fill=0):
        """Fill inputs between start_fill and end_fill included"""
        if end_fill == 0:
            end_fill = self.begin_buffer.events_duration
        
        # print(f"fill_inputs(self, {start_fill}, {end_fill})")
        # Find start steering (if start fill_inputs not on a steering change)
        if LOAD_INPUTS_FROM_FILE:
            buffer = self.pre_rewind_buffer
        else:
            buffer = self.begin_buffer

        curr_steer = 0
        for event_time in range(start_fill, -10, -10):
            # print(f"event_time={event_time}")
            events_at_time = buffer.find(time=event_time, event_name=ANALOG_STEER_NAME)
            if len(events_at_time) > 0:
                if len(events_at_time) > 1:
                    print(f"dirty inputs at {event_time}: len={len(events_at_time)}")
                curr_steer = events_at_time[-1].analog_value
                # print(f"start steer={curr_steer}")
                break

        # Fill inputs
        for event_time in range(start_fill, end_fill+10, 10):
            events_at_time = self.begin_buffer.find(time=event_time, event_name=ANALOG_STEER_NAME)
            if len(events_at_time) > 0:
                if len(events_at_time) > 1:
                    print(f"dirty inputs at {event_time}: len={len(events_at_time)}")
                curr_steer = events_at_time[-1].analog_value
            else:
                self.begin_buffer.add(event_time, ANALOG_STEER_NAME, curr_steer)

    def unfill_inputs(self, buffer: EventBufferData):
        # return buffer
        buffer.sort()

        unfilled_buffer = EventBufferData(buffer.events_duration)
        unfilled_buffer.control_names = buffer.control_names

        last_steer = None
        for event in buffer.find():
            if Input.STEER.value == buffer.control_names[event.name_index]:
                if event.analog_value == last_steer:
                    continue
                else:
                    last_steer = event.analog_value

            unfilled_buffer.events.append(event)

        return unfilled_buffer
        
    def save_result(self, time_found="", file_name="result.txt"):
        if time_found == "":
            time_found = self.race_time
        
        # Gather inputs        
        inputs_str = ""
        # if LOAD_INPUTS_FROM_FILE:
        if self.pre_rewind_buffer:
            # inputs before inputs_min_time
            # unfilled_buffer = self.unfill_inputs(self.pre_rewind_buffer)
            inputs_str += self.unfill_inputs(self.pre_rewind_buffer).to_commands_str()
            inputs_str += "\n"

        # unfilled_buffer = self.unfill_inputs(self.current_buffer)
        inputs_str += self.unfill_inputs(self.current_buffer).to_commands_str()
        
        # Convert inputs
        if FORMAT_DECIMAL:
            inputs_str = to_sec(inputs_str)
            
        # Header
        inputs_str = f"# Time: {time_found}, iterations: {self.nb_iterations}\n" + inputs_str
        
        # Footer
        inputs_str += "\n"

        if LOAD_REPLAY_FROM_STATE:
            inputs_str += f"0 load_state {LOAD_REPLAY_FROM_STATE}\n"
        else:
            # inputs_str += f"0 set draw_game false\n"
            inputs_str += f"0 set speed 100\n"
            # inputs_str += f"{start} set draw_game true\n"
            inputs_str += f"{ms_to_sec(int(sec_to_ms(end)) - 2500)} set speed 1\n"

        # Write inputs in file
        res_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + file_name
        with open(res_file, "w") as f:
            f.write(inputs_str)

    def load_inputs_from_file(self):
        """Load a inputs to bruteforce from a file instead of a replay"""
        print(f"Loading inputs from {LOAD_INPUTS_FROM_FILE}")
        
        # Fill the buffers
        self.begin_buffer.clear()
        self.pre_rewind_buffer.clear()

        inputs_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + LOAD_INPUTS_FROM_FILE
        cmdlist = CommandList(open(inputs_file, 'r'))
        commands = [cmd for cmd in cmdlist.timed_commands if isinstance(cmd, InputCommand)]

        for command in commands:
            if   command.input_type == InputType.UP:      command.input = BINARY_ACCELERATE_NAME
            elif command.input_type == InputType.DOWN:    command.input = BINARY_BRAKE_NAME
            elif command.input_type == InputType.LEFT:    command.input = BINARY_LEFT_NAME
            elif command.input_type == InputType.RIGHT:   command.input = BINARY_RIGHT_NAME
            elif command.input_type == InputType.RESPAWN: command.input = BINARY_RESPAWN_NAME
            elif command.input_type == InputType.STEER:   command.input = ANALOG_STEER_NAME
            else: print(f"{command.input_type=}"); continue

            if command.timestamp < lowest_poss_change:
                self.begin_buffer.add(command.timestamp, command.input, command.state)
            else:
                self.begin_buffer.add(command.timestamp, command.input, command.state)

    def load_replay_from_state(self, iface):
        """Load a save_state to skip the initial simulation up until lowest_poss_change"""
        
        print(f"Loading save_state {LOAD_REPLAY_FROM_STATE}")
        self.state_file = os.path.expanduser('~/Documents') + "/TMInterface/States/" + LOAD_REPLAY_FROM_STATE
        state = load_state(self.state_file)
        # Update self.race_time with time from save_state
        # self.race_time = state.time - 2620
        # state.set
        
        iface.rewind_to_state(state)
        # iface.set_input_state(sim_clear_buffer=False, left=True)

        if lowest_poss_change - 10 < self.race_time:
            print("ERROR: simu save_state time must be at least 1 tick before lowest_poss_change")

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        self.cp_count = current
        if eval == eval.CP:
            # if current == CP_NUMBER:
            #     print(f"Cross CP at {self.race_time}")
            if self.nb_iterations == 0:
                if current == CP_NUMBER:
                    global TIME_MIN
                    global TIME_MAX
                    TIME_MIN = 0 # script won't check before lowest_poss_change anyway
                    TIME_MAX = self.race_time
                    # print(current)
        # print(f'Reached checkpoint {current}/{target}')
        if current == target:
            print(f'Finished the race at {self.race_time}')
            # self.finished = True
            iface.prevent_simulation_finish()

    def get_nb_cp(self, state):
        cp_times = state.cp_data.cp_times
        # self.nb_cp = len([time for (time, _) in cp_times if time != -1])
        # print(f"{current} {self.nb_cp=}")
        return len([time for (time, _) in cp_times if time != -1])

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""
Save replay without save_state?
Problem bruteforce crazy?

ERRORS
Bruteforce replay invalid: 2 respawn on same tick

WARNING
iface.set_event_buffer(self.begin_buffer) # COMMENT FOR PARTIAL BUFFER AND DELETE FOR RUN/SIMU STATES
===> AFTER state_min_change REACHED!!!!!!!!!!!!!!

Bugs
Double start inputs
save_state + finish : ghost en retard ? bruteforce ok ou ko ?

ALED BRAIN
PART 1 - LOAD_STATE - PART 2   - state_min_change - PART 3   - PART ITER
...... - .......... - rep/file - ................ - rep/file - rep/file
...... - .......... - rep      - ................ - rep      - rep       - LOAD_INPUTS_FROM_FILE non
...... - .......... - ........ - ................ - ........ - file      - ATM
...... - .......... - ........ - ................ - file     - ......... - begin_buffer apres min_change
...... - .......... - file     - ................ - ........ - ......... - pre_rewind buffer au start

STATE - INPUTS
STATE
INPUTS
NONE
"""