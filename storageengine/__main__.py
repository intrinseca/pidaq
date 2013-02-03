from dummysource import DummySourceProtocolFactory, DummySource
from storageengine.control import ControlFactory
from storageengine.storage import StorageEngine
from twisted.internet import reactor

source = DummySourceProtocolFactory()
store = StorageEngine()
control = ControlFactory()

store.set_source(DummySource())
control.store = store

reactor.listenTCP(1234, source)
reactor.listenTCP(1235, control)
reactor.run()
    