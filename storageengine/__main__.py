from storageengine import *

if __name__ == "__main__":
    reactor.connectTCP("localhost", 1234, SampleLogFactory())
    reactor.run()
    