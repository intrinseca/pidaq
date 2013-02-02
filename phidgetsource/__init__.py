from Phidgets import PhidgetException
from Phidgets.Devices.InterfaceKit import InterfaceKit
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

class PhidgetSourceProtocol(SampleStreamProtocol):
    implements(interfaces.IPushProducer)
    
    def connectionMade(self):
        SampleStreamProtocol.connectionMade(self)
        
        self._paused = False
        self._samples = Queue(100)
        
        try:
            self._device = InterfaceKit()
        except RuntimeError as e:
            print("Runtime Error: %s" % e.message)
            
        try:
            self._device.openPhidget()
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.detail))
        
        self._device.setOnSensorChangeHandler(self.sensorChanged)
        
        print("Phidget: Waiting for Connection")
        self._device.waitForAttach(10000)
        
        self._device.setSensorChangeTrigger(0, 0)
        self._device.setDataRate(0, 64)
        
        print("Phidget: Connected")
        self.transport.registerProducer(self, True)
        self.resumeProducing()
    
    def connectionLost(self, reason=ConnectionDone):
        self.stopProducing()
    
    def pauseProducing(self):
        self._paused = True
        
    def resumeProducing(self):
        self._paused = False
        
    def stopProducing(self):
        self._paused = True
        self._device.closePhidget()
    
    def sensorChanged(self, e):
        self._samples.put(e.value)
        
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
        

class PhidgetSourceProtocolFactory(Factory):
    def buildProtocol(self, addr):
        return PhidgetSourceProtocol()