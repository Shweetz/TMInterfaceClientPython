import math
import operator
import os
import time

from tminterface.commandlist import CommandList, InputCommand, InputType, BOT_INPUT_TYPES

from SUtil import sec_to_ms

"""
HOW TO USE
- Place the inputs as txt files in the same directory as this script
- Fill "inputs_assemble_info.txt" which is also in this directory. 1 line per respawn 
    Line formatting possibilities:
    * filename.txt start_time end_time
    * filename.txt end_time
    * filename.txt
    If only end_time is defined, start_time will be the previous "press enter"
    If no time is defined, the txt file must contain 2 "press enter", those will be start_time and end_time
"""
class RespawnState:
    """Stores the time and inputs pressed during a respawn"""
    # filename = ""
    # input_accelerate = 0
    # input_brake = 0
    # input_left = 0
    # input_right = 0
    # input_steer = 0
    # input_gas_event = 0

    def __init__(self):
        self.timestamp = 0
        self.inputs = {}
        # self.filename = filename
        for i in range(InputType.UNKNOWN):
            self.inputs[i] = 0

    def copy(self):
        respawn_state = RespawnState()
        respawn_state.timestamp = self.timestamp
        for i in range(InputType.UNKNOWN):
            respawn_state.inputs[i] = self.inputs[i]
        return respawn_state

    def update(self, input_type: InputType, state: int) -> None:
        # print(input_type.value)
        # print(state)
        # time.sleep(1)
        self.inputs[input_type.value] = state


def extract_sorted_timed_commands(filename: str) -> CommandList:
    with open(filename, "r") as f:
        inputs_str = f.read()

    # print(inputs_str)

    # Transform inputs in sorted commands (free inputs clean up)
    cmdlist = CommandList(inputs_str)
    commands = [cmd for cmd in cmdlist.timed_commands if isinstance(cmd, InputCommand)]
    commands.sort(key=operator.attrgetter("timestamp"))

    return commands

def get_respawn_state(commands: list[InputCommand], timestamp: int, respawn_state) -> RespawnState:
    # respawn_state = RespawnState()

    for command in commands:
        # For every command in the file, update the inputs pressed at the moment
        if (command.timestamp < timestamp):
            respawn_state.update(command.input_type, command.state)
        else:
            # Save the state inputs when a respawn is performed
            print(f"Adding respawn_state at {command.timestamp}, press up = {respawn_state.inputs[0]}")
            break
    
    return respawn_state

# def get_respawn_states(commands: CommandList) -> int:
#     respawn_states = []
#     # Add a RespawnState at time 0 with no inputs
#     respawn_states.append(RespawnState())

#     respawn_states.append(RespawnState())
#     for command in commands:
#         # For every command in the file, update the inputs pressed at the moment
#         respawn_states[-1].update(command.input_type, command.state)
#         # if (command.input_type == InputType.RESPAWN and command.state == 1):
#             # Save the state inputs when a respawn is performed
#         respawn_states[-1].timestamp = command.timestamp
#         print(f"Adding respawn_state at {respawn_states[-1].timestamp}, press up = {respawn_states[-1].inputs[0]}")
#         respawn_states.append(RespawnState())
#             # print(f"Adding respawn_state at {respawn_state.timestamp}, press up = {respawn_state.inputs[0]}")
#             # respawn_state = RespawnState()
#             # print(f"Adding respawn_state at {command.timestamp}")
            
#         # elif True:
#         #     # Save the state inputs when a CP is crossed
#             # respawn_states.append(respawn_state)
#             # respawn_states[-1].update(command.input_type, command.state)
#             # respawn_state = RespawnState()
#             # print(f"Adding respawn_state at {command.timestamp}")

#     return respawn_states

