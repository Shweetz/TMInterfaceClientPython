from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time

class MainClient(Client):
    def __init__(self) -> None:
        self.lowest_time = 1000000
        self.lowest_dist = 1000000
        self.current_time = 1000000
        self.current_dist = 1000000
        # self.eval_time = -1
        self.do_accept = False
        self.do_reject = False
        self.force_accept = False
        self.phase = BFPhase.INITIAL
        self.goal = "find_uber"
        self.iterations = 0
        self.iterations_after_uber = 0
        self.save = ""
        self.is_base_run_saved = False
        self.iterations = 0

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
        response.decision = BFEvaluationDecision.CONTINUE
        
            
        if self.phase == BFPhase.SEARCH and self.current_time == 60000:
            if self.iterations % 100 == 0:
                print(f"{self.iterations=}")
            self.iterations += 1
        
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
