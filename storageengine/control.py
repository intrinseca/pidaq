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
            sid = UUID(bytes=command.session_id)
            self.store.start_session(sid)
            print("Session Started: %s" % sid)
        elif command.stop_session:
            self.store.stop_session()
            print("Session Stopped")
        elif command.show_data:
            if command.start_sample:
                start = command.start_sample
            else:
                start = 0
            
            (timestamp, samples) = self.store.session.query(start)
            message = network_pb2.network_message()
            message.sample_stream.timestamp = timestamp
            message.sample_stream.samples.extend(samples)
            self.sendMessage(message)
        elif command.stream_to:
            self.store.live_stream.hosts.append(command.stream_to)
        
class ControlFactory(Factory):
    def buildProtocol(self, addr):
        return ControlProtocol(self.store)
