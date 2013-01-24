from twisted.internet.protocol import Factory

class ControlProtocol:
    pass

class ControlFactory(Factory):
    def buildProtocol(self, addr):
        return ControlProtocol()