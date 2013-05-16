from net import LiveStream
from storageengine.control import ControlFactory
from storageengine.storage import StorageEngine
from twisted.internet import reactor
import sys

store = StorageEngine()
control = ControlFactory()
live_stream = LiveStream()

if sys.argv[1] == 'spi':
    from sources.spi import SPISource
    source = SPISource()
elif sys.argv[1] == 'phidget':
    from sources.phidget import InterfaceSource
    source = InterfaceSource()
elif sys.argv[1] == 'sine':
    from sources.dummy import SineSource
    source = SineSource()
else:
    print("Invalid Source")
    exit()

store.set_source(source)
store.live_stream = live_stream
control.store = store

reactor.listenUDP(0, live_stream)
reactor.listenTCP(1235, control)
reactor.run()
