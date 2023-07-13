# TODO is_better if SCRIPT_ACCEPT

from dataclasses import dataclass
import sys

from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

@dataclass
class Trigger:
    # time is minimum time when the trigger and all previous have been crossed in initial phase
    # so if bruteforce rewinds past a trigger time, they should be noted as already crossed
    x1: int; y1: int; z1: int; x2: int; y2: int; z2: int; time = 0

    def __post_init__(self):
        self.minX, self.maxX = sorted([self.x1, self.x2])
        self.minY, self.maxY = sorted([self.y1, self.y2])
        self.minZ, self.maxZ = sorted([self.z1, self.z2])

SCRIPT_ACCEPT = False # True so the script accepts/rejects iterations, False so that TMI does
EVAL_TIME_MIN = 32500
EVAL_TIME_MAX = EVAL_TIME_MIN

TRIGGERS = []
TRIGGERS.append(Trigger(517, 9, 465, 510, 15, 470))
TRIGGERS.append(Trigger(522, 9, 480, 550, 15, 550))

class MainClient(Client):
    def __init__(self) -> None:
        self.best = -1
        self.time = -1
        self.time_min = EVAL_TIME_MIN
        self.time_max = EVAL_TIME_MAX
        self.last_time = 0
        self.next_trigger_to_check = 0

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.execute_command('set controller bruteforce')

    def on_simulation_begin(self, iface):
        self.lowest_time = iface.get_event_buffer().events_duration
        print(f"Base run time: {self.lowest_time}")
        if not (EVAL_TIME_MIN <= EVAL_TIME_MAX <= self.lowest_time) and SCRIPT_ACCEPT:
            print("ERROR: MUST HAVE 'EVAL_TIME_MIN <= EVAL_TIME_MAX <= REPLAY_TIME'")

    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING

        if not SCRIPT_ACCEPT:
            self.time_min = info.inputs_min_time
            self.time_max = min(self.lowest_time, info.override_stop_time)
            # print(f"{self.time_min=}")
            # print(f"{self.time_max=}")

        self.current_time = info.time
        self.phase = info.phase
        
        if self.current_time < self.last_time:
            # print("bruteforce rewinded")
            self.get_next_trigger_to_check()

        if self.phase == BFPhase.INITIAL:
            # check if next trigger has been reached, if yes store it in trig.time
            while self.next_trigger_to_check < len(TRIGGERS):
                trig = TRIGGERS[self.next_trigger_to_check]
                if self.is_car_in_trigger(trig, iface):
                    #if trig.time == 0:
                    #print("initial hit")
                    trig.time = self.current_time
                    self.next_trigger_to_check += 1
                else:
                    break
            
            if SCRIPT_ACCEPT:
                if self.is_eval_time() and self.is_better(iface) and self.next_trigger_to_check == len(TRIGGERS):
                    self.best = self.current
                    self.time = self.current_time

                if self.is_max_time():
                    print(f"base at {self.time}: {self.best=}, number of triggers crossed={self.next_trigger_to_check}/{len(TRIGGERS)}")

        elif self.phase == BFPhase.SEARCH:
            while self.next_trigger_to_check < len(TRIGGERS):
                trig = TRIGGERS[self.next_trigger_to_check]
                if self.is_car_in_trigger(trig, iface):
                    self.next_trigger_to_check += 1
                    print(f"trigger {self.next_trigger_to_check}: hit")
                else:
                    break

            if SCRIPT_ACCEPT:
                if self.is_eval_time() and self.is_better(iface) and self.next_trigger_to_check == len(TRIGGERS):
                    response.decision = BFEvaluationDecision.ACCEPT
                            
                if self.is_past_eval_time():
                    if response.decision != BFEvaluationDecision.ACCEPT:
                        response.decision = BFEvaluationDecision.REJECT
            else:
                if self.is_past_eval_time():
                    response.decision = BFEvaluationDecision.REJECT
                # CONTINUE if triggers crossed, else DO_NOTHING (don't accept)
                if self.next_trigger_to_check == len(TRIGGERS):
                    response.decision = BFEvaluationDecision.CONTINUE

        self.last_time = self.current_time

        return response

    def is_better(self, iface):
        self.current = iface.get_simulation_state().position[1]
        return self.best == -1 or self.current > self.best

    def is_eval_time(self):
        return self.time_min <= self.current_time <= self.time_max

    def is_past_eval_time(self):
        return self.time_max <= self.current_time

    def is_max_time(self):
        return self.time_max == self.current_time

    def is_car_in_trigger(self, trig, iface):
        pos = iface.get_simulation_state().position
        return trig.minX <= pos[0] <= trig.maxX and trig.minY <= pos[1] <= trig.maxY and trig.minZ <= pos[2] <= trig.maxZ

    def get_next_trigger_to_check(self):
        self.next_trigger_to_check = 0
        
        if not SCRIPT_ACCEPT:
            while self.next_trigger_to_check < len(TRIGGERS):
                trig = TRIGGERS[self.next_trigger_to_check]
                if self.current_time > trig.time and trig.time != 0:
                    self.next_trigger_to_check += 1
                    #print(f"trigger {self.next_trigger_to_check}: rewind past")
                else:
                    break


def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
