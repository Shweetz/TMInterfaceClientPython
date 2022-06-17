
"""
How to use:
- Change 'REPLAY_NAME' in this script with the path of the replay
- Start this script (TMI must be running)
- Validate another replay made on the same map (bruteforce OFF)
- Open 'INPUTS_NAME' file
"""

from copy import deepcopy
import math
import os
import sys
from tminterface.eventbuffer import EventBufferData

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME, BINARY_RESPAWN_NAME, BINARY_RACE_FINISH_NAME
from tminterface.commandlist import CommandList, InputCommand, InputType

import pygbx
from SUtil import to_sec

PRESS = True
REL = False
LEFT = BINARY_LEFT_NAME
RIGHT = BINARY_RIGHT_NAME
DOWN = BINARY_BRAKE_NAME
UP = BINARY_ACCELERATE_NAME
FORMAT_DECIMAL = True

MAX_TIME = 190000
REPLAY_NAME = r"C:\Users\rmnlm\Documents\Trackmania\Tracks\Replays\2022-05-28-14-18-04_A01-Race.Replay.Gbx"
INPUTS_NAME = "guessed_inputs.txt"
CLEAR_INPUTS = True
NB_TICKS = 9

# class State():
#     state = None
#     direction = "straight"
#     up = True
#     down = False

class Pressed():
    """Holds currently pressed inputs"""
    def __init__(self, state_min_change):        
        self.left  = state_min_change.input_left
        self.right = state_min_change.input_right
        self.down  = state_min_change.input_brake
        self.up    = state_min_change.input_accelerate

    def cmd(self, state, input):        
        if input == LEFT:
            self.left = state
        elif input == RIGHT:
            self.right = state
        elif input == DOWN:
            self.down = state
        elif input == UP:
            self.up = state

class Ghost():
    def __init__(self, replay_name):
        self.ghost = self.extract_ghost(replay_name)
        self.records = self.ghost.records
        self.time = (len(self.records) - 1) * 100
        print(f"ghost time={self.time}")

    def extract_ghost(self, filename: str) -> list[int]:
        """Extract ghost from a replay with pygbx"""
        g = pygbx.Gbx(filename)
        ghost = g.get_class_by_id(pygbx.GbxType.CTN_GHOST)
        if not ghost:
            print(f"ERROR: no ghost in {filename=}")
            quit()

        return ghost
    
    def update_next_inputs(self, index):
        self.next_steer = self.records[index].input_steer # left/straight/right
        self.next_up    = self.records[index].input_gas   # bool
        self.next_down  = self.records[index].input_brake # bool

