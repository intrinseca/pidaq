from protobuf import samples_pb2
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from net import ProtobufProtocol
from twisted.internet.protocol import Factory, ClientFactory
from twisted.internet.error import ConnectionDone

class SampleLog(ProtobufProtocol):
    def __init__(self, logFile):
        self._logFile = open(logFile, "w")
        self.stream = samples_pb2.sample_stream()
    
    def messageReceived(self, message):
        samples = message.sample_stream.sample
        self.stream.sample.extend(samples)
        print(samples)
    
    def connectionLost(self, reason=ConnectionDone):
        self._logFile.write(self.stream.SerializeToString())
        self._logFile.close()
        print("Written to File")

class SampleLogFactory(ClientFactory):
    def buildProtocol(self, addr):
        return SampleLog("data.pro")
