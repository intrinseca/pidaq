from twisted.internet.protocol import Factory
from net import ProtobufProtocol
from uuid import UUID
from graphdisplay import plot_samples

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
            plot_samples(self.store.protocols[0].session.query())
        
class ControlFactory(Factory):
    def buildProtocol(self, addr):
        return ControlProtocol(self.store)