#from dummysource import DummySourceProtocolFactory
from phidgetsource import PhidgetSourceProtocolFactory
from storageengine.control import ControlFactory
from storageengine.storage import StorageFactory
from twisted.internet import reactor

source = PhidgetSourceProtocolFactory()
store = StorageFactory()
control = ControlFactory()

control.store = store

reactor.listenTCP(1234, source)
reactor.listenTCP(1235, control)
reactor.connectTCP("localhost", 1234, store)
reactor.run()