def find_command_index(commands: CommandList, end_time: int, input_type: InputType, state: int) -> int:
    """
    In a CommandList, find the index of the command at end_time with the specified InputType.
    Example: find_command_index(commands, 1000, InputType.RESPAWN) -> 45
    """
    # Use dichotomy to find the command
    index_min = 0
    index_max = len(commands) - 1

    command = commands[0]
    
    # Find a command with the same time (can be another command)
    while command.timestamp != end_time:
        index = math.floor((index_min+index_max) / 2)
        command = commands[index]

        if command.timestamp < end_time:
            index_min = index + 1
        elif command.timestamp > end_time:
            index_max = index - 1

        if index_min > index_max:
            print(f"find_command_index: WARNING No command found at {end_time=} (can be because non-instant respawn)")
            return index_min
    
    # Find the enter/respawn command at this time
    if command.input_type != input_type or command.state != state:
        # Find the first command with end_time
        while commands[index-1].timestamp == end_time:
            index -= 1
        command = commands[index]

        # Go through commands until finding it or higher end_time
        while command.timestamp == end_time and command.input_type != input_type and index < len(commands) - 1:
            index += 1
            command = commands[index]
    
    # print(f"find_command_index: {index=}, {command.timestamp=}")
    # Index max means grab inputs until the start
    if index == len(commands) - 1:
        return index

    # Final check
    if command.timestamp != end_time or command.input_type != input_type:
        # print(index)
        # print(len(commands))
        print(f"find_command_index: ERROR {command.timestamp=} != {end_time=} or {command.input_type=} != {input_type=}")
        raise
    
    # print(f"find_command_index: {index=}, {command.timestamp=}")
    return index

def find_previous_index(commands: CommandList, end_index: int, input_type: InputType, state: int) -> int:
    """
    In a CommandList, find the index of the previous command with the specified InputType.
    Example: find_command_index(commands, 1000, InputType.RESPAWN) -> 45
    """
    index = end_index - 1
    command = commands[index]
    
    # Go back one command at a time until finding the previous
    while (command.input_type != input_type or command.state != state) and index > 0:
        index -= 1
        command = commands[index]

    # print(f"find_previous_index: {index=}, {command.timestamp=}")
    # Index 0 means grab inputs from the start
    if index == 0:
        return index

    # Final check (index != 0)
    if command.input_type != input_type:
        print(f"find_previous_index ERROR: {command.input_type=} != {input_type=}")
        raise
    
    return index

def to_script(commands: list) -> str:
    """Transform a list of commands to a string"""
    result_string = ""
    for command in commands:
        result_string += command.to_script() + "\n"
    return result_string

