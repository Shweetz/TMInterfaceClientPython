import sys
import time
from sys import stdout

from tminterface.client import Client, run_client
from tminterface.interface import TMInterface
from tminterface.structs import EventBufferData, Event
import numpy as np


class BruteforceType:
    NORMAL = 0
    TURN_L = 1
    TURN_R = 2


class MainClient(Client):
    def __init__(self) -> None:

        # Settings

        self.enabled = True

        self.turn_s = 4170  # turn start time
        self.turn_e = 7200  # turn end time

        # Temp data

        self.state = None
        self.firstState = None
        self.simtime = 0
        self.inputs = []
        self.bf_type = BruteforceType.TURN_R
        self.curr_t = self.turn_s

        self.worked = False
        self.inputs_buffer = EventBufferData(-1)
        self.og_in_buf = None
        self.og_speed = {}
        self.first_run = True
        self.evaluating = False
        self.first_time_at_this_time = True

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.register_custom_command('bf')

    def on_custom_command(self, iface, time_from: int, time_to: int, command: str, args: list):
        if command == 'bf':
            if len(args) > 0:
                if args[0].lower() == "on":
                    iface.log('Bruteforce enabled', 'success')
                    self.enabled = True
                elif args[0].lower() == "off":
                    iface.log('Bruteforce disabled', 'success')
                    self.enabled = False
                else:
                    iface.log('Syntax: bf <on/off>', 'error')

            else:
                iface.log('Syntax: bf <on/off>', 'error')

    def on_simulation_begin(self, iface):
        if not self.enabled:
            return

        iface.remove_state_validation()
        iface.set_speed(100)

    def on_simulation_step(self, iface, _time: int):

        if not self.enabled:  #
            return

        self.simtime = _time - 2610
        ctrl_names = iface.get_event_buffer().control_names
        steer_index = ctrl_names.index("Steer (analog)")
        gas_index = ctrl_names.index("Accelerate")

        if self.simtime >= 10:

            if self.og_in_buf is None:
                self.og_in_buf = iface.get_event_buffer().copy()

            self.state = iface.get_simulation_state()

            if self.bf_type != BruteforceType.NORMAL:

                c = 1 if self.bf_type == BruteforceType.TURN_R else -1

                # Adding acceleration event at the start of the race

                if self.simtime == 10:
                    e = Event(100010, 0)
                    e.name_index = gas_index
                    e.binary_value = 1
                    self.inputs_buffer.events.append(e)

                #                                                                       |
                # Registering the original speed for later evaluation of the efficiency v

                if self.og_speed.get(self.simtime) is None and self.turn_s <= self.simtime and self.first_run:
                    sys.stdout.write(f"Set original speed for time {self.simtime}")
                    sys.stdout.write("\n")
                    self.og_speed[self.simtime] = np.linalg.norm(self.state.get_velocity())

                if self.simtime == self.curr_t - 10 and self.curr_t - 10 > 10:
                    self.firstState = iface.get_simulation_state()

                if self.simtime == self.turn_e + 110:
                    iface.rewind_to_state(self.firstState)
                    self.first_run = False

                # if self.simtime == 10 and self.firstState is None:
                #     self.firstState = iface.get_simulation_state()

                #                      |
                # Main bruteforce code v

                if not self.first_run:
                    if self.simtime == self.curr_t:
                        if self.first_time_at_this_time:
                            self.state.input_steer_state.analog_value = c * 65536
                            self.first_time_at_this_time = False
                        else:
                            if self.worked:
                                self.save_inputs(False, iface)
                                self.curr_t += 10
                                stdout.write(f"Changing times because it worked: {self.curr_t}")
                                stdout.write("\n")
                                self.first_time_at_this_time = True
                            else:
                                new = self.state.input_steer_state.analog_value - c * 1000
                                print(f"{new=}")
                                if self.bf_type == BruteforceType.TURN_R:
                                    if new < 0:
                                        new = 0
                                        self.curr_t += 10
                                        stdout.write(
                                            f"Changing times because it reached 0 (not supposed to happen): {self.curr_t}")
                                        stdout.write("\n")
                                        self.first_time_at_this_time = True
                                elif new > 0:
                                    new = 0
                                    self.curr_t += 10
                                    stdout.write(
                                        f"Changing times because it reached 0 (not supposed to happen): {self.curr_t}")
                                    stdout.write("\n")
                                    self.first_time_at_this_time = True

                                self.state.input_steer_state.analog_value = new
                        print(f"{self.state.input_steer_state.analog_value=}")
                        print("1")
                        self.last_vel = np.linalg.norm(self.state.get_velocity())
                        self.worked = True

                    elif self.simtime > self.curr_t + 490:
                        print("3")
                        self.evaluating = True
                        iface.set_event_buffer(self.inputs_buffer.copy())
                        self.clear_buffer()
                        iface.rewind_to_state(self.firstState)

                    elif self.simtime > self.curr_t:
                        self.state.input_steer_state.analog_value = 0

                        vel = np.linalg.norm(self.state.get_velocity())
                        if vel > self.last_vel:
                            self.last_vel = vel
                        else:
                            print("2")
                            self.worked = False
                            self.evaluating = False
                            iface.rewind_to_state(self.firstState)

                    elif self.simtime > self.turn_e + 510:
                        self.save_inputs(False, iface)

                #elif not self.first_run:
                    #if self.simtime >= self.turn_s:
                    #    stdout.write(
                    #        f"current speed: {np.linalg.norm(self.state.get_velocity())}, expected speed: {self.og_speed[self.simtime] * 0.99}")
                    #    stdout.write("\n")

                    #if self.simtime == self.curr_t:

                    #if self.curr_t < self.simtime < self.curr_t + 500:
                    #    vel = np.linalg.norm(self.state.get_velocity())
                    #    if vel > self.last_vel:
                    #        self.last_vel = vel
                    #    else:
                    #        print("2")
                    #        self.worked = False
                    #        self.evaluating = False
                    #        iface.rewind_to_state(self.firstState)

                    #if self.curr_t + 500 <= self.simtime :
                    #    print("3")
                    #    if np.linalg.norm(self.state.get_velocity()) > self.last_vel:
                    #        self.worked = True

                    #        #print(f"{self.worked=}")
                    #    self.evaluating = False
                    #    iface.rewind_to_state(self.firstState)

            event = Event(100000 + self.simtime, 0)
            event.name_index = steer_index
            event.analog_value = self.state.input_steer_state.analog_value
            self.inputs_buffer.events.append(event)

    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        # print(f'Reached checkpoint {current}/{target}')

        if not self.enabled:
            return
        self.save_inputs(False, iface)

    def on_simulation_end(self, iface, result: int):
        print('Simulation finished')
        iface.set_speed(1)

    def clear_buffer(self):

        to_remove = []

        for a in self.inputs_buffer.events:
            if a.time >= 100000 + self.curr_t:
                to_remove.append(a)

        for a in to_remove:
            self.inputs_buffer.events.remove(a)

    def save_inputs(self, wait: bool, iface: TMInterface):
        ctrl_names = iface.get_event_buffer().control_names
        steer_index = ctrl_names.index("Steer (analog)")
        gas_index = ctrl_names.index("Accelerate")
        iface.get_event_buffer().sort()
        inputs = []
        for a in iface.get_event_buffer().events:
            if a.name_index == steer_index:
                inputs.append(f"{a.time - 100000} steer {a.analog_value}")
            elif a.name_index == gas_index:
                inputs.append(f"{a.time - 100000} press up")
        with open(r"C:\Users\rmnlm\Documents\TMInterface\Scripts\result.txt", "w") as f:
            f.write("\n".join(inputs))
            
        #print(inputs)
        if wait:
            time.sleep(1)


def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    server_name = 'TMInterface1'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)


if __name__ == '__main__':
    main()
