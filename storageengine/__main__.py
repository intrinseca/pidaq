from sources import SPISource
from sources.dummy import SineSource
from sources.phidget import InterfaceSource
from storageengine.control import ControlFactory
from storageengine.storage import StorageEngine
from twisted.internet import reactor
from net import LiveStream

store = StorageEngine()
control = ControlFactory()
live_stream = LiveStream()

store.set_source(SPISource())
store.live_stream = live_stream
control.store = store

reactor.listenUDP(0, live_stream)
reactor.listenTCP(1235, control)
reactor.run()
    
