from dummysource import DummySourceProtocolFactory
from twisted.internet import reactor

if __name__ == '__main__':
    print("Starting DummySource")
    reactor.listenTCP(1234, DummySourceProtocolFactory())
    reactor.run()