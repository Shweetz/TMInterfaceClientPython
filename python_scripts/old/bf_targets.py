from tminterface.structs import BFEvaluationDecision, BFEvaluationInfo, BFEvaluationResponse, BFPhase, BFTarget
from tminterface.interface import TMInterface
from tminterface.client import Client
import sys
import signal
import time

import numpy as np

def get_cp_times(iface):
	cp_times = iface.get_checkpoint_state().cp_times
	return [time for (time, _) in cp_times if time != -1]

class MainClient(Client):
	def __init__(self) -> None:
		self.current_time = 0
		self.lowest_time = 0
		self.phase = BFPhase.INITIAL
		self.current_ending_pos = 0
		self.target_ending_pos = 0
		self.better = False

	def on_registered(self, iface: TMInterface) -> None:
		print(f'Registered to {iface.server_name}')
		iface.execute_command('set controller bruteforce')
		iface.execute_command('set bf_search_forever true')
	
	def on_simulation_begin(self, iface):
		self.lowest_time = iface.get_event_buffer().events_duration

	def on_bruteforce_evaluate(self, iface, info: BFEvaluationInfo) -> BFEvaluationResponse:
		self.current_time = info.time - 2610
		self.phase = info.phase

		response = BFEvaluationResponse()
		response.decision = BFEvaluationDecision.DO_NOTHING

		if self.better:
			print("************** BETTER")
			print(f"{self.min_cps}: OLD")
			print(f"{self.current_cps}: NEW")
			response.decision = BFEvaluationDecision.ACCEPT
		elif self.current_time > self.lowest_time:
			response.decision = BFEvaluationDecision.REJECT

		self.better = False

		return response

	def on_checkpoint_count_changed(self, iface, current: int, target: int):
		if current == target:
			if self.phase == BFPhase.INITIAL:
				self.lowest_time = self.current_time
				self.min_cps = get_cp_times(iface)
				# print(self.min_cps)
				
			elif self.phase == BFPhase.SEARCH:
				self.current_cps = get_cp_times(iface)
				# print(self.current_cps)
				
				# if len(self.current_cps) >= len(self.min_cps):				
					# my_zip = list(zip(self.current_cps, self.min_cps))
					# print(my_zip)
					# my_zip.reverse()
					# for cur, min in my_zip:
				for i in range(len(self.min_cps)-1, 0, -1):
					if self.current_cps[i] < self.min_cps[i]:
						self.better = True
		
		if self.better:
			self.min_cps.append(self.lowest_time)
			self.current_cps.append(self.current_time)

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