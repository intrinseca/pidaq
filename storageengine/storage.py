from Queue import Queue, Empty
from google.protobuf import text_format
from net import ProtobufProtocol, machine_id
from protobuf import samples_pb2
from twisted.internet import reactor
from uuid import UUID, uuid1
import math
import os

class BlockPoolError(Exception):
    pass

class StorageError(Exception):
    pass

class Session:
    def __init__(self, sid, persistent=False):
        self.sid = sid
        self.persistent = persistent
        self.running = False
        
        self.sample_count = 0
        self.machine_id = machine_id()
            
        self.blocks = []
        self.block_size = Block.size
        self.block_pool = None
        self._current_block = None
    
    def start(self):
        self.running = True
        self._new_block()

    def stop(self):
        if self.persistent:
            stream_file = open(os.path.join(self.block_pool.file_root, "index-%s" % str(self.sid)), "wb")
            stream_file.write(self.serialize())
            stream_file.close()
        
        self.block_pool.release(self._current_block)
        self.running = False
    
    def _new_block(self):
        if self._current_block:
            self.block_pool.release(self._current_block)
                
        self._current_block = self.block_pool.new_block()
        self._current_block.session_id = self.sid
        self._current_block.machine_id = self.machine_id
        self._current_block.timestamp = self.sample_count
        self._current_block.persist = self.persistent
        
        self.blocks.append(self._current_block.block_id)
    
    def add_samples(self, samples):
        assert(self.running == True)
        
        i = 0
        while i < len(samples):
            if self._current_block.full():
                self.sample_count += len(self._current_block.samples)
                self._new_block()
            
            self._current_block.samples.append(samples[i])
            i += 1
    
    def query(self, start=0, end=None):
        samples = []
        
        start_block = int(math.floor(start / Block.size))
        
        if not end:
            end_block = len(self.blocks) - 1
            blocks = self.blocks[start_block:]
        else:
            end_block = int(math.ceil(end / Block.size))
            blocks = self.blocks[start_block:end_block + 1]
        
        for block_id in blocks:
            block = self.block_pool.get(block_id, mem_only=not self.persistent)
            
            if block is not None:
                samples.extend(block.samples)
        
        return (start_block * Block.size, samples)
    
    def serialize(self):
        session = samples_pb2.session()
        session.session_id = self.sid.bytes
        session.blocks.extend(map(lambda x: x.bytes, self.blocks))
        return session.SerializeToString()
        # return text_format.MessageToString(session)
    
    @staticmethod
    def deserialise(serialized):
        session_pb = samples_pb2.session()
        session_pb.ParseFromString(serialized)
        # text_format.Merge(serialized, session_pb)
        
        session = Session(UUID(bytes=session_pb.session_id), persistent=True)
        session.blocks = map(lambda x: UUID(bytes=x), session_pb.blocks)
        
        return session

class Block:
    size = 100000
    
    def __init__(self):
        self.reset()
        self.new = True
    
    def full(self):
        return len(self.samples) >= Block.size
    
    def reset(self):
        self.block_id = uuid1()
        self.session_id = UUID(int=0)
        self.machine_id = [0, 0, 0, 0, 0, 0]
        self.timestamp = 0
        self.channel = 0
        # TODO: Memory Fail
        self.samples = []
        
        # Block States:
        # Saved/Not Saved - written
        # Needs Saving/Doesn't Need Saving - persist
        # Under Pool Control/Not Under Pool Control - locked
        
        self.written = False
        self.persist = False
        self.locked = False
    
    def serialize(self):
        stream = samples_pb2.sample_stream()
        stream.timestamp = self.timestamp
        stream.session_id = self.session_id.bytes
        stream.machine_id = str(bytearray(self.machine_id))
        stream.channel = self.channel
        stream.samples.extend(self.samples)
        
        return stream.SerializeToString()
        # return text_format.MessageToString(stream)
    
    @staticmethod
    def deserialize(serialized):
        stream = samples_pb2.sample_stream()
        stream.ParseFromString(serialized)
        # text_format.Merge(serialized, stream)
        
        b = Block()
        b.timestamp = stream.timestamp
        b.channel = stream.channel
        b.samples = stream.samples
        
        return b

class BlockPool:
    def __init__(self, file_root, pool_size=100):
        self.pool_size = pool_size
        self.file_root = file_root
        
        if not os.path.isdir(self.file_root):
            os.mkdir(self.file_root)
        
        self.blocks = []
        self.pool = [Block() for i in range(pool_size)]  # @UnusedVariable
        self._next_block = 0
        
        self.stop_write = False
        self.write_queue = Queue(pool_size)
        
        reactor.callInThread(self._process_write_queue)
    
    def get(self, block_id, mem_only=True):
        if block_id in self.blocks:
            block, = (b for b in self.pool if b.block_id == block_id)
        elif not mem_only:
            try:
                block_file = open(os.path.join(self.file_root, str(block_id)), "rb")
                block = Block.deserialize(block_file.read())
            except IOError:
                raise BlockPoolError("Block not Found in Store")
        else:
            return None
        
        block.locked = True
        
        return block
    
    def new_block(self):
        if self._next_block >= self.pool_size:
            self._next_block = 0
        
        block = self.pool[self._next_block]
        
        if block.persist and not block.written:
            raise BlockPoolError("Potential data loss - need to overwrite unsaved data")
        
        if block.new:
            block.new = False
        else:
            self.blocks.remove(block.block_id)
            block.reset()
        
        self._next_block += 1
        block.locked = True
        self.blocks.append(block.block_id)
        return block
    
    def release(self, block):
        if block.persist:
            self.write_queue.put(block)
        
        block.locked = False
    
    def stop_workers(self):
        self.write_queue.join()
        self.stop_write = True
    
    def _process_write_queue(self):
        while not self.stop_write:
            try:
                block = self.write_queue.get(timeout=0.5)
            except Empty:
                pass
            else:            
                stream_file = open(os.path.join(self.file_root, str(block.block_id)), "wb")
                stream_file.write(block.serialize())
                stream_file.close()
                
                block.written = True
                
                self.write_queue.task_done()

class StorageEngine():
    def __init__(self):
        path = os.path.join(os.getcwd(), "storage")
        self.block_pool = BlockPool(file_root=path, pool_size=10)
        self.session = None
        self.store = None
        self.live_stream = None
        self._make_live_session()
    
    def start_session(self, sid, persistent=True):
        self.session = Session(sid, persistent=persistent)
        self.session.block_pool = self.block_pool
        self.session.start()
            
    def stop_session(self):
        self.session.stop()
        self._make_live_session()
    
    def _make_live_session(self):
        self.start_session(UUID(int=0), persistent=False)
    
    def add_samples(self, samples):
        if self.session is not None and self.session.running:
            self.live_stream.send_samples(samples)
            
            self.session.add_samples(samples)
    
    def set_source(self, store):
        self.store = store
        self.store.sink = self.add_samples
    
    def shutdown(self):
        self.store.stop()
        self.block_pool.stop_workers()
