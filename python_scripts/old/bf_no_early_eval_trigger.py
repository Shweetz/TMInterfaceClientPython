from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time

import numpy as np

class Trigger():
    def __init__(self, x1, y1, z1, x2, y2, z2) -> None:
        self.x1 = x1
        self.y1 = y1
        self.z1 = z1
        self.x2 = x2
        self.y2 = y2
        self.z2 = z2
    
    def is_triggered(self, pos):
        # print(pos)
        x, y, z = pos
        # print(self.x1, x, self.x2)
        if self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2 and self.z1 <= z <= self.z2:
            return True
        else:
            return False

# eval_time_min = 57900
# eval_time_max = 58200
eval_time_min = 59500
eval_time_max = 59500
trigger = Trigger(200, 40, 169, 238, 60, 170)

class MainClient(Client):
    def __init__(self) -> None:
        self.current_time = 0
        self.do_accept = -1
        self.lowest_time = 0
        self.current_speed = 0
        self.lowest_speed = 0
        self.phase = BFPhase.INITIAL

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller bruteforce')
        iface.execute_command('set bf_search_forever true')
    
    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        # print("bf")
        self.current_time = info.time - 2610
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING

        if self.current_time < eval_time_min:
            pass
        elif self.current_time <= eval_time_max:
            state = iface.get_simulation_state()
            pos = state.get_position()
            # if self.phase == BFPhase.INITIAL:
                # print(pos)
            if trigger.is_triggered(pos):
                self.current_speed = np.linalg.norm(state.get_velocity())
                
                if self.phase == BFPhase.INITIAL:
                    # print("a")
                    response.decision = BFEvaluationDecision.CONTINUE
                    if self.current_speed > self.lowest_speed:
                        self.lowest_speed = self.current_speed
                        print(f"!{self.current_speed} at  {self.current_time}")
                        
                if self.phase == BFPhase.SEARCH:
                    if self.current_speed > self.lowest_speed:
                        response.decision = BFEvaluationDecision.ACCEPT
                        print(f"{self.current_speed} at {self.current_time}")
                        self.lowest_speed = self.current_speed
        else:
            if self.phase == BFPhase.INITIAL:
                response.decision = BFEvaluationDecision.CONTINUE
                
            if self.phase == BFPhase.SEARCH:
                response.decision = BFEvaluationDecision.REJECT
                    
        return response

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
