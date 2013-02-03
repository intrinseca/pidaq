from dummysource import DummySourceProtocolFactory
from storageengine.control import ControlFactory
from storageengine.storage import StorageFactory
from twisted.internet import reactor

#source = DummySourceProtocolFactory()
store = StorageFactory()
control = ControlFactory()

control.store = store

#reactor.listenTCP(1234, source)
reactor.listenTCP(1235, control)
reactor.connectTCP("raspberrypi", 1234, store)
reactor.run()
    