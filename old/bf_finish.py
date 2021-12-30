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

	def on_run_step(self, iface, _time: int):
		cp_data = iface.get_checkpoint_state()
		# print(cp_data.cp_times)

		for i in range(len(cp_data.cp_states)):
			cp_data.cp_states[i] = True

		for i in range(len(cp_data.cp_times)):
			if cp_data.cp_times[i][0] == -1:
				cp_data.cp_times[i] = (_time, cp_data.cp_times[i][1])
				_time += 10

		# print(cp_data.cp_times)
		iface.set_checkpoint_state(cp_data)

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