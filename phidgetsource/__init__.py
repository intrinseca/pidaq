from protobuf import samples_pb2, network_pb2
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from net import ProtobufProtocolFactory
from twisted.python import log

s = samples_pb2.Sample()
s.timestamp = 10
s.value = 1024

print(s)

def gotProtocol(p):
    m = network_pb2.network_message()
    m.sample.CopyFrom(s)
    p.sendMessage(m)
    p.transport.loseConnection()

point = TCP4ClientEndpoint(reactor, "localhost", 1234)
d = point.connect(ProtobufProtocolFactory())
d.addCallback(gotProtocol)
d.addErrback(log.err)
reactor.run()

print("Done")