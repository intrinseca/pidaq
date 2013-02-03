from protobuf import network_pb2, samples_pb2
from twisted.internet import protocol, reactor
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Factory
from twisted.protocols.basic import Int32StringReceiver
import struct
import uuid

def machine_id():
    # uuid.getnode will usually return the system MAC address as a 48 bit int
    # struct.pack for a long long (Q) gives eight bytes, so we slice off the first six
    return struct.pack("Q", uuid.getnode())[0:6]

class ProtobufProtocol(Int32StringReceiver):
    def sendMessage(self, message):
        #print("ProtobufProtocol: Sending")
        self.sendString(message.SerializeToString())
        #print("ProtobufProtocol: Sent")
  
    def stringReceived(self, data):
        #print("ProtobufProtocol: Received")
        message = network_pb2.network_message()
        message.ParseFromString(data)
        self.messageReceived(message)
    
    def messageReceived(self, message):
        print(message)
  
    def connectionMade(self):
        print("ProtobufProtocol: Connected")
    
    def connectionLost(self, reason=ConnectionDone):
        print("ProtobufProtocol: Connection Lost")
        print(reason)
    
class ProtobufProtocolFactory(Factory):
    def buildProtocol(self, addr):
        return ProtobufProtocol()

class SampleStreamProtocol(ProtobufProtocol):
    def sendSample(self, timestamp, value):      
        m = network_pb2.network_message()
        m.sample.timestamp = timestamp
        m.sample.value = value
        self.sendMessage(m)

class SampleStreamProtocolFactory(Factory):
    def buildProtocol(self, addr):
        return SampleStreamProtocol()