from sources import Source
from twisted.internet import reactor
from spipy import SPI

class SPISource(Source):
    def __init__(self):
        print("SPI Source")
        Source.__init__(self)
        self._spi = SPI(0, 0)
        #self._timer = LoopingCall(self.sample)
        #print("Starting Sample Timer")
        #self._timer.start(1)
        reactor.callInThread(self.sample)
        
    def sample(self):
        while True:
            len = ord(self._spi.transfer("", 1))
            if len > 0:
                data = map(ord, self._spi.transfer("", len))
                if self.sink is not None:
                    self.sink(data)
                print("%d: %r" % (len, data))
