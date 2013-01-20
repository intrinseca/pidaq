from phidgetsource import *

if __name__ == '__main__':
    reactor.listenTCP(1234, PhidgetSourceProtocolFactory())
    reactor.run()