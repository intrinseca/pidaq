import time
import pidaqif

p = pidaqif.PiDAQ(0, 0)

next = 0
samples = 0

starttime = time.time()

p.set_digital_out(0x56, 0xFF)

try:
    while True:
        data = p.get_samples()
        digital_in = p.get_digital_in();
        
        
        if len(data) == 0:
            continue
        
        print("data ({}): {}".format(len(data), data))
        print("digital in: {:2X}".format(digital_in));
        
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