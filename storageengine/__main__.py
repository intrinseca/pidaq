from storageengine.storage import StorageFactory
from storageengine.control import ControlFactory
from twisted.internet import reactor


store = StorageFactory()
control = ControlFactory()

control.store = store

reactor.listenTCP(1235, control) #@UndefinedVariable
reactor.connectTCP("localhost", 1234, store) #@UndefinedVariable
reactor.run() #@UndefinedVariable
    