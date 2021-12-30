
from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

import math
import numpy
import sys
import time

# MUST GIVE INPUTS TIME FOR ON_RUN_STEP
# INPUTS_TIME = 26200
# print(f"Base time={INPUTS_TIME/1000}")

PRECISION = 0.001

# state = iface.get_simulation_state()
# state.velocity = [100, 0, 0]
# iface.rewind_to_state(state)

class MainClient(Client):
    def __init__(self) -> None:
        self.cp_count = -1
        self.lowest_time = -1
        self.best_time = -1
        self.base_velocity = None
        self.finish_crossed = False
        # self.nb_rewinds = 0
        self.min_coeff = 0
        self.max_coeff = 1
        self.best_precise_time = -1
        self.time_with_speed_coeff = -1
        self.printed = False
        self.simulation = False
        self.states = []
        self.phase = BFPhase.INITIAL
        self.bf_response = BFEvaluationDecision.DO_NOTHING

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')

    def on_simulation_begin(self, iface):
        iface.remove_state_validation()
        self.simulation = True
        # self.lowest_time = iface.get_event_buffer().events_duration

    def on_simulation_end(self, iface, result: int):
        self.simulation = False

    def on_run_step(self, iface, _time):

        # Let run play until finish to detect base time first, and store it in self.lowest_time
        if self.lowest_time == -1:
            if self.finish_crossed:
                self.lowest_time = _time-10
                print(f"{self.lowest_time=}")
                iface.rewind_to_state(self.states[-3])
                self.finish_crossed = False
            else:
                self.states.append(iface.get_simulation_state())
            return

        if _time == 0:
            self.printed = False
            
        if self.max_coeff - self.min_coeff > PRECISION:
            self.on_step(iface, _time)
        elif not self.printed:
            print(f"{self.time_with_speed_coeff:.4f}")
            self.printed = True
            self.finish_crossed = False
            self.min_coeff = 0
            self.max_coeff = 1
            
    def on_simulation_step(self, iface, _time):
        # Let run play until finish to detect base time first, and store it in self.lowest_time
        if self.lowest_time == -1:
            if self.finish_crossed:
                self.lowest_time = _time-10
                print(f"{self.lowest_time=}")
                if self.best_time == -1:
                    self.best_time = self.lowest_time
                iface.rewind_to_state(self.states[-3])
                self.finish_crossed = False
            else:
                self.states.append(iface.get_simulation_state())
            return

        # if self.max_coeff - self.min_coeff > PRECISION:
        self.on_step(iface, _time)

        # if self.best_time == -1:
        #     self.best_time = self.lowest_time
        #     print(f"{self.best_time=}")

        if self.best_time == self.lowest_time:
            if self.max_coeff - self.min_coeff > PRECISION:
                # current iteration needs more investigation
                return
            elif PRECISION < self.max_coeff - self.min_coeff < PRECISION * 3:
                self.states.append(iface.get_simulation_state())
                return
            else:
                if self.time_with_speed_coeff < self.best_precise_time or self.best_precise_time == -1:
                    self.best_precise_time = self.time_with_speed_coeff
                    self.bf_response = BFEvaluationDecision.ACCEPT
                    print(f"accept {self.lowest_time}")
                    print(f"accept {self.time_with_speed_coeff}")
                else:
                    self.bf_response = BFEvaluationDecision.REJECT
                    # print(f"reject {self.time_with_speed_coeff}")
                # iface.rewind_to_state(self.states[-1])

        elif self.lowest_time < self.best_time:
            self.bf_response = BFEvaluationDecision.ACCEPT
            print(f"accept {self.lowest_time} better than {self.best_time}")
            self.best_time = self.lowest_time
        elif self.lowest_time > self.best_time:
            self.bf_response = BFEvaluationDecision.REJECT
            # print(f"reject {self.lowest_time} worse than {self.best_time}")

        self.finish_crossed = False
        self.min_coeff = 0
        self.max_coeff = 1
        self.lowest_time = -1

    def on_step(self, iface, _time):
        if _time < self.lowest_time - 10:
            return

        # print(f"s {_time}")
        if _time == self.lowest_time - 10:
            self.min_coeff = 0
            self.max_coeff = 1

        if _time == self.lowest_time - 10:
            # Save base state to rewind before any change
            self.base_state = iface.get_simulation_state()
            
            # print()

        if _time == self.lowest_time:
            self.coeff = (self.min_coeff + self.max_coeff) / 2

            self.state = iface.get_simulation_state()

            # Save base run velocity
            if not self.base_velocity:
                self.base_velocity = self.state.velocity

            # Apply a coefficient to the speed on the last tick
            self.state.velocity = [v * self.coeff for v in self.base_velocity]
            iface.rewind_to_state(self.state)

            # print(f"pos_z={self.state.position[2]}")
            # print(f"vel_z={self.state.velocity[2]}")

        if _time == self.lowest_time + 10:
            # print(f"pos_z={iface.get_simulation_state().position[2]} (tick+1)")

            self.time_with_speed_coeff = (_time-10 + self.coeff*10) / 1000

            if self.finish_crossed:
                # print(f"finish with {self.coeff}")
                # print(f"{self.time_with_speed_coeff}: finish")
                self.max_coeff = self.coeff
            else:
                # print(f"no finish with {self.coeff}")
                # print(f"{self.time_with_speed_coeff}: no finish")
                self.min_coeff = self.coeff

            # time.sleep(0.1)
            # iface.prevent_simulation_finish()
            if self.max_coeff - self.min_coeff > PRECISION:
                iface.rewind_to_state(self.base_state)
            self.finish_crossed = False
            # self.nb_rewinds += 1
            # self.rewinded = True

        if _time >= self.lowest_time + 20:
            self.min_coeff = 0
            self.max_coeff = 0
            self.time_with_speed_coeff = _time / 1000


    def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
        self.phase = info.phase

        response = BFEvaluationResponse()
        response.decision = BFEvaluationDecision.DO_NOTHING

        # self.bf_response = BFEvaluationDecision.DO_NOTHING

        if self.best_time == self.lowest_time:
            if self.max_coeff - self.min_coeff < PRECISION:
        # if self.time_with_speed_coeff != -1:
                if self.time_with_speed_coeff < self.best_precise_time or self.best_precise_time == -1:
                    self.best_precise_time = self.time_with_speed_coeff
                    response.decision = BFEvaluationDecision.ACCEPT
                    print(f"accept {self.time_with_speed_coeff}")
                else:
                    response.decision = BFEvaluationDecision.REJECT
                print(f"{self.time_with_speed_coeff=} {self.best_precise_time=}")


                self.time_with_speed_coeff = -1

        self.finish_crossed = False
        self.min_coeff = 0
        self.max_coeff = 1
        self.lowest_time = -1

        return response

    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        # print("c")
        self.cp_count = current
        if current == target:
            # print("true")
            self.finish_crossed = True
            iface.prevent_simulation_finish()

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
