from Phidgets import PhidgetException
from Phidgets.Devices.InterfaceKit import InterfaceKit
from sources import Source

class InterfaceSource(Source):
    def __init__(self):
        Source.__init__(self)
        
        try:
            self._device = InterfaceKit()
        except RuntimeError as e:
            print("Runtime Error: %s" % e.message)
            
        try:
            self._device.openPhidget()
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.detail))
        
        self._device.setOnSensorChangeHandler(self.sensor_changed)
        
        print("Phidget: Waiting for Connection")
        self._device.waitForAttach(10000)
        
        self._device.setSensorChangeTrigger(0, 0)
        self._device.setDataRate(0, 1)
        
        print("Phidget: Connected")
    
    def sensor_changed(self, e):
        if self.sink is not None:
            self.sink([e.value])
