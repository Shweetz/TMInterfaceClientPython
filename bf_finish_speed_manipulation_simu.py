
from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase
from tminterface.interface import TMInterface
from tminterface.client import Client, run_client

import datetime
from enum import IntEnum
import math
import numpy
import shutil
import sys
import time

PRECISION = 0.0001
LOCK_BASE_RUN = True

class MainClient(Client):
    def __init__(self) -> None:
        self.cp_count = -1
        self.lowest_time = -1
        self.best_time = -1
        self.base_velocity = None
        self.finish_crossed = False
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

    def on_simulation_step(self, iface, _time):
        self.race_time = _time

        # Let run play until finish to detect base time first, and store it in self.lowest_time
        if self.lowest_time == -1:
            if self.finish_crossed:
                # self.save_inputs(f"last_time={self.time_with_speed_coeff}", iface)
                self.lowest_time = _time-10
                # print(f"{self.lowest_time=}")
                # time.sleep(1)
                if self.best_time == -1:
                    self.best_time = self.lowest_time
                iface.rewind_to_state(self.states[-3])
                self.finish_crossed = False
                self.base_velocity = None
            else:
                if _time > 4390:
                    self.lowest_time = _time
                self.states.append(iface.get_simulation_state())
            return

        # if self.max_coeff - self.min_coeff > PRECISION:
        self.on_step(iface, _time)
        # time.sleep(1)

        # if self.best_time == -1:
        #     self.best_time = self.lowest_time
        #     print(f"{self.best_time=}")

        if self.best_time == self.lowest_time:
            if self.max_coeff - self.min_coeff > PRECISION:
                # print("a")
                # current iteration needs more investigation
                return
            elif PRECISION < self.max_coeff - self.min_coeff < PRECISION * 3:
                # print("b")
                self.states.append(iface.get_simulation_state())
                return
            else:
        #         # print("c")
                if self.time_with_speed_coeff < self.best_precise_time or self.best_precise_time == -1:
                    inputs = iface.get_event_buffer().to_commands_str()
                    # or save event_buffer for later?
                    # or save an entire state?
                    # or restore a previous state?

    def on_step(self, iface, _time):
        if _time < self.lowest_time - 10:
            return

        # print(f"s {_time}")
        if _time == self.lowest_time - 10:
            self.min_coeff = 0
            self.max_coeff = 1
            # self.base_velocity = None

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
            # if self.max_coeff - self.min_coeff > PRECISION:
            iface.rewind_to_state(self.base_state)
            self.finish_crossed = False
            # print(f"{self.finish_crossed=}")
            # self.nb_rewinds += 1
            # self.rewinded = True

        # if _time >= self.lowest_time + 20:
        #     self.min_coeff = 0
        #     self.max_coeff = 0
        #     self.time_with_speed_coeff = _time / 1000


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
                    response.decision = BFEvaluationDecision.REJECT
                    print(f"accept {self.time_with_speed_coeff}")
                    self.save_result("", iface)
                else:
                    response.decision = BFEvaluationDecision.REJECT
                # print(f"{self.time_with_speed_coeff=} {self.best_precise_time=}")


                # self.time_with_speed_coeff = -1
                self.finish_crossed = False
                self.lowest_time = -1
                self.min_coeff = 0
                self.max_coeff = 1
                
        elif self.best_time < self.lowest_time:
            response.decision = BFEvaluationDecision.REJECT
            self.finish_crossed = False
            self.lowest_time = -1
            self.min_coeff = 0
            self.max_coeff = 1

        return response

    def on_checkpoint_count_changed(self, iface, current: int, target: int):
        # print("c")
        self.cp_count = current
        if current == target:
            self.finish_crossed = True
            # print(f"Finished race at {self.race_time}")
            # print(f"{self.finish_crossed=}")
            # iface.prevent_simulation_finish()
        
    def save_inputs(self, result_name, iface):
        tmp_file = "C:/Users/rmnlm/Documents/TMInterface/Scripts/result_tmp.txt"
        tmp_file = fr"C:/Users/rmnlm/Documents/TMInterface/Scripts/{result_name}.txt"
        with open(tmp_file, "w") as f:
            f.write(iface.get_event_buffer().to_commands_str())
        time.sleep(1)

    def save_result(self, result_name, iface):
        tmp_file = "C:/Users/rmnlm/Documents/TMInterface/Scripts/result_tmp.txt"
        res_file = "C:/Users/rmnlm/Documents/TMInterface/Scripts/result.txt"
        shutil.copy2(tmp_file, res_file)

        # Copy result.txt in another file
        date = datetime.datetime.now()
        date = date.strftime("%Y%m%d_%H%M%S")
        dest = res_file.replace("result.txt", f"{date}_{result_name}.txt")
        shutil.copy2(res_file, dest)

def main():
    server_name = f'TMInterface{sys.argv[1]}' if len(sys.argv) > 1 else 'TMInterface0'
    print(f'Connecting to {server_name}...')
    run_client(MainClient(), server_name)

if __name__ == '__main__':
    main()
