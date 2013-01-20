from protobuf import samples_pb2, network_pb2
from twisted.internet import interfaces, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from net import SampleStreamProtocol, SampleStreamProtocolFactory
from twisted.python import log
from zope.interface import implements
from Phidgets.Devices.InterfaceKit import InterfaceKit
from Phidgets import PhidgetException
from twisted.internet.task import LoopingCall
import time
from twisted.internet.protocol import Factory

class PhidgetSourceProtocol(SampleStreamProtocol):
    implements(interfaces.IPushProducer)
    
    def connectionMade(self):
        SampleStreamProtocol.connectionMade(self)
        
        self._paused = False
        
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
        self._device.setDataRate(0, 100)
        
        print("Phidget: Connected")
        self.transport.registerProducer(self, True)
        self.resumeProducing()
        
    def pauseProducing(self):
        self._paused = True
        
    def resumeProducing(self):
        self._paused = False
        
    def stopProducing(self):
        self._paused = True
        self._device.closePhidget()
    
    def sensorChanged(self, e):
        if not self._paused:
            self.sendSample(int(time.time()), e.value)

class PhidgetSourceProtocolFactory(Factory):
    def buildProtocol(self, addr):
        return PhidgetSourceProtocol()