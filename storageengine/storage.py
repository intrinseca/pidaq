from Queue import Queue
from google.protobuf import text_format
from net import ProtobufProtocol
from protobuf import samples_pb2
from twisted.internet import reactor
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import ReconnectingClientFactory
from uuid import UUID, uuid1
import os
import struct
import uuid

class Session:
    def __init__(self, sid, persistent):
        self.sid = sid
        self.sample_count = 0
        self.machine_id = [0, 0, 0, 0, 0, 0]
        self.block_count = 0
        self.block_pool_size = 0
        self.blocks = []
        self.persistent = persistent
    
    def path(self):
        return str(self.sid)

class Block:
    size = 10
    
    def __init__(self, index):
        self.reset(index)
    
    def full(self):
        return len(self.samples) >= Block.size
    
    def reset(self, index):
        self.block_id = uuid1()
        self.block_number = index
        self.timestamp = 0
        self.channel = 0
        self.written = False
        self.free = True
        self.samples = []
    
    def path(self):
        return os.path.join(self.session.path(), str(self.block_id))
        
class BlockPoolError(Exception):
    pass

class BlockPool:
    def __init__(self, machine_id, file_root, pool_size=100):
        self.machine_id = machine_id
        self.pool_size = pool_size
        self.file_root = file_root
        
        self.pool = [Block(i) for i in range(pool_size)]
        self._next_free = 0
        
        self.stop_write = False
        self.write_queue = Queue(pool_size)
        
        reactor.callInThread(self._process_write_queue)
    
    def get(self):
        if self._next_free >= self.pool_size:
            self._next_free = 0
        
        next_block = self.pool[self._next_free]
        
        if not next_block.free:
            if next_block.session.persistent and not next_block.written:
                raise BlockPoolError("Potential data loss - need to overwrite unsaved data")
            next_block.reset(next_block.block_number + self.pool_size)
        
        self._next_free += 1
        next_block.free = False
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
                
                stream = samples_pb2.sample_stream()
                stream.timestamp = block.timestamp
                stream.session_id = block.session.sid.bytes
                stream.machine_id = str(bytearray(self.machine_id))
                stream.channel = block.channel
                stream.sample.extend(block.samples)
                
                stream_file = open(os.path.join(self.file_root, block.path()), "w")
                stream_file.write(stream.SerializeToString())
                # text_format.PrintMessage(stream, stream_file)
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
        self.session.block_pool_size = self.block_pool.pool_size
        self._new_block()

    def stop_session(self):
        self.session = Session(UUID(int=0))
        self.persistent_session = False
        self._new_block()

    def _new_block(self):
        if self._current_block:
            self.block_pool.write(self._current_block)
                
        self._current_block = self.block_pool.get()
        self._current_block.session = self.session
        self._current_block.timestamp = self.session.sample_count
        
        self.session.blocks.append(self._current_block.block_id)
        self.session.block_count += 1

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
        
        
