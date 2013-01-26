from net import ProtobufProtocol
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.protocols import basic
from protobuf.network_pb2 import network_message, storage_command
from uuid import uuid1

class CLI(basic.LineReceiver):
    from os import linesep as delimiter

    def connectionMade(self):
        self.transport.write('>>> ')

    def lineReceived(self, line):
        if line == "start":
            command = network_message()
            command.storage_command.start_session = True
            command.storage_command.session_id = uuid1().bytes
            self.control.sendCommand(command)
        elif line == "stop":
            command = network_message()
            command.storage_command.stop_session = True
            self.control.sendCommand(command)            
        
        self.transport.write('>>> ')

class StorageEngineControl(ProtobufProtocol):
    pass

class StorageEngineControlFactory(ReconnectingClientFactory):
    def buildProtocol(self, addr):
        self.protocol = StorageEngineControl()
        self.resetDelay()
        return self.protocol
    
    def sendCommand(self, message):
        self.protocol.sendMessage(message)