# Common scripts - How to use
For all scripts but bf_precise_finish.py, open the script with a text editor and change EVAL_TIME_MIN with the timestamp of the tick where the car data will be evaluated. 

You can also change EVAL_TIME_MAX to evaluate the car at all ticks between EVAL_TIME_MIN and EVAL_TIME_MAX.

## 1. bf_precise_finish.py
Open the script with a text editor and set your inputs randomization "rules" and FILL_INPUTS


## 2. bf_height.py
The car's height will be evaluated (maximized)


## 3. bf_nosedown.py
The car's nose position will be evaluated


## 4. bf_speed.py
The car's speed will be evaluated (maximized)


## 5. bf_point.py
The car's distance to a point will be evaluated (minimized)

You also need to edit POINT in the script, the x,y,z coordinates of the point to get close to


## 6. bf_nosepos_jav.py / bf_nosepos_speed.py
The car's nose position will be evaluated

Nose position is yaw being closest to where the car is going, pitch is closest to 90° and roll to 0° (script by JaV)
