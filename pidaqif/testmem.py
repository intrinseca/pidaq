import pidaqif

p = pidaqif.PiDAQ(0, 0)

while True:
    p.get_samples()