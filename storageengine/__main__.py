from sources.dummy import SineSource
from sources.phidget import InterfaceSource
from storageengine.control import ControlFactory
from storageengine.storage import StorageEngine
from twisted.internet import reactor

store = StorageEngine()
control = ControlFactory()

store.set_source(SineSource())
control.store = store

reactor.listenTCP(1235, control)
reactor.run()
