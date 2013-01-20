from protobuf import samples_pb2
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from net import ProtobufProtocolFactory

print("Server Started")

reactor.listenTCP(1234, ProtobufProtocolFactory())
reactor.run()