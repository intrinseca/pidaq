import matplotlib
matplotlib.use('WXAgg')
import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure

class ControlWindow(wx.Frame):
    def __init__(self, parent, control):
        self.control = control        
        
        wx.Frame.__init__(self, parent, title="PiDAQ", size=(640, 480))
        
        panel = wx.Panel(self, -1)
        
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.figure = Figure(None, None)
        self.canvas = FigureCanvasWxAgg(panel, -1, self.figure)
        
        btnStart = wx.Button(panel, label="Start")
        btnStop = wx.Button(panel, label="Stop")
        btnShow = wx.Button(panel, label="Show")
        
        control_sizer.Add(btnStart, flag=wx.ALL, border=3)
        control_sizer.Add(btnStop, flag=wx.ALL, border=3)
        control_sizer.Add(btnShow, flag=wx.ALL, border=3)
        
        top_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 3)
        top_sizer.Add(control_sizer)
        
        btnStart.Bind(wx.EVT_BUTTON, self.btnStart_Click)
        btnStop.Bind(wx.EVT_BUTTON, self.btnStop_Click)
        btnShow.Bind(wx.EVT_BUTTON, self.btnShow_Click)
    
        panel.SetSizer(top_sizer)
    
    def message_handler(self, message):
        plot = self.figure.add_subplot(111)
        plot.clear()
        plot.plot(message.sample_stream.samples)
        self.canvas.draw()
    
    def btnStart_Click(self, event=None):
        self.control.start_session()
    
    def btnStop_Click(self, event=None):
        self.control.stop_session()
    
    def btnShow_Click(self, event=None):
        self.control.get_data()
