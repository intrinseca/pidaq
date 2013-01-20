from protobuf import samples_pb2
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from net import ProtobufProtocol
from twisted.internet.protocol import Factory, ClientFactory

class SampleLog(ProtobufProtocol):
    def __init__(self, logFile):
        self._logFile = logFile
    
    def messageReceived(self, message):
        print("%d %d" % (message.sample.timestamp, message.sample.value))
        self._logFile.write(message.sample.SerializeToString() + "\n")
        self._logFile.flush()

class SampleLogFactory(ClientFactory):
    def startFactory(self):
        self._logFile = open("data.prl", "w")
    
    def stopFactory(self):
        self._logFile.close()
    
    def buildProtocol(self, addr):
        return SampleLog(self._logFile)


reactor.connectTCP("raspberrypi", 1234, SampleLogFactory())
reactor.run()