from net import ProtobufProtocol
from protobuf import network_pb2
from twisted.internet.protocol import Factory
from uuid import UUID

class ControlProtocol(ProtobufProtocol):
    def __init__(self, store):
        self.store = store
    
    def messageReceived(self, message):
        command = message.storage_command
        if command.start_session:
            self.store.start_session(UUID(bytes=command.session_id))
        elif command.stop_session:
            self.store.stop_session()
        elif command.show_data:
            message = network_pb2.network_message()
            message.sample_stream.samples.extend(self.store.protocols[0].session.query())
            self.sendMessage(message)
        
class ControlFactory(Factory):
    def buildProtocol(self, addr):
        return ControlProtocol(self.store)