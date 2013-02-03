import matplotlib
matplotlib.use('WXAgg')
import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure
from collections import deque

class ControlWindow(wx.Frame):
    def __init__(self, parent, control):
        self.control = control
        self.line = None
        self.live_buffer = deque(maxlen=5000)
        
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
        
        self.canvas.Bind(wx.EVT_IDLE, self.update_data)
        btnStart.Bind(wx.EVT_BUTTON, self.btnStart_Click)
        btnStop.Bind(wx.EVT_BUTTON, self.btnStop_Click)
        btnShow.Bind(wx.EVT_BUTTON, self.btnShow_Click)
    
        panel.SetSizer(top_sizer)
    
    def update_data(self, event=None):
        self.show_samples(self.live_buffer, self.live_buffer.maxlen)
    
    def show_samples(self, samples, width):
        if self.line is None or len(samples) < width:        
            plot = self.figure.add_subplot(111)
            plot.clear()
            plot.set_xlim(-width, 0)
            plot.set_ylim(0, 1024)
            plot.yaxis.tick_right()
            plot.set_yticks(range(0,1025,256))
            line, = plot.plot(range(-len(samples), 0), samples)
            
            if len(samples) == width:
                self.line = line
            else:
                self.line = None    
        else:
            self.line.set_ydata(samples)

        self.canvas.draw()
    
    def btnStart_Click(self, event=None):
        self.control.start_session()
    
    def btnStop_Click(self, event=None):
        self.control.stop_session()
    
    def btnShow_Click(self, event=None):
        self.control.get_data()
