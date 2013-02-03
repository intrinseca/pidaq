from twisted.internet.task import LoopingCall
import math
from sources import Source

class SineSource(Source):
    def __init__(self):
        Source.__init__(self)
        self._sample_number = 0
        self._timer = LoopingCall(self.sample)
        self._timer.start(0.01)
    
    def sample(self):
        if self.sink is not None:
            self.sink([512 + int(math.sin(self._sample_number * 0.001) * 512)])
        
        self._sample_number += 1
