
from dataclasses import dataclass

@dataclass
class Iteration:
    time: float
    distance : float
    velocity : float

def donadigo(strategy, time, distance, velocity, prev):
    if strategy == 'distance' or strategy == 'distance,velocity':
        if time < prev.time:
            return True
            
        if strategy == 'distance,velocity':
            return abs(distance - prev.distance) < 0.01 and velocity > prev.velocity
        else:
            return distance < prev.distance
    elif strategy == 'velocity':
        return velocity > prev.velocity

def test1():
    strategy = "distance,velocity"
    
    iter = Iteration(5.48, 0.1, 1000)
    prev = Iteration(5.48, 999, 1)

    if not donadigo(strategy, iter.time, iter.distance, iter.velocity, prev):
        print("How is 1000 velocity worse than 1 velocity?")

def test2():
    strategy = "distance,velocity"
    
    iter = Iteration(9.99, 0.005, 101)
    prev = Iteration(0.01, 0.004, 100)

    if donadigo(strategy, iter.time, iter.distance, iter.velocity, prev):
        print("How is 9.99 better time than 0.01?")

def main():
    test1()
    test2()

if __name__ == '__main__':
    main()