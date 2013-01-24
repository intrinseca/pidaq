from twisted.internet.protocol import ClientFactory
from protobuf import samples_pb2
from twisted.internet.error import ConnectionDone
from net import ProtobufProtocol

class StorageProtocol(ProtobufProtocol):
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

class StorageFactory(ClientFactory):
    def buildProtocol(self, addr):
        return StorageProtocol("data.pro")