class MainClient(Client):
    def __init__(self) -> None:
        # self.last_ok_state = State()
        self.state_min_change = None
        self.list_changes = []
        self.nb_inputs_change = 0
        self.nb_iterations = 0

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        self.ghost = Ghost(REPLAY_NAME)
        # self.lowest_time = (len(self.ghost.records) - 1) * 100

        # nb_records = len(self.ghost.records)
        # # print(f"{self.lowest_time=}")
        # for i, rec in enumerate(self.ghost.records):
        #     rec.time = i * 10
            # print(rec.time)
            # print(rec.position[0])

    def on_deregistered(self, iface: TMInterface) -> None:
        print(f'Deregistered from {iface.server_name}')

    def on_simulation_begin(self, iface):
        iface.remove_state_validation()

        # self.buffer = iface.get_event_buffer()

        # Fill begin_buffer
        # if LOAD_INPUTS_FROM_FILE:
        #     self.pre_rewind_buffer = EventBufferData(self.lowest_time)
        #     self.pre_rewind_buffer.control_names = self.begin_buffer.control_names
        #     self.load_inputs_from_file()
        state = iface.get_event_buffer()
        self.current_buffer = EventBufferData(state.events_duration)
        self.current_buffer.control_names = state.control_names
        # print(self.current_buffer.control_names)

        if CLEAR_INPUTS:
            # Empty inputs file to not use previously found ones
            open(os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + INPUTS_NAME, "w").close()
            # print(os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + INPUTS_NAME)
            # sys.exit()

        self.load_inputs_from_file(INPUTS_NAME)
        iface.set_event_buffer(self.current_buffer)

        # self.records = self.extract_records(REPLAY_NAME)
        # print(self.records[0].position[0])
        
    def on_simulation_step(self, iface: TMInterface, _time: int):
        self.race_time = _time

        state = iface.get_simulation_state()
        if 0 <= self.race_time < MAX_TIME:
            # % 100 == 0 => is_equal
            # % 100 == 90 => start guess inputs (pos)
            # % 100 == 70 => stop guess inputs (pos)
            # % 100 == 90 => self.state_min_change
            if self.race_time == 0:
                self.state_min_change = state
                self.current_state = state
                self.event_min_change = self.deep_copy(self.current_buffer)
                self.ghost.update_next_inputs(index=1)
                
            if self.race_time % 100 == 90:
                if not self.current_state:
                    self.current_state = state

            if self.race_time % 100 == 0 and self.state_min_change.time - 2610 + 100 <= self.race_time:
                # print(self.state_min_change.time - 2510)
                index = int(self.race_time/100)
                equal = self.is_equal(state, self.ghost.records[index])
                # print(f"{equal} {_time} {state.position[0]} {self.ghost.records[index].position[0]}")
                # print(f"{equal} {_time} {state.position[1]} {self.ghost.records[index].position[1]}")
                # print(f"{equal} {_time} {state.position[2]} {self.ghost.records[index].position[2]}")

                # if self.race_time == 19700:
                #     print(f"{self.list_changes}")
                #     print(f"{equal} {_time} {state.position[0]} {self.ghost.records[index].position[0]}")
                #     print(f"{equal} {_time} {state.position[1]} {self.ghost.records[index].position[1]}")
                #     print(f"{equal} {_time} {state.position[2]} {self.ghost.records[index].position[2]}")

                if equal:
                    print(f"{_time=}, WheelDirectionRotation={self.ghost.records[index].WheelDirectionRotation}")
                    # print(f"steer={self.ghost.records[index].input_steer}, gas={self.ghost.records[index].input_gas}, brake={self.ghost.records[index].input_brake}, time={_time}")
                    # print(f"{self.ghost.records[index].input_steer}")
                    # print(f"{self.ghost.records[index].input_gas}")
                    # print(f"{self.ghost.records[index].input_brake}")
                    # print(f"{equal} {_time} {state.position[0]} {self.ghost.records[index].position[0]}")
                    # print(f"{equal} {_time} {state.position[1]} {self.ghost.records[index].position[1]}")
                    # print(f"{equal} {_time} {state.position[2]} {self.ghost.records[index].position[2]}")
                    # print(f"{equal} {_time} {state.velocity[0]} {self.ghost.records[index].speed}")
                    # print(f"{equal} {_time} {state.velocity[1]} {state.velocity[2]}")
                    # print(f"{equal} {_time} {state.position[1]} {self.ghost.records[index].position[1]}")
                    # print(f"{equal} {_time} {state.position[2]} {self.ghost.records[index].position[2]}")
                    # self.state_min_change = self.deep_copy(self.current_buffer)
                    # self.last_ok_state.state = state
                    # self.last_ok_state.direction = state.input_left
                    # self.last_ok_state.up = state.input_accelerate
                    # self.last_ok_state.down = state.input_brake

                    self.state_min_change = self.current_state

                    # maybe don't copy 11th tick though
                    # or changed the pressed keys for the next iteration?
                    self.event_min_change = self.deep_copy(self.current_buffer)

                    # print(self.current_buffer.to_commands_str())
                    self.save_result(self.race_time)

                    # print(self.list_changes)
                    self.list_changes = []
                    # self.nb_inputs_change = 0

                    self.ghost.update_next_inputs(index+1)
                    self.change_inputs(False) # change with ghost next inputs
                    iface.set_event_buffer(self.current_buffer)

                else:
                    # print(f"{equal} {_time} {state.position[0]} {self.ghost.records[index].position[0]}")
                    
                    # Change inputs
                    self.change_inputs(True)
                    iface.set_event_buffer(self.current_buffer)
                    # print(self.list_changes)
                    # if self.list_changes == [9, 29, 39]:
                    #     print(self.current_buffer.to_commands_str())
                    #     sys.exit()
                    # print(self.current_buffer.to_commands_str())
                    # return
                    iface.rewind_to_state(self.state_min_change)
                
                self.current_state = None

    def is_equal(self, state, record):
        # speed       = record.display_speed / 3.6
        # vel_heading = record.vel_heading / 128 * (math.pi)
        # vel_pitch   = record.vel_pitch   / 128 * (math.pi / 2)
        
        # print(f"{state.velocity[0]} {speed*math.cos(vel_pitch)*math.cos(vel_heading)}")
        # print(f"{state.velocity[1]} {speed*math.cos(vel_pitch)*math.sin(vel_heading)}")
        # print(f"{state.velocity[2]} {speed*math.sin(vel_pitch)}")
        
        # print(f"{state.display_speed} {record.speed}")

        if state.position != record.position:
            return False

        # int16		Velocity								(-> exp(Velocity/1000); 0x8000 means 0)
        # int8		VelocityHeading							(-0x80..0x7F -> -pi..pi)
        # int8		VelocityPitch							(-0x80..0x7F -> -pi/2..pi/2)
        
        # The rotation of the car is calculated as a quaternion.

        # The real part of the quaternion is calculated as cos(angle) which corresponds to a rotation of 2*angle around the rotation axis.
        # The imaginary part of the quaternion (the rotation axis) is calculated as the vector 
        # (sin(angle)*cos(axisPitch)*cos(axisHeading), 
        # sin(angle)*cos(axisPitch)*sin(axisHeading), 
        # sin(angle)*sin(axisPitch)).
        # You can convert this quaternion to a transform matrix.

        # The velocity vector (direction and Velocity of movement) is calculated in a similar way: 
        # (Velocity*cos(VelocityPitch)*cos(VelocityHeading), 
        # Velocity*cos(VelocityPitch)*sin(VelocityHeading), 
        # Velocity*sin(VelocityPitch)).
        
        return True

    def add_input(self, pressed, time, state, input):
        pressed.cmd(state, input)
        # print("add")
        self.current_buffer.add(time, input, state)
    
    def change_inputs(self, find_input):
        """
        Stategy to change 1 input:
        Direction first (10 + 10 iterations):
            - if going straight, try going left, then try going right
            - if going left, try going straight, then try going right
            - if going right, try going straight, then try going left
        Then try down (toggle on/off, 10 iterations)
        Then try up   (toggle on/off, 10 iterations)

        self.list_changes are the changes tried.
        The unit is the tick number (0 to 9), the other is the nature of the change
        0-9 : direction change 1
        10-19 : direction change 2
        20-29 : down change
        30-39 : up change
        """
        pressed = Pressed(self.state_min_change)

        # Remove inputs in the last tenth
        # self.state_min_change.time
        # self.deep_copy()
        self.current_buffer = self.deep_copy(self.event_min_change)
        # for event in self.current_buffer.find(time=self.state_min_change.time):
        #     pass

        if find_input:
            new = self.find_input_change()

            new = sorted(new, key=lambda n: n % NB_TICKS)

            # Add new inputs
            for change in new:
                # event_time
                type_change = change // NB_TICKS
                tick        = change  % NB_TICKS

                event_time = self.state_min_change.time - 2610 + tick * 10
                
                # event_input and event_value
                if type_change == 0:
                    # direction 1
                    if pressed.left:
                        self.add_input(pressed, event_time, REL, LEFT)
                        if pressed.right:
                            self.add_input(pressed, event_time, REL, RIGHT)
                    elif pressed.right:
                        self.add_input(pressed, event_time, REL, RIGHT)
                    else:
                        self.add_input(pressed, event_time, PRESS, LEFT)

                if type_change == 1:
                    # direction 2
                    if pressed.left:
                        self.add_input(pressed, event_time, REL, LEFT)
                        if not pressed.right:
                            self.add_input(pressed, event_time, PRESS, RIGHT)
                    elif pressed.right:
                        self.add_input(pressed, event_time, REL, RIGHT)
                        self.add_input(pressed, event_time, PRESS, LEFT)
                    else:
                        self.add_input(pressed, event_time, PRESS, RIGHT)

                if type_change == 2:
                    # down
                    if pressed.down:
                        self.add_input(pressed, event_time, REL, DOWN)
                    else:
                        self.add_input(pressed, event_time, PRESS, DOWN)

                if type_change == 3:
                    # up
                    if pressed.up:
                        self.add_input(pressed, event_time, REL, UP)
                    else:
                        self.add_input(pressed, event_time, PRESS, UP)

                # add event
                # self.current_buffer.add(event_time, event_input, event_value)
            
    # def add_inputs_ghost_tick(self, buffer):
        # Add inputs from ghost tick
        event_time = self.state_min_change.time - 2610 + NB_TICKS * 10

        if self.ghost.next_steer == "left":
            if not pressed.left:
                
                # print(event_time, 1)
                self.add_input(pressed, event_time, PRESS, LEFT)
            if pressed.right:
                # print(event_time, 2)
                self.add_input(pressed, event_time, REL, RIGHT)
        elif self.ghost.next_steer == "right":
            if pressed.left:
                # print(event_time, 3)
                self.add_input(pressed, event_time, REL, LEFT)
            if not pressed.right:
                # print(event_time, 4)
                self.add_input(pressed, event_time, PRESS, RIGHT)
        else:
            if pressed.left:
                # print(event_time, 5)
                self.add_input(pressed, event_time, REL, LEFT)
            if pressed.right:
                # print(event_time, 6)
                self.add_input(pressed, event_time, REL, RIGHT)

        if self.ghost.next_up != pressed.up:
            # print(event_time, 7)
            self.add_input(pressed, event_time, self.ghost.next_up, UP)

        if self.ghost.next_down != pressed.down:
            # print(event_time, 8)
            self.add_input(pressed, event_time, self.ghost.next_down, DOWN)

    def find_input_change(self):
        """
        Strategy global:
        Try 0 input change (1 iteration)
        Try 1 input change (40 iterations)
        Try 2 inputs change...

        The idea is to get the next logical self.list_changes
        if [] (no changes), then next should be [0]
        Then [1]... [39] at which point we tried all 1 input change and nothing worked
        So try 2 inputs [0, 1], [0, 2]... [0, 39] then [1, 2]... [1, 39]... [38, 39]
        Then 3 inputs [0, 1, 2]...

        Extra stuff: 
        - avoid duplicates
        - avoid 0/10, 1/11...
        """
        # Deep copy self.list_changes
        last_list_changes = []
        for change in self.list_changes:
            last_list_changes.append(change)

        # self.nb_inputs_change
        # self.list_changes = [0, 23, 39]

        impossible_list = []
        for i in range(NB_TICKS):
            impossible_list.append((i, i+NB_TICKS))

        size = len(self.list_changes)
        # print(size)

        if size == 0:
            # Try the first change
            self.list_changes = [0]
        else:
            i = -1
            backtracking = True
            while backtracking:
                
                if self.list_changes[i] >= NB_TICKS*4 + i:
                    if -i < size:
                        backtracking = True
                        # self.list_changes[i-1] += 1
                        # self.list_changes[i] = self.list_changes[i-1] + 2
                        i -= 1
                    else:
                        backtracking = False
                        # Add an input
                        self.list_changes = [*range(size + 1)]
                else:
                    backtracking = False
                    self.list_changes[i] += 1
                    
                    while i < -1:
                        self.list_changes[i+1] = self.list_changes[i] + 1
                        i += 1

                    # Skip 0/10, 1/11...
                    for a, b in impossible_list:
                        if a in self.list_changes and b in self.list_changes:
                            backtracking = True
                            i = max(self.list_changes.index(a), self.list_changes.index(b)) - size
                            break
        
        # print(self.list_changes)
        # if size == 2 and self.list_changes[0] == 5:
        #     sys.exit()
        # elif size == 1:
        #     self.list_changes[-1] += 1
        #     if self.list_changes[-1] > 39:
        #         self.list_changes = [0, 1]
        #     # print (self.list_changes[0])
        # elif size == 2:
        #     self.list_changes[-1] += 1
        #     if self.list_changes[-1] == 40:
        #         self.list_changes[-2] += 1
        #         self.list_changes[-1] = self.list_changes[-2] + 1
        #     if self.list_changes[-2] == 40 - 1:
        #         self.list_changes = [0, 1, 2]
        
        # if self.list_changes[-1] == 39:
        #     # Everything has been tried with the fixed number of changes, try with 1 more change
        #     self.list_changes.append(0)
        #     self.list_changes = range(len(self.list_changes))
        # else:
        #     # Try a different last change
        #     self.list_changes[-1] += 1
        
        self.nb_iterations += 1

        return self.list_changes
    
    def deep_copy(self, buffer):
        new_buffer = EventBufferData(buffer.events_duration)
        new_buffer.control_names = buffer.control_names
        for event in buffer.events:
            event_time = event.time - 100010
            event_name = self.current_buffer.control_names[event.name_index]
            event_value = event.analog_value if "analog" in event_name else event.binary_value
            new_buffer.add(event_time, event_name, event_value)
        
        return new_buffer

    def load_inputs_from_file(self, filename):
        """Load a inputs to bruteforce from a file instead of a replay"""
        print(f"Loading inputs from {filename}")
        
        # Fill the buffer
        self.current_buffer.clear()

        inputs_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + filename
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

            self.current_buffer.add(command.timestamp, command.input, command.state)

    def save_result(self, time_found=""):
        # if time_found == "":
        #     time_found = self.time_with_speed_coeff

        # Write inputs in file
        res_file = os.path.expanduser('~/Documents') + "/TMInterface/Scripts/" + INPUTS_NAME
        with open(res_file, "w") as f:
            inputs_str = self.current_buffer.to_commands_str()            
            if FORMAT_DECIMAL:
                inputs_str = to_sec(inputs_str)

            f.write(f"# Found inputs until time={time_found}, iterations: {self.nb_iterations}\n")
            f.write(inputs_str)

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    # Change current directory from executing directory to script directory
    if os.path.dirname(__file__) != os.getcwd():
        print(f"Changing current directory from executing directory to script directory")
        print(f"{os.getcwd()} => {os.path.dirname(__file__)}")
        os.chdir(os.path.dirname(__file__))

    main()
