import wx
from collections import deque
import numpy
import time
from wx.lib.plot import PlotCanvas, PlotGraphics, PolyLine

class ControlWindow(wx.Frame):
    def __init__(self, parent, control):
        self.control = control
        self.line = None
        self.live_buffer = deque(maxlen=5000)
        
        wx.Frame.__init__(self, parent, title="PiDAQ", size=(640, 480))
        
        panel = wx.Panel(self, -1)
        
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.canvas = PlotCanvas(panel)
        self.canvas.SetEnableAntiAliasing(True)
        
        btnStart = wx.Button(panel, label="Start Session")
        btnStop = wx.Button(panel, label="Stop Session")
        self.lblFPS = wx.StaticText(panel, label="000 FPS")
        
        control_sizer.Add(btnStart, flag=wx.ALL, border=3)
        control_sizer.Add(btnStop, flag=wx.ALL, border=3)
        control_sizer.Add(self.lblFPS, flag=wx.ALL, border=3)
        
        top_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 3)
        top_sizer.Add(control_sizer)
        
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_data, self.update_timer)
        self.update_timer.Start(10)
        #self.canvas.Bind(wx.EVT_IDLE, self.update_data)
        
        self.start_time = time.time()
        self.frames = 0
        self.frame_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_fps, self.frame_timer)
        self.frame_timer.Start(1000)
        
        btnStart.Bind(wx.EVT_BUTTON, self.btnStart_Click)
        btnStop.Bind(wx.EVT_BUTTON, self.btnStop_Click)
    
        panel.SetSizer(top_sizer)
    
    def update_fps(self, event=None):
        self.end_time = time.time()
        fps = self.frames / (self.end_time - self.start_time)
        self.frames = 0
        
        self.lblFPS.SetLabel("{:3.0f} FPS".format(fps))
        self.start_time = time.time()
    
    def update_data(self, event=None):
        plot_width = self.canvas.GetSize()[0]
        data_width = self.live_buffer.maxlen
        
        (x1, data) = self.downsample(self.live_buffer, int(data_width / plot_width))
        
        x = numpy.array(x1) - len(self.live_buffer)
        x.shape = (len(x), 1)
        y = numpy.resize(data, (len(x), 1))
        z = numpy.append(x, y, axis=1)
        line = PolyLine(z, colour='blue', width=1.5)
        self.canvas.Draw(PlotGraphics([line]), xAxis=(-self.live_buffer.maxlen, 0), yAxis=(0,4095))
        self.frames += 1
    
    def downsample(self, samples, downsample_factor):
        downsampled = []
        downsample_points = range(0, len(samples), downsample_factor)
        downsample_x = []
        
        for i in downsample_points:
            downsampled.append(samples[i])
            downsample_x.append(i - len(samples))
        
        return (downsample_points, downsampled)
    
    def btnStart_Click(self, event=None):
        self.control.start_session()
    
    def btnStop_Click(self, event=None):
        self.control.stop_session()
