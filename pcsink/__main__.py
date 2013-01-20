from pcsink import *

if __name__ == "__main__":
    reactor.connectTCP("raspberrypi", 1234, SampleLogFactory())
    reactor.run()
    