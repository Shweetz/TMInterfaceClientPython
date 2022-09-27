# Common scripts - How to use
## 1. bf_precise_finish.py
Deactivate TMI's bruteforce 

Open the script with a text editor and set your inputs randomization "rules" and `FILL_INPUTS`


## 2. bf_height.py
Activate TMI's bruteforce 

Open the script and change the first line `TIME_MIN` with the time at which the car's height will be evaluated

This script tries to maximise the height of the car.

## 3. bf_nosedown.py
Activate TMI's bruteforce 

Open the script and change the first line `TIME_MIN` with the time at which the car's nose position will be evaluated

This script tries to make the nose of the car face down.

## 4. bf_speed.py
Activate TMI's bruteforce 

Open the script and change the first line `TIME_MIN` with the time at which the car's speed will be evaluated

This script tries to maximise the speed of the car.

## 5. bf_point.py
Activate TMI's bruteforce 

Open the script and change the first line `TIME_MIN` with the time at which the car's distance to a point will be evaluated

Also change `POINT`, the x,y,z coordinates of the point to get close to

This script tries to make the car go to a certain point.

## 6. bf_nosepos_jav.py
Activate TMI's bruteforce 

Open the script and change the first line `TIME_MIN` with the time at which the car's nose position will be evaluated

Nose position is yaw being closest to where the car is going, pitch is closest to 90° and roll to 0° (script by JaV)
