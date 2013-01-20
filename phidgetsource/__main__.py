from phidgetsource import *

if __name__ == '__main__':
    print("Starting PhidgetSource")
    reactor.listenTCP(1234, PhidgetSourceProtocolFactory())
    reactor.run()