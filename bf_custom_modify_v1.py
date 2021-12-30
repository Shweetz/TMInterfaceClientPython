
from dataclasses import dataclass
from enum import IntEnum
import random
import sys
import time

from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client
from tminterface.constants import ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME

LOCK_BASE_RUN = True
steer_cap_accept = True
steer_equal_last_input_proba = 0.5

# class Input(IntEnum):
#     UP = 0
#     DOWN = 1
#     STEER = 2

class ChangeType(IntEnum):
    TIMING = 0
    STEER_DIFF = 1
    CREATE_REMOVE = 2

@dataclass
class Change:
    proba : float
    start_time : int
    end_time : int
    input : str
    change_type : ChangeType
    value : int

rules = []
# rules.append(Change(0.02, 10000, 12000, Input.UP, ChangeType.TIMING, 50))
# rules.append(Change(0.1, 0, 100, Input.DOWN, ChangeType.CREATE_REMOVE, 0))
rules.append(Change(0.1, 0, 10000, ANALOG_STEER_NAME, ChangeType.STEER_DIFF, 65536))

for rule in rules:
    lowest_poss_change = min([c.start_time for c in rules])
    highest_poss_change = max([c.end_time for c in rules])


class MainClient(Client):
    def __init__(self) -> None:
        self.best = -1
        self.time = -1
        self.cp_count = 0
        self.force_accept = False
        self.phase = BFPhase.INITIAL
        self.finished = False
        self.begin_buffer = None
        self.current_buffer = None
        self.best_buffer = None
        self.best_inputs = None

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_simulation_begin(self, iface):
        iface.remove_state_validation()

        self.begin_buffer = iface.get_event_buffer() # fill_inputs happens before on_simulaton_begin
        self.lowest_time = self.begin_buffer.events_duration
        self.current_buffer = self.begin_buffer.copy()
        print(self.current_buffer.to_commands_str())
        
    def on_simulation_step(self, iface: TMInterface, _time: int):
        self.race_time = _time
        if self.race_time == 0:
            self.state = iface.get_simulation_state()

        # print(buffer.to_commands_str())

        if self.finished or self.race_time > self.lowest_time:
            if self.race_time < self.lowest_time:
                self.lowest_time = self.race_time
                self.best_inputs = self.current_buffer.to_commands_str()
                self.save_result("", iface)

            iface.rewind_to_state(self.state)
            self.randomize_inputs()
            iface.set_event_buffer(self.current_buffer)
            # print()
            # time.sleep(1)
            self.finished = False
        

    def on_checkpoint_count_changed(self, iface: TMInterface, current: int, target: int):
        print(f'Reached checkpoint {current}/{target}')
        if current == target:
            print(f'Finished the race at {self.race_time}')
            self.finished = True
            iface.prevent_simulation_finish()

    def randomize_inputs(self):
        # can't copy because events is deepcopied but not the individual events
        # self.current_buffer = self.begin_buffer.copy()
        
        self.current_buffer.clear()
        for event in self.begin_buffer.events:
            event_time = event.time - 100010
            event_name = self.begin_buffer.control_names[event.name_index]
            event_value = event.analog_value if "analog" in event_name else event.binary_value
            self.current_buffer.add(event_time, event_name, event_value)

        # print(self.begin_buffer.to_commands_str())
        # print(self.current_buffer.to_commands_str())
        
        for rule in rules:
            # only inputs that match the rule (ex: steer)
            events = self.current_buffer.find(event_name=rule.input)
            for event in events:
                event_realtime = event.time - 100010
                # print("1")
                # print(event_realtime)
                # event in rule time
                if rule.start_time <= event_realtime <= rule.end_time:
                    # event proba
                    if random.random() < rule.proba:
                        # event type
                        if rule.change_type == ChangeType.STEER_DIFF:
                            diff = random.randint(-rule.value, rule.value)
                            event.analog_value += diff
                            event.analog_value = min(event.analog_value, 65536)
                            event.analog_value = max(event.analog_value, -65536)

                # print(event)
        # print(self.current_buffer.to_commands_str())
        
    def save_result(self, result_name, iface):
        res_file = "C:/Users/rmnlm/Documents/TMInterface/Scripts/result.txt"
        # Write in result.txt if base run is locked, else ACCEPT takes care of it
        if LOCK_BASE_RUN:
            with open(res_file, "w") as f:
                f.write(iface.get_event_buffer().to_commands_str())

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()

"""Ideas:
- not rewind to time 0 => rewind to lowest_poss => rewind to 1st change
"""