def main():
    with open("inputs_assemble_info.txt", "r") as f:
        lines_info = f.readlines()

    assembled_file = "inputs_assemble.txt"
    # assembled_file = os.path.expanduser('~/Documents') + "/TMInterface/States/" + "work2.txt"
    assembled_inputs = ""
    # inputs_files_read = []
    last_end_time = 0
    last_respawn_state = RespawnState()
    # last_respawn_state.timestamp = 5
    # print(new_respawn_state.timestamp)

    # get_cp_states()

    # Every line in lines_info shall be formatted like this:
    # filename.txt [start_time] end_time
    # Note: start_time is optional, if undefined it will be the previous press enter
    for line in lines_info:
        # print("")
        line = line.replace("\n", "")
        if not line or line.startswith("#"):
            continue
        
        splits = line.split(" ")
        filename = splits[0]
        start_time = None
        end_time = None

        if len(splits) == 2:
            end_time = int(sec_to_ms(splits[1]))

        elif len(splits) == 3:
            start_time = int(sec_to_ms(splits[1]))
            end_time = int(sec_to_ms(splits[2]))
            # print(f"{start_time=} {end_time=}")
        elif len(splits) > 3:
            print(f"{len(splits)=}: {line}")
            continue

        # if filename not in inputs_files_read:
        if not os.path.isfile(filename):
            print(f"{filename} does not exist")
            continue

            # read and store pressed buttons + time every respawn
            # respawn_states = get_respawn_states(commands)

            # inputs_files_read.append(filename)
        
        commands = extract_sorted_timed_commands(filename)

        # Find end_time
        if not end_time:
            # count nb press enter
            nb_press_enter = 0
            for command in commands:
                if command.input_type == InputType.RESPAWN and command.state == 1:
                    nb_press_enter += 1
                    # print(f"press enter found at {command.timestamp}")
            
            if nb_press_enter == 1:
                # last command
                end_time = commands[-1].timestamp
                print(f"WARNING only 1 press enter found, cutting on last InputCommand")

            elif nb_press_enter == 2:
                # last press enter
                end_index = find_previous_index(commands, len(commands), InputType.RESPAWN, 1)
                end_time = commands[end_index].timestamp

            else:
                print(f"ERROR {nb_press_enter=}")
                continue

        # Find start_time
        if start_time is None:
            #find previous press enter before end_time
            end_index = find_command_index(commands, end_time, InputType.RESPAWN, 1)
            start_index = find_previous_index(commands, end_index, InputType.RESPAWN, 1)
            start_time = commands[start_index].timestamp
        
        print(f"{filename} between {start_time} and {end_time}")

        # Transition state: replace inputs during last respawn with inputs new respawn
        commands_inputs_difference = []
        # for i, respawn_state in enumerate(respawn_states):
        #     # Exact time
        #     if respawn_state.timestamp == start_time:
        #         new_respawn_state = respawn_state
        #         break
        #     # Too far because no respawn state on the tick CP was crossed
        #     if respawn_state.timestamp > start_time:
        #         new_respawn_state = respawn_states[i-1]
        #         break
        
        # print(f"{last_respawn_state.inputs[0]=}")
        # new_respawn_state = get_respawn_state(commands, start_time, new_respawn_state)
        
        new_respawn_state = RespawnState()
        
        for command in commands:
            # For every command in the file, update the inputs pressed at the moment
            if (command.timestamp < start_time):
                new_respawn_state.update(command.input_type, command.state)
                # print(f"{command.input_type=}, {command.state=}")
            else:
                # Save the state inputs when a respawn is performed
                # print(f"Adding new_respawn_state at {command.timestamp}, steer = {new_respawn_state.inputs[6]}")
                break
        # print(f"{last_respawn_state.inputs[0]=}")
        # print(f"{start_time} {last_respawn_state.inputs[0]} {new_respawn_state.inputs[0]}")
        for i in range(InputType.UNKNOWN):
            # print("")
            # print(f"{start_time} {i} {last_respawn_state.inputs[i]} {new_respawn_state.inputs[i]}")
            # print("")
            if new_respawn_state.inputs[i] != last_respawn_state.inputs[i]:
                timestamp = start_time
                inputs_type = InputType(i)
                state = new_respawn_state.inputs[i]
                # command = 
                commands_inputs_difference.append(InputCommand(timestamp, inputs_type, state))
                # print("")
                # print(f"{start_time} {i} {last_respawn_state.inputs[i]} {new_respawn_state.inputs[i]}")
                # print("")
        
        # last_respawn_state = get_respawn_state(commands, end_time, last_respawn_state)
        for command in commands:
            # For every command in the file, update the inputs pressed at the moment
            if (command.timestamp < end_time):
                last_respawn_state.update(command.input_type, command.state)
            else:
                # Save the state inputs when a respawn is performed
                # print(f"Adding last_respawn_state at {command.timestamp}, steer = {last_respawn_state.inputs[6]}")
                break

        # print(f"Making commands")
        
        # Get commands between start_time and end_time
        commands_between_start_and_end = [command for command in commands if start_time <= command.timestamp < end_time]

        # Combine transition state + new commands
        new_commands = commands_inputs_difference
        new_commands.extend(commands_between_start_and_end)

        # Delay commands
        delay = last_end_time - new_commands[0].timestamp
        # print(delay)
        # print(len(new_commands))
        # print(new_commands[0].timestamp)
        for i in range(len(new_commands)):
            new_commands[i].timestamp += delay

        # print(new_commands[0].timestamp)
        last_end_time = end_time + delay

        # print inputs
        assembled_inputs += to_script(new_commands)


    with open(assembled_file, "w") as f:
        f.write(assembled_inputs)


if __name__ == "__main__":
    main()
