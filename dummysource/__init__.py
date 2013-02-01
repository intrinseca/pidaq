from Queue import Queue, Empty
from net import SampleStreamProtocol, SampleStreamProtocolFactory
from protobuf import samples_pb2, network_pb2
from twisted.internet import interfaces, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Factory
from twisted.internet.task import LoopingCall
from twisted.python import log
from zope.interface import implements
import time
import math

class DummySourceProtocol(SampleStreamProtocol):
    implements(interfaces.IPushProducer)
    
    def connectionMade(self):
        SampleStreamProtocol.connectionMade(self)
        
        self._paused = False
        self._samples = Queue(100)
        self._sampleNumber = 0
        
        self._timer = LoopingCall(self.takeSample)
        
        print("DummySource: Connected")
        self.transport.registerProducer(self, True)
        self.resumeProducing()
    
    def connectionLost(self, reason=ConnectionDone):
        self.stopProducing()
        print("DummySource: Disconnected")
    
    def pauseProducing(self):
        self._timer.stop()
        self._paused = True
        
    def resumeProducing(self):
        self._paused = False
        self._timer.start(0.128)
        
    def stopProducing(self):
        self._paused = True
        if self._timer.running:
            self._timer.stop()
    
    def takeSample(self):
        self._sampleNumber += 1
        
        self._samples.put(int(512 + math.sin(self._sampleNumber * 0.1) * 512))
        
        if not self._paused and self._samples.qsize() >= 10:
            reactor.callFromThread(self.sendSamples)
    
    def sendSamples(self):
        if not self._paused:
            message = network_pb2.network_message()
            message.sample_stream.channel = 0
            message.sample_stream.rate = 128
                        
            while not self._paused:
                try:
                    sample = self._samples.get_nowait()
                    message.sample_stream.samples.append(sample)
                except Empty:
                    break
            
            self.sendMessage(message)
        

class DummySourceProtocolFactory(Factory):
    def buildProtocol(self, addr):
        return DummySourceProtocol()