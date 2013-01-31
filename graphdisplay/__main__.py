from protobuf import samples_pb2
from protobuf.samples_pb2 import sample_stream
import os
import pylab

#get session list
sessions = os.listdir("storage")

print("Available Sessions:")
i = 1
for folder in sessions:
    print("  %d. %s" % (i, folder))
    i += 1

#session chooser
session = sessions[0]
blocks = os.listdir(os.path.join("storage", session))

blocks = sorted(blocks, key = lambda x: int(x))

samples = []

for block in blocks:
    print(block)
    block_file = open(os.path.join("storage", session, block), "r")
    stream = sample_stream()
    stream.ParseFromString(block_file.read())
    samples.extend(stream.sample)
    
pylab.plot(samples)
pylab.grid()
pylab.show()