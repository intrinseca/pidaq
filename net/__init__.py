from protobuf import network_pb2, samples_pb2
from twisted.internet import protocol, reactor
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Factory, DatagramProtocol
from twisted.protocols.basic import Int32StringReceiver
import struct
import uuid

def machine_id():
    # uuid.getnode will usually return the system MAC address as a 48 bit int
    # struct.pack for a long long (Q) gives eight bytes, so we slice off the first six
    return struct.pack("Q", uuid.getnode())[0:6]


class LiveStream(DatagramProtocol):
    def startProtocol(self):
        self.receive_buffer = bytearray()
        self.hosts = []
        self.target = None
    
    def send_samples(self, samples):
        buffer = ""
        
        for s in samples:
            buffer += struct.pack("<H", s)
        
        for host in self.hosts:
            self.transport.write(buffer, (host, 1234))
    
    def datagramReceived(self, data, (host, port)):
        self.receive_buffer.extend(data)
        count = 0
        
        while len(self.receive_buffer) >= 2:
            sample, = struct.unpack_from("<H", buffer(self.receive_buffer))
            if self.target is not None:
                self.target.append(sample)
            del self.receive_buffer[0:2]
            count += 1
        
        #print count

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