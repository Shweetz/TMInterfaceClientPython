
import datetime
import math
import numpy
import signal
import sys
import time

from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase, BFTarget, Event
from tminterface.interface import TMInterface
from tminterface.client import Client
from tminterface.constants import ANALOG_ACCELERATE_NAME, ANALOG_STEER_NAME, BINARY_ACCELERATE_NAME, BINARY_RACE_START_NAME, BINARY_RACE_FINISH_NAME, BINARY_LEFT_NAME, BINARY_RIGHT_NAME

class Working():
    _time = 0
    min_steer = 0 # ne doit pas etre reset a chaque tick car on tourne de + en +
    max_steer = 65536
    cur_steer = 0
    min_crash = -1
    max_crash = -1

class MainClient(Client):
    def __init__(self) -> None:
        self.current_time = 0
        self.do_accept = False
        self.force_accept = False
        self.lowest_time = 0
        self.phase = BFPhase.INITIAL
        self.target_ending_pos = 0
        self.rewinded = True
        self.last_vel = 0
        self.working = Working()

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller bruteforce')
        iface.execute_command('set bf_search_forever true')
    
    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration
        self.save_base_run(iface)
        # self.base_run.clear()
        # self.base_run.add(time=0, event_name=BINARY_ACCELERATE_NAME, value=1)
        events = self.base_run.find(event_name=BINARY_LEFT_NAME)
        for event in events:
            print(f"{event.time=}")
            self.base_run.events.remove(event)
        events = self.base_run.find(event_name=BINARY_RIGHT_NAME)
        for event in events:
            print(f"{event.time=}")
            self.base_run.events.remove(event)
        #self.load_base_run(iface)
        #self.load_base_run(iface)
        #self.inputs_buffer = self.base_run
    
    def on_simulation_step(self, iface, _time: int):
        self.simtime = _time
        #print(f"{self.simtime=}")
        #working_time = 0

        state = iface.get_simulation_state()

        #if self.rewinded:
        #    self.rewinded = false
        #    self.last_vel = 0
        #else:
        #    self.working.cur_steer = 0

        if self.simtime == -10:
            self.firstState = state

        elif self.simtime == self.working._time:
            events = self.base_run.find(time=self.working._time, event_name=ANALOG_STEER_NAME)

            if events:
                self.base_run.events.remove(events[0])
        
            self.base_run.add(self.working._time, ANALOG_STEER_NAME, self.working.cur_steer)
            self.load_base_run(iface)
            #event = Event(100010 + self.working._time, 0)
            #event.name_index = iface.get_event_buffer().control_names.index(ANALOG_STEER_NAME)
            #event.name_index = self.base_run.control_names.index("Steer (analog)")
            #event.analog_value = 65536
            #self.base_run.events.append(event)
        
            #event = self.base_run.find(event_name=ANALOG_STEER_NAME)
            #if event:
            #    print("event")

            #self.save_base_run(iface)
            self.last_vel = self.get_velocity(state)

        elif self.simtime > self.working._time:
            curr_vel = self.get_velocity(state)
            #print(f"{self.simtime=}, {curr_vel=}, {self.last_vel=}")
            if curr_vel < self.last_vel - 0.1 and self.simtime > 1000:
                #print(f"for {self.working._time=} steer {self.working.cur_steer}, slower at {self.simtime=}")
                #print(f"{curr_vel=}, {self.last_vel=}")
                if self.working.cur_steer == self.working.min_steer:
                    self.working.min_crash = self.simtime
                elif self.working.cur_steer == self.working.max_steer:
                    self.working.max_crash = self.simtime
                else:
                    if self.simtime >= self.working.min_crash:
                        self.working.min_steer = self.working.cur_steer
                        self.working.min_crash = self.simtime
                    #elif self.simtime >= self.working.max_crash:
                    #    self.working.max_steer = self.working.cur_steer
                    #    self.working.max_crash = self.simtime
                    #else:
                    #    print("Probleme")
                    else:
                        self.working.max_steer = self.working.cur_steer
                        self.working.max_crash = self.simtime
                        
                if self.working.max_steer - self.working.min_steer == 1 or self.working.min_steer == 65536:
                    print(f"Perfect: {self.working._time} steer {self.working.min_steer}")
                    self.save_inputs(iface)
                    self.working._time += 10
                    self.working.max_steer = 65536
                    self.working.max_crash = -1
                    self.working.min_steer = 0 # eh
                    self.working.min_crash = -1 # eh
                if self.working.min_crash == -1:
                    self.working.cur_steer = self.working.min_steer
                    self.working.cur_steer = 0 # eh
                elif self.working.max_crash == -1:
                    self.working.cur_steer = 65536
                else:
                    self.working.cur_steer = math.floor((self.working.min_steer + self.working.max_steer) / 2)

                #print(f"{self.working._time=}, {self.working.cur_steer=}, {self.working.min_steer=}, {self.working.max_steer=}")

                if self.phase == BFPhase.SEARCH:
                    iface.rewind_to_state(self.firstState)
                #self.rewinded = True
                #return

            self.last_vel = curr_vel


    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        self.current_time = info.time
        self.phase = info.phase

        response = BFEvaluationResponse()

        if self.phase == BFPhase.INITIAL:
            response.decision = BFEvaluationDecision.CONTINUE
        else:
            response.decision = BFEvaluationDecision.DO_NOTHING

        # if self.current_time >= 0:
        #     pass
            #print(f"{self.current_time=}, {self.get_velocity(iface.get_simulation_state())=}")
            #response.decision = BFEvaluationDecision.ACCEPT

        return response

    def get_velocity(self, state):
        return numpy.linalg.norm(state.velocity)
    
    def save_base_run(self, iface):
        self.base_run = iface.get_event_buffer()
    
    def load_base_run(self, iface):
        iface.set_event_buffer(self.base_run)

    def save_inputs(self, iface):
        #save_base_run
        #print(self.base_run.events_duration)
        print(self.base_run.to_commands_str())
        with open(r"C:\Users\rmnlm\Documents\TMInterface\Scripts\result.txt", "w") as f:
            #f.write("\n".join(inputs))
            f.write(self.base_run.to_commands_str())
        #time.sleep(10)            

def main():
    server_name = 'TMInterface0'
    if len(sys.argv) > 1:
        server_name = 'TMInterface' + str(sys.argv[1])

    print(f'Connecting to {server_name}...')

    iface = TMInterface(server_name)
    def handler(signum, frame):
        iface.close()

    signal.signal(signal.SIGBREAK, handler)
    signal.signal(signal.SIGINT, handler)

    client = MainClient()
    iface.register(client)

    while iface.running:
        time.sleep(0)

if __name__ == '__main__':
    main()
