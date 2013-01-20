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
        
        self._sampleLoop = LoopingCall(self.takeSample)
        print("Phidget: Waiting for Connection")
        self._device.waitForAttach(10000)
        print("Phidget: Connected")
        self.transport.registerProducer(self, True)
        self.resumeProducing()
        
    def pauseProducing(self):
        self._paused = True
        self._sampleLoop.stop()
        
    def resumeProducing(self):
        self._paused = False
        self._sampleLoop.start(1)
        
    def stopProducing(self):
        self._paused = True
        self._sampleLoop.stop()
        self._device.closePhidget()
    
    def takeSample(self):
        value = self._device.getSensorValue(0)
        
        self.sendSample(int(time.time()), value)

class PhidgetSourceProtocolFactory(Factory):
    def buildProtocol(self, addr):
        return PhidgetSourceProtocol()     

reactor.listenTCP(1234, PhidgetSourceProtocolFactory())
reactor.run()

#s = samples_pb2.Sample()
#s.timestamp = 10
#s.value = 1024
#
#print(s)
#
#def gotProtocol(p):
#    m = network_pb2.network_message()
#    m.sample.CopyFrom(s)
#    p.sendMessage(m)
#    p.transport.loseConnection()
#
#point = TCP4ClientEndpoint(reactor, "localhost", 1234)
#d = point.connect(ProtobufProtocolFactory())
#reactor.run()
#d.addCallback(gotProtocol)
#d.addErrback(log.err)
#
#print("Done")