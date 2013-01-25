from storageengine.storage import StorageFactory
from storageengine.control import ControlFactory
from twisted.internet import reactor


store = StorageFactory()
control = ControlFactory()

control.store = store

reactor.listenTCP(1235, control)
reactor.connectTCP("localhost", 1234, store)
reactor.run()
    