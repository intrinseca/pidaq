from dummysource import *

if __name__ == '__main__':
    print("Starting DummySource")
    reactor.listenTCP(1234, DummySourceProtocolFactory())
    reactor.run()