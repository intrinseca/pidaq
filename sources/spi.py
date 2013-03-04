from sources import Source
from twisted.internet import reactor
from pidaqif import PiDAQ

class SPISource(Source):
    def __init__(self):
        print("SPI Source")
        Source.__init__(self)
        self._pidaq = PiDAQ(0, 0)
        #self._timer = LoopingCall(self.sample)
        #print("Starting Sample Timer")
        #self._timer.start(1)
        self.stopping = False
        reactor.callInThread(self.sample)
        
    def sample(self):
        while not self.stopping:
            data = self._pidaq.get_samples()
            print("data ({}): {:3} ({:3}) {:3}".format(len(data), data[0], data[len(data) - 1] - data[0], data[len(data) - 1]))
            if self.sink is not None:
                self.sink(data)

    def stop(self):
        self.stopping = True