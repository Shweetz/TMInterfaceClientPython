
from copy import deepcopy
import os
import sys
from tminterface.eventbuffer import EventBufferData

from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_BRAKE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME, BINARY_RESPAWN_NAME, BINARY_RACE_FINISH_NAME
from tminterface.commandlist import CommandList, InputCommand, InputType

import pygbx

PRESS = True
REL = False
LEFT = BINARY_LEFT_NAME
RIGHT = BINARY_RIGHT_NAME
DOWN = BINARY_BRAKE_NAME
UP = BINARY_ACCELERATE_NAME

REPLAY_NAME = "2022-04-15-00-19-21_A01-Race_6.43.Replay.Gbx"
INPUTS_NAME = "guessed_inputs.txt"

# class State():
#     state = None
#     direction = "straight"
#     up = True
#     down = False

class Pressed():
    left: False
    right: False
    up: True
    down: False

    def cmd(self, state, input):        
        if input == LEFT:
            self.left = state
        elif input == RIGHT:
            self.right = state
        elif input == DOWN:
            self.down = state
        elif input == UP:
            self.up = state

class MainClient(Client):
    def __init__(self) -> None:
        # self.last_ok_state = State()
        self.state_min_change = None
        self.list_changes = []
        self.nb_inputs_change = 0
        self.nb_iterations = 0

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        self.ghost = self.extract_ghost(REPLAY_NAME)
        self.lowest_time = (len(self.ghost.records) - 1) * 100

        nb_records = len(self.ghost.records)
        print(f"{self.lowest_time=}")
        for i, rec in enumerate(self.ghost.records):
            rec.time = i * 10
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
        self.load_inputs_from_file(INPUTS_NAME)
        iface.set_event_buffer(self.current_buffer)

        # self.records = self.extract_records(REPLAY_NAME)
        # print(self.records[0].position[0])
        
    def on_simulation_step(self, iface: TMInterface, _time: int):
        self.race_time = _time

        state = iface.get_simulation_state()
        if 0 <= self.race_time < 2100:
            if self.race_time % 100 == 0:
                index = int(self.race_time/100)
                equal = self.is_equal(state, self.ghost.records[index])
                # print(f"{equal} {_time} {state.position[0]} {self.ghost.records[index].position[0]}")
                # print(f"{equal} {_time} {state.position[1]} {self.ghost.records[index].position[1]}")
                # print(f"{equal} {_time} {state.position[2]} {self.ghost.records[index].position[2]}")

                if equal:
                    print(f"{equal} {_time} {state.position[0]} {self.ghost.records[index].position[0]}")
                    print(f"{equal} {_time} {state.position[1]} {self.ghost.records[index].position[1]}")
                    print(f"{equal} {_time} {state.position[2]} {self.ghost.records[index].position[2]}")
                    print(f"{equal} {_time} {state.velocity[0]} {self.ghost.records[index].speed}")
                    print(f"{equal} {_time} {state.velocity[1]} {state.velocity[2]}")
                    # print(f"{equal} {_time} {state.position[1]} {self.ghost.records[index].position[1]}")
                    # print(f"{equal} {_time} {state.position[2]} {self.ghost.records[index].position[2]}")
                    # self.state_min_change = self.deep_copy(self.current_buffer)
                    # self.last_ok_state.state = state
                    # self.last_ok_state.direction = state.input_left
                    # self.last_ok_state.up = state.input_accelerate
                    # self.last_ok_state.down = state.input_brake

                    self.state_min_change = state
                    self.event_min_change = self.deep_copy(self.current_buffer)

                    print(self.list_changes)
                    self.list_changes = []
                    self.nb_inputs_change = 0

                    print(self.current_buffer.to_commands_str())
                    self.save_result(self.race_time)

                else:
                    # Change inputs
                    self.change_inputs(self.current_buffer)
                    iface.set_event_buffer(self.current_buffer)
                    # print(self.current_buffer.to_commands_str())
                    # return
                    iface.rewind_to_state(self.state_min_change)

    def is_equal(self, state, record):
        if state.position != record.position:
            return False
            
        # if state.angle != record.angle:
        #     return False
        
        return True

    def add_input(self, pressed, time, state, input):
        pressed.cmd(state, input)
        # print("add")
        self.current_buffer.add(time, input, state)
    
    def change_inputs(self, buffer):
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
        old, new = self.find_input_change()

        # Remove inputs in the last tenth
        # self.state_min_change.time
        # self.deep_copy()
        self.current_buffer = self.deep_copy(self.event_min_change)
        # for event in self.current_buffer.find(time=self.state_min_change.time):
        #     pass

        pressed = Pressed()
        pressed.left = self.state_min_change.input_left
        pressed.right = self.state_min_change.input_right
        pressed.down = self.state_min_change.input_brake
        pressed.up = self.state_min_change.input_accelerate

        new = sorted(new, key=lambda n: n%10)

        # Add new inputs
        for change in new:
            # event_time
            tick = change % 10
            event_time = self.state_min_change.time - 2610 + tick * 10

            
            # print(f"{event_time=}")
            # print(f"{change=}")
            # event_input and event_value
            if change // 10 == 0:
                # direction 1
                if pressed.left:
                    self.add_input(pressed, event_time, REL, LEFT)
                    if pressed.right:
                        self.add_input(pressed, event_time, REL, RIGHT)
                elif pressed.right:
                    self.add_input(pressed, event_time, REL, RIGHT)
                else:
                    self.add_input(pressed, event_time, PRESS, LEFT)

            if change // 10 == 1:
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

            if change // 10 == 2:
                # down
                if pressed.down:
                    self.add_input(pressed, event_time, REL, DOWN)
                else:
                    self.add_input(pressed, event_time, PRESS, DOWN)

            if change // 10 == 3:
                # up
                if pressed.up:
                    self.add_input(pressed, event_time, REL, UP)
                else:
                    self.add_input(pressed, event_time, PRESS, UP)

            # add event
            # self.current_buffer.add(event_time, event_input, event_value)

    def find_input_change(self):
        """
        Strategy global:
        Try 0 input change (1 iteration)
        Try 1 input change (40 iterations)
        Try 2 inputs change (? iterations)
        ...
        The idea is to get the next logical self.list_changes
        if [] (no changes), then next should be [0]
        Then [1]... [39] at which point we tried all 1 input change and nothing worked
        So try 2 inputs [0, 1], [0, 2]... [0, 39] then [1, 2]... [1, 39]... [38, 39]
        Then 3 inputs [0, 1, 2]...

        TODO: avoid duplicates
        TODO: avoid 0/10, 1/11...
        """
        # Deep copy self.list_changes
        last_list_changes = []
        for change in self.list_changes:
            last_list_changes.append(change)

        # self.nb_inputs_change
        # self.list_changes = [0, 23, 39]

        impossible_list = []
        for i in range(10):
            impossible_list.append((i, i+10))

        size = len(self.list_changes)
        # print(size)

        if size == 0:
            # Try the first change
            self.list_changes = [0]
        else:
            i = -1
            backtracking = True
            while backtracking:
                self.list_changes[i] += 1
                if self.list_changes[i] > 39 + i + 1:
                    if -i < size:
                        backtracking = True
                        # self.list_changes[i-1] += 1
                        self.list_changes[i] = self.list_changes[i-1] + 1
                        i -= 1
                    else:
                        backtracking = False
                        # Add an input
                        self.list_changes = [*range(size + 1)]
                else:
                    backtracking = False
                    
                    # Skip 0/10, 1/11...
                    for a, b in impossible_list:
                        if a in self.list_changes and b in self.list_changes:
                            backtracking = True
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

        return last_list_changes, self.list_changes
    
    def deep_copy(self, buffer):
        new_buffer = EventBufferData(buffer.events_duration)
        new_buffer.control_names = buffer.control_names
        for event in buffer.events:
            event_time = event.time - 100010
            event_name = self.current_buffer.control_names[event.name_index]
            event_value = event.analog_value if "analog" in event_name else event.binary_value
            new_buffer.add(event_time, event_name, event_value)
        
        return new_buffer

    def extract_ghost(self, filename: str) -> list[int]:
        """Extract ghost from a replay with pygbx"""
        g = pygbx.Gbx(filename)
        ghost = g.get_class_by_id(pygbx.GbxType.CTN_GHOST)
        if not ghost:
            print(f"ERROR: no ghost in {filename=}")
            quit()

        return ghost

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
            f.write(f"# Found inputs until time={time_found}, iterations: {self.nb_iterations}\n")
            f.write(self.current_buffer.to_commands_str())

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
