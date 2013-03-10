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
            
        i = 0
        
        for d in data:
            if d <> next:
                raise Exception("Data Loss, expecting {}, got {} at offset {}".format(next, d, i))
            else:
                next += 1
                if next > 1023:
                    next = 0
            i += 1
        
        samples += len(data)
        duration = time.time() - starttime
        #time.sleep(0.01)
except KeyboardInterrupt:
    print("{} samples in {}, {}S/s".format(samples, duration, samples/duration))
except Exception as e:
    print(e)