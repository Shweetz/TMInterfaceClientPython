from tminterface.interface import TMInterface
from tminterface.client import Client
import numpy
import sys
import signal
import time

class MainClient(Client):
    def __init__(self) -> None:
        pass

    def on_registered(self, iface: TMInterface) -> None:
        print(f'Registered to {iface.server_name}')
        iface.register_custom_command('custom')

    def on_run_step(self, iface: TMInterface, _time: int):
        if _time >= 0:
            state = iface.get_simulation_state()

            speed = numpy.linalg.norm(state.velocity) * 3.6
            novspeed = numpy.linalg.norm([state.velocity[0], state.velocity[2]]) * 3.6

            print(f'Time: {_time}, Real Speed: {speed:.3f} kmh, No Vertical Speed: {novspeed:.3f} kmh')

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
