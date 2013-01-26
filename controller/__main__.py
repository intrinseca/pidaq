from twisted.internet import reactor, stdio
from controller import StorageEngineControlFactory, CLI, CLIFactory

control = StorageEngineControlFactory()
cli = CLI(control)

stdio.StandardIO(cli)
reactor.listenTCP(1236, CLIFactory(control))
reactor.connectTCP("localhost", 1235, control)
reactor.run()