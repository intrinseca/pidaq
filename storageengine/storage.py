from Queue import Queue
from google.protobuf import text_format
from net import ProtobufProtocol
from protobuf import samples_pb2
from twisted.internet import reactor
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import ReconnectingClientFactory
from uuid import UUID, uuid1
import math
import os
import struct
import uuid


class Session:
    def __init__(self, sid, persistent=False):
        self.sid = sid
        self.persistent = persistent
        
        self.sample_count = 0
        self.machine_id = [0, 0, 0, 0, 0, 0]
        
        self.block_pool = None
        self.blocks = []
        self.block_size = Block.size
    
    def path(self):
        return str(self.sid)
    
    def query(self, start=0, end=None):
        samples = []
        
        start_block = int(math.floor(start / Block.size))
        
        if not end:
            blocks = self.blocks[start_block:]
        else:
            end_block = int(math.ceil(end / Block.size))
            blocks = self.blocks[start_block:end_block + 1]
        
        for block_id in blocks:
            block_file = open(os.path.join("storage", self.path(), str(block_id)), "rb")
            block = Block.deserialize(block_file.read(), self)
            samples.extend(block.samples)
        
        return samples
    
    def serialize(self):
        session = samples_pb2.session()
        session.session_id = self.sid.bytes
        session.blocks.extend(map(lambda x: x.bytes, self.blocks))
        return session.SerializeToString()
        #return text_format.MessageToString(session)
    
    @staticmethod
    def deserialise(serialized):
        session_pb = samples_pb2.session()
        session_pb.ParseFromString(serialized)
        #text_format.Merge(serialized, session_pb)
        
        session = Session(UUID(bytes=session_pb.session_id))
        session.blocks = map(lambda x: UUID(bytes=x), session_pb.blocks)
        
        return session

class Block:
    size = 10
    
    def __init__(self):
        self.reset()
    
    def full(self):
        return len(self.samples) >= Block.size
    
    def reset(self):
        self.block_id = uuid1()
        self.timestamp = 0
        self.channel = 0
        self.written = False
        self.free = True
        self.samples = []
    
    def path(self):
        return os.path.join(self.session.path(), str(self.block_id))
    
    def serialize(self):
        stream = samples_pb2.sample_stream()
        stream.timestamp = self.timestamp
        stream.session_id = self.session.sid.bytes
        #TODO: move machine_id to the session
        #stream.machine_id = str(bytearray(self.machine_id))
        stream.channel = self.channel
        stream.sample.extend(self.samples)
        
        return stream.SerializeToString()
        #return text_format.MessageToString(stream)
    
    @staticmethod
    def deserialize(serialized, session):
        stream = samples_pb2.sample_stream()
        stream.ParseFromString(serialized)
        #text_format.Merge(serialized, stream)
        
        assert(stream.session_id == session.sid.bytes)
        
        b = Block(0)
        b.session = session
        b.timestamp = stream.timestamp
        b.channel = stream.channel
        b.samples = stream.sample
        
        return b
        
class BlockPoolError(Exception):
    pass

class BlockPool:
    def __init__(self, machine_id, file_root, pool_size=100):
        self.machine_id = machine_id
        self.pool_size = pool_size
        self.file_root = file_root
        
        self.blocks = []
        self.pool = [Block() for i in range(pool_size)] #@UnusedVariable
        self._next_free = 0
        
        self.stop_write = False
        self.write_queue = Queue(pool_size)
        
        reactor.callInThread(self._process_write_queue)
    
    def get_free(self):
        if self._next_free >= self.pool_size:
            self._next_free = 0
        
        next_block = self.pool[self._next_free]
        
        if not next_block.free:
            if next_block.session.persistent and not next_block.written:
                raise BlockPoolError("Potential data loss - need to overwrite unsaved data")
            self.blocks.remove(next_block.block_id)
            next_block.reset()
        
        self._next_free += 1
        next_block.free = False
        self.blocks.append(next_block.block_id)
        return next_block
    
    def write(self, block):
        self.write_queue.put(block)
    
    def stop_workers(self):
        self.write_queue.join()
        self.stop_write = True
    
    def _process_write_queue(self):
        while not self.stop_write:
            block = self.write_queue.get()
            # print("Block %d in write queue, persist: %r" % (block.block_number, block.persist))
            
            if block.session.persistent:
                # print("Writing block %d, sample %d" % (block.block_number, block.timestamp))
                path = os.path.join(self.file_root, block.session.path())
                if not os.path.isdir(path):
                    os.mkdir(path)
                
                stream_file = open(os.path.join(self.file_root, block.path()), "wb")
                stream_file.write(block.serialize())
                stream_file.close()
                
                block.written = True
            
            self.write_queue.task_done()        

class StorageProtocol(ProtobufProtocol):
    def __init__(self, block_pool):
        self.session = None
        self._current_block = None
        
        self.block_pool = block_pool
    
    def start_session(self, session):
        self.session = session
        self.session.block_pool = self.block_pool
        self._new_block()

    def stop_session(self):
        stream_file = open(os.path.join(self.block_pool.file_root, self.session.path(), "index"), "wb")
        stream_file.write(self.session.serialize())
        stream_file.close()
        
        self.session = Session(UUID(int=0))
        self.persistent_session = False
        self._new_block()

    def _new_block(self):
        if self._current_block:
            self.block_pool.write(self._current_block)
                
        self._current_block = self.block_pool.get_free()
        self._current_block.session = self.session
        self._current_block.timestamp = self.session.sample_count
        
        self.session.blocks.append(self._current_block.block_id)

    def messageReceived(self, message):
        samples = message.sample_stream.sample
        print(samples)
        
        if self.session:
            i = 0
            while i < len(samples):
                if self._current_block.full():
                    self.session.sample_count += len(self._current_block.samples)
                    self._new_block()
                
                self._current_block.samples.append(samples[i])
                i += 1
    
    def connectionLost(self, reason=ConnectionDone):
        pass

class StorageFactory(ReconnectingClientFactory):
    def __init__(self):
        self.protocols = []
        
        path = os.path.join(os.getcwd(), "storage")
        
        # uuid.getnode will usually return the system mac address as a 48 bit int
        # struct.pack for a long long (Q) gives eight bytes, so we slice off the first six
        mac = struct.pack("Q", uuid.getnode())[0:5]
        self.block_pool = BlockPool(machine_id=mac, file_root=path, pool_size=10)
    
    def buildProtocol(self, addr):
        protocol = StorageProtocol(self.block_pool)
        protocol.factory = self
        self.protocols.append(protocol)
        protocol.start_session(Session(UUID(int=0), persistent=False))
        self.resetDelay()
        return protocol
    
    def stopFactory(self):
        self.block_pool.stop_workers()
    
    def start_session(self, sid):
        for p in self.protocols:
            p.start_session(Session(sid, persistent=True))
            
    def stop_session(self):
        for p in self.protocols:
            p.stop_session()
        
        
