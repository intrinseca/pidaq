from twisted.internet import wxreactor
wxreactor.install()

from net import LiveStream
from controller import StorageEngineControlFactory, CLI, CLIFactory
from controller.gui import ControlWindow
from twisted.internet import reactor, stdio
import wx

control = StorageEngineControlFactory()
live_stream = LiveStream()
#cli = CLI(control)
#
#stdio.StandardIO(cli)
#reactor.listenTCP(1236, CLIFactory(control))

reactor.listenUDP(1234, live_stream)
reactor.connectTCP("raspberrypi", 1235, control)

app = wx.App(False)
frame = ControlWindow(None, control)
control.add_ui(frame)
frame.Show(True)
reactor.registerWxApp(app)

live_stream.target = frame.live_buffer

reactor.run()