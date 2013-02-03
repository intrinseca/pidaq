from net import ProtobufProtocol
from protobuf.network_pb2 import network_message, storage_command
from twisted.internet.protocol import ReconnectingClientFactory, Factory
from twisted.internet.task import LoopingCall
from twisted.protocols import basic
from uuid import uuid1

class CLI(basic.LineReceiver):
    def __init__(self, control):
        self.control = control

    def connectionMade(self):
        self.transport.write('>>> ')

    def lineReceived(self, line):
        if line == "start":
            self.control.start_session()
            self.transport.write("Started session\r\n")
        elif line == "stop":
            self.control.stop_session()
            self.transport.write("Session ended\r\n")         
        elif line == "show":
            self.control.get_data() 
            self.transport.write("Showing data\r\n")         
        
        self.transport.write('>>> ')

class CLIFactory(Factory):
    def __init__(self, control):
        self.control = control
    
    def buildProtocol(self, addr):
        return CLI(self.control)

class StorageEngineControl(ProtobufProtocol):
    def messageReceived(self, message):
        self.factory.messageReceived(message)

class StorageEngineControlFactory(ReconnectingClientFactory):
    def __init__(self):
        self.handlers = []
    
    def buildProtocol(self, addr):
        self.protocol = StorageEngineControl()
        self.protocol.factory = self
        self.resetDelay()
        self.start_refresh()
        return self.protocol
    
    def add_handler(self, handler):
        self.handlers.append(handler)
    
    def messageReceived(self, message):
        for handler in self.handlers:
            handler(message)
    
    def start_session(self):
        sid = uuid1()
        command = network_message()
        command.storage_command.start_session = True
        command.storage_command.session_id = sid.bytes
        self.protocol.sendMessage(command)
    
    def stop_session(self):
        command = network_message()
        command.storage_command.stop_session = True
        self.protocol.sendMessage(command)
    
    def get_data(self):
        if self.protocol.connected:
            command = network_message()
            command.storage_command.show_data = True
            self.protocol.sendMessage(command)
    
    def start_refresh(self):        
        self._timer = LoopingCall(self.get_data)
        self._timer.start(0.5)
    
    def stop_refresh(self):
        self._timer.stop()
