import time
import pidaqif

p = pidaqif.PiDAQ(0, 0)

next = 0
samples = 0

starttime = time.time()

try:
    while True:
        data = p.get_samples()
        print("data ({}): {}".format(len(data), data))
        
        if samples <= 8 * 199:
            next = data[0]
        
        for d in data:
            if d <> next:
                raise Exception("Data Loss, expecting {}, got {}".format(next, d))
            else:
                next += 1
                if next > 255:
                    next = 0
        
        samples += len(data)
        duration = time.time() - starttime
except KeyboardInterrupt:
    print("{} samples in {}, {}S/s".format(samples, duration, samples/duration))