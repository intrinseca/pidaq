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
        self.stopping = False
        reactor.callInThread(self.sample)
        
    def sample(self):
        skip = 0
        while not self.stopping:
            length, = self._spi.transfer([], 1)
            if length > 0:
                data = self._spi.transfer([], length)
                print("{:3}->data ({}): {:3} ({:3}) {:3}".format(skip, length, data[0], data[len(data) - 1] - data[0], data[len(data) - 1]))
                if self.sink is not None:
                    self.sink(data)
                    
                skip = 0
                
            skip += 1

    def stop(self):
        self.stopping = True