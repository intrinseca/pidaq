from twisted.internet import protocol, reactor
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver, Int32StringReceiver
from twisted.internet.error import ConnectionDone

from protobuf import network_pb2

class SamplesProtocol(LineReceiver):
  def __init__(self):
    self.setRawMode()
  
  def rawDataReceived(self, data):
    #self.transport.write(data)
    print(data)
        
  def sendData(self, data):
    print("SamplesProtocol: Sending {0}" % data)
    self.transport.write(data)
  
  def connectionMade(self):
    print("SamplesProtocol: Connected")

class SamplesFactory(Factory):
    def buildProtocol(self, addr):
        return SamplesProtocol()

class SamplesServerFactory(protocol.ServerFactory):
    protocol = SamplesProtocol

class ProtobufProtocol(Int32StringReceiver):
  def sendMessage(self, message):
    print("ProtobufProtocol: Sending")
    self.sendString(message.SerializeToString())
    print("ProtobufProtocol: Sent")
  
  def stringReceived(self, data):
    print("ProtobufProtocol: Received")
    message = network_pb2.network_message()
    message.ParseFromString(data)
    print(message)
  
  def connectionMade(self):
    print("ProtobufProtocol: Connected")
    
  def connectionLost(self, reason=ConnectionDone):
    print("ProtobufProtocol: Connection Lost")
    print(reason)
    
class ProtobufProtocolFactory(Factory):
      def buildProtocol(self, addr):
        return ProtobufProtocol()
