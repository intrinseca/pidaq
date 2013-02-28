import matplotlib
import time
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
        self.lblFPS = wx.StaticText(panel, label="000 FPS")
        
        control_sizer.Add(btnStart, flag=wx.ALL, border=3)
        control_sizer.Add(btnStop, flag=wx.ALL, border=3)
        control_sizer.Add(btnShow, flag=wx.ALL, border=3)
        control_sizer.Add(self.lblFPS, flag=wx.ALL, border=3)
        
        top_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 3)
        top_sizer.Add(control_sizer)
        
        self.update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_data, self.update_timer)
        self.update_timer.Start(20)
        
        self.start_time = time.time()
        self.frames = 0
        self.frame_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.update_fps, self.frame_timer)
        self.frame_timer.Start(1000)
        
        #self.canvas.Bind(wx.EVT_IDLE, self.update_data)
        btnStart.Bind(wx.EVT_BUTTON, self.btnStart_Click)
        btnStop.Bind(wx.EVT_BUTTON, self.btnStop_Click)
        btnShow.Bind(wx.EVT_BUTTON, self.btnShow_Click)
    
        panel.SetSizer(top_sizer)
    
    def update_fps(self, event=None):
        self.end_time = time.time()
        fps = self.frames / (self.end_time - self.start_time)
        self.frames = 0
        
        self.lblFPS.SetLabel("{:3.0f} FPS".format(fps))
        self.start_time = time.time()
    
    def update_data(self, event=None):
        self.show_samples(self.live_buffer, self.live_buffer.maxlen)
    
    def show_samples(self, samples, width):
        plot_width = self.canvas.GetSize()[0]
        
        downsample_factor = int(width / plot_width) * 2
        
        downsampled = []
        downsample_points = range(0, len(samples), downsample_factor)
        downsample_x = []
        
        for i in downsample_points:
            downsampled.append(samples[i])
            downsample_x.append(i - len(samples))
        
        if self.line is None or len(samples) < width:        
            plot = self.figure.add_subplot(111)
            plot.clear()
            plot.set_xlim(-width, 0)
            plot.set_ylim(0, 1024)
            plot.yaxis.tick_right()
            plot.set_yticks(range(0,1025,256))
            line, = plot.plot(downsample_x, downsampled)
            
            if len(samples) == width:
                self.line = line
            else:
                self.line = None    
        else:
            self.line.set_ydata(downsampled)

        self.frames += 1
        self.canvas.draw()
    
    def btnStart_Click(self, event=None):
        self.control.start_session()
    
    def btnStop_Click(self, event=None):
        self.control.stop_session()
    
    def btnShow_Click(self, event=None):
        self.control.get_data()
