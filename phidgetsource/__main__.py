from phidgetsource import PhidgetSourceProtocolFactory
from twisted.internet import reactor

if __name__ == '__main__':
    print("Starting PhidgetSource")
    reactor.listenTCP(1234, PhidgetSourceProtocolFactory())
    reactor.run()