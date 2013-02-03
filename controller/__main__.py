from twisted.internet import wxreactor
wxreactor.install()

from controller import StorageEngineControlFactory, CLI, CLIFactory
from controller.gui import ControlWindow
from twisted.internet import reactor, stdio
import wx



control = StorageEngineControlFactory()
#cli = CLI(control)
#
#stdio.StandardIO(cli)
#reactor.listenTCP(1236, CLIFactory(control))
reactor.connectTCP("localhost", 1235, control)

app = wx.App(False)  # Create a new app, don't redirect stdout/stderr to a window.

frame = ControlWindow(None, control)
control.add_ui(frame)
frame.Show(True)
reactor.registerWxApp(app)

reactor.run()