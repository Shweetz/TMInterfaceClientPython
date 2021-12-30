from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time

import numpy as np

start_eval_time = 49250

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

        if self.current_time >= start_eval_time:
            response.decision = BFEvaluationDecision.CONTINUE

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
