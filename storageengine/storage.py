from net import ProtobufProtocol
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import ClientFactory
from uuid import UUID

class Block:
    def __init__(self):
        self.reset()
    
    def full(self):
        return len(self.samples) >= 10
    
    def reset(self):
        self.timestamp = 0
        self.written = False
        self.persist = False
        self.free = True
        self.samples = []
        self.session_id = UUID(int=0)
        
class BlockPoolError(Exception):
    pass

class BlockPool:
    def __init__(self, machine_id, pool_size=100):
        self.machine_id = machine_id
        self.pool_size = pool_size
        self.pool = [Block() for i in range(pool_size)]
        self._next_free = 0
    
    def get(self):
        if self._next_free >= self.pool_size:
            self._next_free = 0
        
        next_block = self.pool[self._next_free]
        
        if not next_block.free:
            if next_block.persist and not next_block.written:
                raise BlockPoolError("Potential data loss - need to overwrite unsaved data")
            next_block.reset()
        
        self._next_free += 1
        next_block.free = False
        return next_block

class StorageProtocol(ProtobufProtocol):
    def __init__(self, block_pool):
        self.session_id = UUID(int=0)
        self.persistent_session = True
        self.session = []
        
        self.block_pool = block_pool
        self._current_block = self.block_pool.get()
        self._current_block.persist = self.persistent_session
    
    def start_session(self, session_id):
        self.session_id = session_id
        self.session = []
    
    def messageReceived(self, message):
        samples = message.sample_stream.sample
        print(samples)
        
        i = 0
        while i < len(samples):
            if self._current_block.full():
                self._current_block = self.block_pool.get()
                self._current_block.session_id = self.session_id
                self._current_block.persist = self.persistent_session
            
            self._current_block.samples.append(samples[i])
            i += 1
    
    def connectionLost(self, reason=ConnectionDone):
        pass

class StorageFactory(ClientFactory):
    def __init__(self):
        self.protocols = []
        self.block_pool = BlockPool(machine_id=[0x00] * 6, pool_size=10)
    
    def buildProtocol(self, addr):
        protocol = StorageProtocol(self.block_pool)
        protocol.factory = self
        self.protocols.append(protocol)
        return protocol
        
        