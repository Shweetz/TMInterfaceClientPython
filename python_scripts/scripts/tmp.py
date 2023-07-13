import math

x_old = 5
y_old = 0

# change center: target point is new 0,0
x_tar = 2
y_tar = -3

x_mid = x_old - x_tar
y_mid = y_old - y_tar

print(x_mid)
print(y_mid)

# transpose with target direction
angle = math.pi / 2.5

x_new = x_mid * math.cos(angle) - y_mid * math.sin(angle)
y_new = x_mid * math.sin(angle) + y_mid * math.cos(angle)

print(x_new)
print(y_new)