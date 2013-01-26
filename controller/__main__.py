from twisted.internet import reactor, stdio
from controller import StorageEngineControlFactory, CLI

control = StorageEngineControlFactory()
cli = CLI()
cli.control = control

stdio.StandardIO(cli)
reactor.connectTCP("localhost", 1235, control)
reactor.run()