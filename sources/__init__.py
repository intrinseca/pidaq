from twisted.internet.task import LoopingCall
from spi import spi_transfer, SPIDev
from twisted.internet import reactor

class Source:
    def __init__(self):        
        self.sink = None

class SPISource(Source):
    def __init__(self):
        print("SPI Source")
        Source.__init__(self)
        self._spi = open('/dev/spidev0.0', 'rw+')
        #self._timer = LoopingCall(self.sample)
        #print("Starting Sample Timer")
        #self._timer.start(1)
        reactor.callInThread(self.sample)
        
    def sample(self):
        while True:
            len = ord(self._spi.read(1))
            if len > 0:
                data = map(ord, self._spi.read(len))
                if self.sink is not None:
                    self.sink(data)
                print("%d: %r" % (len, data))
                        
