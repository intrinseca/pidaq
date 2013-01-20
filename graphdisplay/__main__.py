from protobuf import samples_pb2
import pylab
from protobuf.samples_pb2 import sample_stream

data = open("data.pro", "r")

stream = sample_stream()
stream.ParseFromString(data.read())

pylab.plot(stream.sample)
pylab.show()