import matplotlib
matplotlib.use('WXAgg')
import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure

class PlotPanel (wx.Panel):
    """The PlotPanel has a Figure and a Canvas. OnSize events simply set a 
    flag, and the actual resizing of the figure is triggered by an Idle event."""
    def __init__( self, parent, color=None, dpi=None, **kwargs ):
        # initialize Panel
        if 'id' not in kwargs.keys():
            kwargs['id'] = wx.ID_ANY
        if 'style' not in kwargs.keys():
            kwargs['style'] = wx.NO_FULL_REPAINT_ON_RESIZE
        wx.Panel.__init__( self, parent, **kwargs )

        # initialize matplotlib stuff
        self.figure = Figure( None, dpi )
        self.canvas = FigureCanvasWxAgg( self, -1, self.figure )
        self.SetColor( color )

        self._SetSize()
        self.draw()

        self._resizeflag = False

        self.Bind(wx.EVT_IDLE, self._onIdle)
        self.Bind(wx.EVT_SIZE, self._onSize)

    def SetColor( self, rgbtuple=None ):
        """Set figure and canvas colours to be the same."""
        if rgbtuple is None:
            rgbtuple = wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ).Get()
        clr = [c/255. for c in rgbtuple]
        self.figure.set_facecolor( clr )
        self.figure.set_edgecolor( clr )
        self.canvas.SetBackgroundColour( wx.Colour( *rgbtuple ) )

    def _onSize( self, event ):
        self._resizeflag = True

    def _onIdle( self, evt ):
        if self._resizeflag:
            self._resizeflag = False
            self._SetSize()

    def _SetSize( self ):
        pixels = tuple( self.parent.GetClientSize() )
        self.SetSize( pixels )
        self.canvas.SetSize( pixels )
        self.figure.set_size_inches( float( pixels[0] )/self.figure.get_dpi(),
                                     float( pixels[1] )/self.figure.get_dpi() )

    def draw(self): pass # abstract, to be overridden by child classes


class DemoPlotPanel (PlotPanel):
    """Plots several lines in distinct colors."""
    def __init__( self, parent, point_lists, clr_list, **kwargs ):
        self.parent = parent
        self.point_lists = point_lists
        self.clr_list = clr_list

        # initiate plotter
        PlotPanel.__init__( self, parent, **kwargs )
        self.SetColor( (255,255,255) )

    def draw( self ):
        """Draw data."""
        if not hasattr( self, 'subplot' ):
            self.subplot = self.figure.add_subplot( 111 )

        for i, pt_list in enumerate( self.point_lists ):
            plot_pts = num.array( pt_list )
            clr = [float( c )/255. for c in self.clr_list[i]]
            self.subplot.plot( plot_pts[:,0], plot_pts[:,1], color=clr )

class ControlWindow(wx.Frame):
    def __init__(self, parent, control):
        self.control = control        
        
        wx.Frame.__init__(self, parent, title="PiDAQ", size=(640, 480))
        
        panel = wx.Panel(self, -1)
        
        top_sizer = wx.BoxSizer(wx.VERTICAL)
        control_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.txtData = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        btnStart = wx.Button(panel, label="Start")
        btnStop = wx.Button(panel, label="Stop")
        btnShow = wx.Button(panel, label="Show")
        
        control_sizer.Add(btnStart, flag=wx.ALL, border=3)
        control_sizer.Add(btnStop, flag=wx.ALL, border=3)
        control_sizer.Add(btnShow, flag=wx.ALL, border=3)
        
        top_sizer.Add(self.txtData, 1, wx.EXPAND | wx.ALL, 3)        
        top_sizer.Add(control_sizer)
        
        btnStart.Bind(wx.EVT_BUTTON, self.btnStart_Click)
        btnStop.Bind(wx.EVT_BUTTON, self.btnStop_Click)
        btnShow.Bind(wx.EVT_BUTTON, self.btnShow_Click)
    
        panel.SetSizer(top_sizer)
    
    def message_handler(self, message):
        self.txtData.SetValue(str(message))
    
    def btnStart_Click(self, event=None):
        self.control.start_session()
    
    def btnStop_Click(self, event=None):
        self.control.stop_session()
    
    def btnShow_Click(self, event=None):
        self.control.get_data()
