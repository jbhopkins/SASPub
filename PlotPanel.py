'''
Created on Sept 28, 2019

@author: Jesse Hopkins

#******************************************************************************
# This file is part of SASPub.
#
#    SASPub is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    SASPub is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with SASPub.  If not, see <http://www.gnu.org/licenses/>.
#
#******************************************************************************

This file contains basic functions for processing on one more or scattering profile,
including averaging, subtracting, and merging.
'''

if __name__ == "__main__" and __package__ is None:
    __package__ = "SASPub"

from itertools import cycle
import copy

import numpy as np
import wx
import wx.lib.agw.ultimatelistctrl as ULC
import wx.aui as aui
import wx.lib.scrolledpanel as scrolled
import matplotlib as mpl
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg
from matplotlib.figure import Figure
import matplotlib.colors as mplcol

mpl.rcParams['backend'] = 'WxAgg'
# mpl.rcParams['font.family'] = ['fantasy']
# mpl.rcParams['font.fantasy'] = ['xkcd']

import Data


class PlotPanel(wx.Panel):

    def __init__(self, *args, **kwargs):

        wx.Panel.__init__(self, *args, **kwargs)

        self._initialize()
        self._create_layout()

        self.Layout()

    def _initialize(self):
        self.plots = []
        self.profile_plotted = False
        self.ift_plotted = False
        self.series_plotted = False

        self.plot_titles = {'loglin'    : 'Log-Lin',
            'loglog'        : 'Log-Log',
            'dimkratky'     : 'Dim. Kratky',
            'guinier'       : 'Guinier',
            }

        self.plot_ctrls = {}
        self.translation = {
            'tick_position_x'   : {'inside' : 'in',
                'cross' : 'inout',
                'outside' : 'out'},
            'tick_position_y'   : {'inside' : 'in',
                'cross' : 'inout',
                'outside' : 'out'},
        }

        self.reverse_translation = {}

        for key in self.translation:
            self.reverse_translation[key] = {value2 : key2 for (key2, value2) in self.translation[key].items()}

        self.fonts = mpl.rcParams['font.cursive']+ mpl.rcParams['font.fantasy'] \
            + mpl.rcParams['font.monospace'] + mpl.rcParams['font.sans-serif'] \
            + mpl.rcParams['font.serif']

        try:
            self.fonts.remove('cursive')
            self.fonts.remove('fantasy')
            self.fonts.remove('monospace')
            self.fonts.remove('serif')
            self.fonts.remove('sans-serif')
        except Exception:
            pass

        print (mpl.rcParams['font.family'])

        self.fonts.sort(key=str.lower)

    def _create_layout(self):

        ctrl_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, "Plot Controls")
        static_box = ctrl_sizer.GetStaticBox()

        self.control_notebook = wx.Notebook(static_box)
        self.control_notebook.AddPage(self._create_axes_tick_ctrl(self.control_notebook), 'Axes', select=True)

        ctrl_sizer.Add(self.control_notebook, border=5, flag=wx.ALL|wx.EXPAND, proportion=1)

        self.plot_notebook = aui.AuiNotebook(self, style = aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_SCROLL_BUTTONS)

        self.plot_notebook.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self._on_plot_change)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(ctrl_sizer, border=5, flag=wx.ALL|wx.EXPAND, proportion=1)
        top_sizer.Add(self.plot_notebook, border=5, flag=wx.ALL|wx.EXPAND, proportion=2)

        self.SetSizer(top_sizer)

        self.plot_ctrl_lookup = {value[0] : key for (key, value) in self.plot_ctrls.items()}

    def _create_axes_tick_ctrl(self, parent):

        top_panel = scrolled.ScrolledPanel(parent)
        top_panel.SetVirtualSize((200, 200))
        top_panel.SetScrollRate(20, 20)

        left_axis = wx.CheckBox(top_panel, label='Left')
        right_axis = wx.CheckBox(top_panel, label='Right')
        bottom_axis = wx.CheckBox(top_panel, label='Bottom')
        top_axis = wx.CheckBox(top_panel, label='Top')

        left_axis.Bind(wx.EVT_CHECKBOX, self._on_plot_update)
        right_axis.Bind(wx.EVT_CHECKBOX, self._on_plot_update)
        bottom_axis.Bind(wx.EVT_CHECKBOX, self._on_plot_update)
        top_axis.Bind(wx.EVT_CHECKBOX, self._on_plot_update)

        axes_sizer = wx.FlexGridSizer(rows=2, cols=2, vgap=2, hgap=2)
        axes_sizer.Add(left_axis)
        axes_sizer.Add(right_axis)
        axes_sizer.Add(bottom_axis)
        axes_sizer.Add(top_axis)

        tick_position_x = wx.Choice(top_panel, choices=['Inside', 'Cross', 'Outside'])
        tick_position_y = wx.Choice(top_panel, choices=['Inside', 'Cross', 'Outside'])

        tick_position_x.Bind(wx.EVT_CHOICE, self._on_plot_update)
        tick_position_y.Bind(wx.EVT_CHOICE, self._on_plot_update)

        major_x_axis = wx.CheckBox(top_panel, label='X')
        major_y_axis = wx.CheckBox(top_panel, label='Y')

        major_x_axis.Bind(wx.EVT_CHECKBOX, self._on_plot_update)
        major_y_axis.Bind(wx.EVT_CHECKBOX, self._on_plot_update)

        major_sizer = wx.FlexGridSizer(rows=1, cols=2, vgap=2, hgap=2)
        major_sizer.Add(major_x_axis)
        major_sizer.Add(major_y_axis)

        minor_x_axis = wx.CheckBox(top_panel, label='X')
        minor_y_axis = wx.CheckBox(top_panel, label='Y')

        minor_x_axis.Bind(wx.EVT_CHECKBOX, self._on_plot_update)
        minor_y_axis.Bind(wx.EVT_CHECKBOX, self._on_plot_update)

        minor_sizer = wx.FlexGridSizer(rows=1, cols=2, vgap=2, hgap=2)
        minor_sizer.Add(minor_x_axis)
        minor_sizer.Add(minor_y_axis)

        left_label = wx.CheckBox(top_panel, label='Left')
        right_label = wx.CheckBox(top_panel, label='Right')
        bottom_label = wx.CheckBox(top_panel, label='Bottom')
        top_label = wx.CheckBox(top_panel, label='Top')

        left_label.Bind(wx.EVT_CHECKBOX, self._on_plot_update)
        right_label.Bind(wx.EVT_CHECKBOX, self._on_plot_update)
        bottom_label.Bind(wx.EVT_CHECKBOX, self._on_plot_update)
        top_label.Bind(wx.EVT_CHECKBOX, self._on_plot_update)

        label_sizer = wx.FlexGridSizer(rows=2, cols=2, vgap=2, hgap=2)
        label_sizer.Add(left_label)
        label_sizer.Add(right_label)
        label_sizer.Add(bottom_label)
        label_sizer.Add(top_label)

        top_sizer = wx.FlexGridSizer(cols=2, vgap=2, hgap=2)
        top_sizer.Add(wx.StaticText(top_panel, label='Axes'))
        top_sizer.Add(axes_sizer)
        top_sizer.Add(wx.StaticText(top_panel, label='X Tick Position'))
        top_sizer.Add(tick_position_x)
        top_sizer.Add(wx.StaticText(top_panel, label='Y Tick Position'))
        top_sizer.Add(tick_position_y)
        top_sizer.Add(wx.StaticText(top_panel, label='Major Ticks'))
        top_sizer.Add(major_sizer)
        top_sizer.Add(wx.StaticText(top_panel, label='Minor Ticks'))
        top_sizer.Add(minor_sizer)
        top_sizer.Add(wx.StaticText(top_panel, label='Labels'))
        top_sizer.Add(label_sizer)

        self.plot_ctrls['axis_left_on'] = (left_axis, left_axis.GetValue, left_axis.SetValue, 'bool')
        self.plot_ctrls['axis_right_on'] = (right_axis, right_axis.GetValue, right_axis.SetValue, 'bool')
        self.plot_ctrls['axis_top_on'] = (top_axis, top_axis.GetValue, top_axis.SetValue, 'bool')
        self.plot_ctrls['axis_bottom_on'] = (bottom_axis, bottom_axis.GetValue, bottom_axis.SetValue, 'bool')
        self.plot_ctrls['tick_position_x'] = (tick_position_x, tick_position_x.GetStringSelection, 
            tick_position_x.SetStringSelection, 'str')
        self.plot_ctrls['tick_position_y'] = (tick_position_y, tick_position_y.GetStringSelection, 
            tick_position_y.SetStringSelection, 'str')
        self.plot_ctrls['major_ticks_x'] = (major_x_axis, major_x_axis.GetValue, major_x_axis.SetValue, 'bool')
        self.plot_ctrls['major_ticks_y'] = (major_y_axis, major_y_axis.GetValue, major_y_axis.SetValue, 'bool')
        self.plot_ctrls['minor_ticks_x'] = (minor_x_axis, minor_x_axis.GetValue, minor_x_axis.SetValue, 'bool')
        self.plot_ctrls['minor_ticks_y'] = (minor_y_axis, minor_y_axis.GetValue, minor_y_axis.SetValue, 'bool')
        self.plot_ctrls['label_left'] = (left_label, left_label.GetValue, left_label.SetValue, 'bool')
        self.plot_ctrls['label_right'] = (right_label, right_label.GetValue, right_label.SetValue, 'bool')
        self.plot_ctrls['label_top'] = (top_label, top_label.GetValue, top_label.SetValue, 'bool')
        self.plot_ctrls['label_bottom'] = (bottom_label, bottom_label.GetValue, bottom_label.SetValue, 'bool')

        # Be good to be able to set tick font and font size
        # Be good to be able to set tick label offset from axis
        # Custom tick labels?

        top_panel.SetSizer(top_sizer)

        return top_panel

    def load_data(self, data):
        self._on_load(data)
        self.Refresh()

    def _on_load(self, data):
        self.make_profile_plots = False
        self.make_ift_plots = False
        self.make_series_plots = False
        
        for item in data:
            if isinstance(item, Data.ProfileData):
                self.make_profile_plots = True
            elif isinstance(item, Data.SeriesData):
                self.make_series_plots = True
            elif isinstance(item, Data.IFTData):
                self.make_series_plots = True

        if self.make_profile_plots and not self.profile_plotted:
            self._add_plot('loglin')
            self._add_plot('dimkratky')
            self._add_plot('guinier')

            self.profile_plotted = True

        elif self.make_ift_plots and not self.ift_plotted:
            pass

        elif self.make_series_plots and not self.series_plotted:
            pass

        profile_plots = []
        ift_plots = []
        series_plots = []
        
        for i in range(self.plot_notebook.GetPageCount()):
            plot = self.plot_notebook.GetPage(i)

            if plot.is_profile_plot:
                profile_plots.append(plot)
            elif plot.is_ift_plot:
                ift_plots.append(plot)
            elif plot_is_series_plot:
                series_plots.append(plot)

        for item in data:
            if isinstance(item, Data.ProfileData):
                for plot in profile_plots:
                    plot.plot_data(item)

            elif isinstance(item, Data.IFTData):
                for plot in ift_plots:
                    plot.plot_data(item)

            elif isinstance(item, Data.SeriesData):
                for plot in series_plots:
                    plot.plot_data(item)

    def _on_remove(self, data):
        pass

    def _add_plot(self, plot_type):

        plot_tab = PlotTab(self.plot_notebook, plot_type)

        num_plots = self.plots.count(plot_type)

        if num_plots > 0:
            name = self.plot_titles[plot_type] + ' {}'.format(num_plots+1)
        else:
            name = self.plot_titles[plot_type]

        self.plot_notebook.AddPage(plot_tab, name)

        self.plots.append(plot_type)

        if self.plot_notebook.GetPageCount():
            self._update_settings_from_plot()

    def _on_plot_update(self, evt):

        ctrl = evt.GetEventObject()

        item_key = self.plot_ctrl_lookup[ctrl]

        value = self.plot_ctrls[item_key][1]()

        if self.plot_ctrls[item_key][3] == 'int':
            value = int(value)
        elif self.plot_ctrls[item_key][3] == 'float':
            value = float(value)

        if item_key in self.translation:
            value = self.translation[item_key][value.lower()]

        update_dict = {item_key :  value}

        current_plot_tab = self.plot_notebook.GetCurrentPage()

        if current_plot_tab is not None:
            current_plot_tab.change_plot_settings(update_dict)

        pass

    def _update_settings_from_plot(self):

        current_plot_tab = self.plot_notebook.GetCurrentPage()

        if current_plot_tab is not None:
            for key, value in current_plot_tab.plot_settings.items():

                if key in self.plot_ctrls:
                    item_vals = self.plot_ctrls[key]

                    if key in self.reverse_translation:
                        value = self.reverse_translation[key][value]

                    if item_vals[3] == 'bool':
                        item_vals[2](value)
                    else:
                        item_vals[2](str(value))

    def _on_plot_change(self, evt):
        self._update_settings_from_plot()


class PlotTab(wx.Panel):

    def __init__(self, parent, plot_type, *args, **kwargs):

        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.plot_type = plot_type

        self._create_layout()
        self._initialize()
        

    def _create_layout(self):
        self.fig = Figure((5,4), 75)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)

        self.SetSizer(sizer)

        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def _initialize(self):

        self.subplot1 = None
        self.subplot2 = None

        if self.plot_type == 'loglin' or self.plot_type == 'loglog':
            self.subplot1 = self.fig.add_subplot(1, 1, 1)
            self.subplot1.set_xlabel('$q$ ($\AA^{-1}$)')
            self.subplot1.set_ylabel('$I(q)$')

            self.subplot1.set_yscale('log')

            if self.plot_type == 'loglog':
                self.subplot1.set_xscale('log')

        elif self.plot_type == 'dimkratky':
            self.subplot1 = self.fig.add_subplot(1, 1, 1)
            self.subplot1.set_xlabel('$qR_g$')
            self.subplot1.set_ylabel('$(qR_g)^2I(q)/I(0)$')

        elif self.plot_type == 'guinier':
            self.subplot1 = self.fig.add_subplot(2, 1, 1)
            self.subplot1.set_ylabel('$I(q)$')
            self.subplot1.set_yscale('log')

            self.subplot2 = self.fig.add_subplot(212, sharex=self.subplot1)
            self.subplot2.set_xlabel('$q^2$ ($\AA^{-2}$)')
            self.subplot2.set_ylabel('$\Delta \ln (I(q))/\sigma (q)$')

        elif self.plot_type == 'ift':
            pass

        elif self.plot_type == 'series':
            pass

        if (self.plot_type == 'loglin' or self.plot_type == 'loglog' or self.plot_type == 'dimkratky'
            or self.plot_type == 'guinier'):
            self.is_profile_plot = True
        else:
            self.is_profile_plot = False

        if self.plot_type == 'ift':
            self.is_ift_plot = True
        else:
            self.is_ift_plot = False

        if self.plot_type == 'series':
            self.is_series_plot = True
        else:
            self.is_series_plot = False


        self.plot_settings = {
            'norm_residuals'    : True,
            'auto_limits'       : True,

            'tick_position_x'   : 'in',
            'major_ticks_x'     : True,
            'minor_ticks_x'     : False,
            'tick_position_y'   : 'in',
            'major_ticks_y'     : True,
            'minor_ticks_y'     : True,
            'tick_position_x2'  : 'in',
            'major_ticks_x2'    : True,
            'minor_ticks_x2'    : False,
            'tick_position_y2'  : 'in',
            'major_ticks_y2'    : True,
            'minor_ticks_y2'    : True,
            'label_top'         : False,
            'label_bottom'      : True,
            'label_right'       : False,
            'label_left'        : True,
            'label_top2'        : False,
            'label_bottom2'     : True,
            'label_right2'      : False,
            'label_left2'       : True,
            'tick_x_font'       : 'Humor Sans',
            'tick_y_font'       : 'Humor Sans',
            'tick_x_size'       : 20,
            'tick_y_size'       : 20,
            'tick_x2_font'      : 'Humor Sans',
            'tick_y2_font'      : 'Humor Sans',
            'tick_x2_size'      : 20,
            'tick_y2_size'      : 20,

            'axis_left_on'      : True,
            'axis_right_on'     : True,
            'axis_top_on'       : True,
            'axis_bottom_on'    : True,
            'axis_left_on2'     : True,
            'axis_right_on2'    : True,
            'axis_top_on2'      : True,
            'axis_bottom_on2'   : True,
            }

        self.default_line_settings = {
            'show_error_bars'       : False,
            'default_line_style'    : 'None',
            'default_marker_style'  : 'Auto',
            'default_marker_cycler' : cycle(['o', 'v', 's', '^',  'D', '<', 'X', '>', 'p', '*', 'h']),
            }

        self.plotted_data = {}
        self.line_settings = {}

        self.update_plot_settings()

    def ax_redraw(self, widget=None):
        self.canvas.mpl_disconnect(self.cid)
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect('draw_event', self.ax_redraw)

    def plot_data(self, data):
        if self.is_profile_plot:
            self.plot_profile(data)
        elif self.is_ift_plot:
            self.plot_ift(data)
        elif self.is_series_plot:
            self.plot_series(data)

    def plot_profile(self, data):
        q = data.q
        i = data.i
        err = data.err

        if self.plot_type == 'loglin' or self.plot_type == 'loglog':
            x = q
            y = i
            err = err

        elif self.plot_type == 'dimkratky':
            if data.rg is not None and data.i0 is not None:
                x = q*data.rg
                y = (q*data.rg)**2*i/data.i0
                err = (q*data.rg)**2*err/data.i0

            else:
                x = None
                y = None
                err = None

        elif self.plot_type == 'guinier':
            x = q**2
            y = i
            err = err

            if data.rg is not None and data.i0 is not None and data.guinier_qmin is not None and data.guinier_qmax is not None:
                fit, residual = self._calc_guinier_fit(data)

                find_closest = lambda a,l:min(l,key=lambda x:abs(x-a))
                closest_qmin = find_closest(data.guinier_qmin, q)
                closest_qmax = find_closest(data.guinier_qmax, q)

                q_idx_min = np.where(q == closest_qmin)[0][0]
                q_idx_max = np.where(q == closest_qmax)[0][0]

                data.q_idx_min = q_idx_min
                data.q_idx_max = q_idx_max

            else:
                fit = None
                residual = None


        if x is not None:
            if self.plot_type != 'guinier':
                lines1 = self.subplot1.errorbar(x, y, err)
                lines2 = None
                fitlines = None
            elif self.plot_type == 'guinier' and fit is not None:
                lines1 = self.subplot1.errorbar(x[q_idx_min:q_idx_max+1], y[q_idx_min:q_idx_max+1], 
                    err[q_idx_min:q_idx_max+1], zorder=1)
                fitlines = self.subplot1.plot(x[q_idx_min:q_idx_max+1], fit[q_idx_min:q_idx_max+1], color='k', zorder=2)
                lines2 = self.subplot2.plot(x[q_idx_min:q_idx_max+1], residual[q_idx_min:q_idx_max+1], 'o', zorder=2)
                zero_line = self.subplot2.axhline(color='k', zorder=1)
                
            else:
                lines1 = None
                lines2 = None
                fitlines = None
        else:
            lines1 = None
            lines2 = None
            fitlines = None

        self.plotted_data[data.id] = {'data': data, 'lines': (lines1, lines2, fitlines)}

        self.line_settings[data.id] = copy.copy(self.default_line_settings)
        self.line_settings[data.id]['default_marker_cycler'] = self.default_line_settings['default_marker_cycler']

        self.update_line_settings(data)

        if self.plot_settings['auto_limits']:
            self.do_auto_limits()

    def plot_ift(self, data):
        pass

    def plot_series(self, data):
        pass

    def _calc_guinier_fit(self, data):
        fit = data.i0*np.exp(-data.rg**2*data.q**2/3)

        residual = data.i - fit

        if self.plot_settings['norm_residuals']:
            residual = residual/data.err

        data.guinier_fit = fit
        data.guinier_residual = residual

        return fit, residual

    def do_auto_limits(self):

        if self.plot_type != 'guinier':
            plots = [self.subplot1]
        elif self.plot_type == 'guinier':
            plots = [self.subplot1, self.subplot2]

        for plot in plots:
            plot.set_autoscale_on(True)

            oldx = plot.get_xlim()
            oldy = plot.get_ylim()

            plot.relim()
            plot.autoscale_view()

            newx = plot.get_xlim()
            newy = plot.get_ylim()

        self.canvas.draw()

    def change_plot_settings(self, settings):

        for key, value in settings.items():
            self.plot_settings[key] = value

        self.update_plot_settings()

    def update_line_settings(self, data):

        line_settings = self.line_settings[data.id]

        lines1 = self.plotted_data[data.id]['lines'][0]

        if lines1 is not None:
            line, ec, el = lines1

            for each in ec:
                each.set_visible(line_settings['show_error_bars'])
            for each in el:
                each.set_visible(line_settings['show_error_bars'])

            line.set_linestyle(line_settings['default_line_style'])

            if line_settings['default_marker_style'] != 'Auto':
                line.set_marker(line_settings['default_marker_style'])
            else:
                line.set_marker(next(line_settings['default_marker_cycler']))

    def update_plot_settings(self):

        self.set_axes_settings()
        self.set_ticks_settings()

        self.canvas.draw()

    def set_ticks_settings(self):

        axes = {}
        axes2 = {}
        axeslabel = {}
        axeslabel2 = {}

        if self.plot_settings['axis_bottom_on']:
            axes['bottom'] = True
        else:
            axes['bottom'] = False

        if self.plot_settings['axis_top_on']:
            axes['top'] = True
        else:
            axes['top'] = False

        if self.plot_settings['axis_left_on']:
            axes['left'] = True
        else:
            axes['left'] = False

        if self.plot_settings['axis_right_on']:
            axes['right'] = True
        else:
            axes['right'] = False

        if self.plot_settings['axis_bottom_on2']:
            axes2['bottom'] = True
        else:
            axes2['bottom'] = False

        if self.plot_settings['axis_top_on2']:
            axes2['top'] = True
        else:
            axes2['top'] = False

        if self.plot_settings['axis_left_on2']:
            axes2['left'] = True
        else:
            axes2['left'] = False

        if self.plot_settings['axis_right_on2']:
            axes2['right'] = True
        else:
            axes2['right'] = False


        if self.plot_settings['axis_bottom_on'] and self.plot_settings['label_bottom']:
            axeslabel['labelbottom'] = True
        else:
            axeslabel['labelbottom'] = False

        if self.plot_settings['axis_top_on'] and self.plot_settings['label_top']:
            axeslabel['labeltop'] = True
        else:
            axeslabel['labeltop'] = False

        if self.plot_settings['axis_left_on'] and self.plot_settings['label_left']:
            axeslabel['labelleft'] = True
        else:
            axeslabel['labelleft'] = False

        if self.plot_settings['axis_right_on'] and self.plot_settings['label_right']:
            axeslabel['labelright'] = True
        else:
            axeslabel['labelright'] = False

        if self.plot_settings['axis_bottom_on2'] and self.plot_settings['label_bottom2']:
            axeslabel2['labelbottom'] = True
        else:
            axeslabel2['labelbottom'] = False

        if self.plot_settings['axis_top_on2'] and self.plot_settings['label_top2']:
            axeslabel2['labeltop'] = True
        else:
            axeslabel2['labeltop'] = False

        if self.plot_settings['axis_left_on2'] and self.plot_settings['label_left2']:
            axeslabel2['labelleft'] = True
        else:
            axeslabel2['labelleft'] = False

        if self.plot_settings['axis_right_on2'] and self.plot_settings['label_right2']:
            axeslabel2['labelright'] = True
        else:
            axeslabel2['labelright'] = False

        if self.subplot1 is not None:
            if self.plot_settings['major_ticks_x'] and self.plot_settings['minor_ticks_x']:
                self.subplot1.tick_params(which='both', direction=self.plot_settings['tick_position_x'], axis='x',
                    **axes, **axeslabel)

            elif self.plot_settings['major_ticks_x']:
                self.subplot1.tick_params(which='major', direction=self.plot_settings['tick_position_x'], axis='x',
                    **axes, **axeslabel)
                self.subplot1.tick_params(which='minor', axis='x', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            elif self.plot_settings['minor_ticks_x']:
                self.subplot1.tick_params(which='minor', direction=self.plot_settings['tick_position_x'], axis='x',
                    **axes, **axeslabel)
                self.subplot1.tick_params(which='major', axis='x', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            else:
                self.subplot1.tick_params(which='both', axis='x', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)
                

            if self.plot_settings['major_ticks_y'] and self.plot_settings['minor_ticks_y']:
                self.subplot1.tick_params(which='both', direction=self.plot_settings['tick_position_y'], axis='y',
                    **axes, **axeslabel)

            elif self.plot_settings['major_ticks_y']:
                self.subplot1.tick_params(which='major', direction=self.plot_settings['tick_position_y'], axis='y',
                    **axes, **axeslabel)
                self.subplot1.tick_params(which='minor', axis='y', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            elif self.plot_settings['minor_ticks_y']:
                self.subplot1.tick_params(which='minor', direction=self.plot_settings['tick_position_y'], axis='y',
                    **axes, **axeslabel)
                self.subplot1.tick_params(which='major', axis='y', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            else:
                self.subplot1.tick_params(which='both', axis='y', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            self.subplot1.tick_params(which='both', axis='x', labelsize=self.plot_settings['tick_x_size'])
            self.subplot1.tick_params(which='both', axis='y', labelsize=self.plot_settings['tick_y_size'])

            for tick in self.subplot1.get_xticklabels(which='both'):
                tick.set_fontname(self.plot_settings['tick_x_font'])

            for tick in self.subplot1.get_yticklabels(which='both'):
                tick.set_fontname(self.plot_settings['tick_y_font'])


        if self.subplot2 is not None:
            if self.plot_settings['major_ticks_x2'] and self.plot_settings['minor_ticks_x2']:
                self.subplot2.tick_params(which='both', direction=self.plot_settings['tick_position_x2'], axis='x',
                    **axes2, **axeslabel2)

            elif self.plot_settings['major_ticks_x2']:
                self.subplot2.tick_params(which='major', direction=self.plot_settings['tick_position_x2'], axis='x',
                    **axes2, **axeslabel2)
                self.subplot2.tick_params(which='minor', axis='x', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            elif self.plot_settings['minor_ticks_x2']:
                self.subplot2.tick_params(which='minor', direction=self.plot_settings['tick_position_x2'], axis='x',
                    **axes2, **axeslabel2)
                self.subplot2.tick_params(which='major', axis='x', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            else:
                self.subplot2.tick_params(which='both', axis='x', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)
                

            if self.plot_settings['major_ticks_y2'] and self.plot_settings['minor_ticks_y2']:
                self.subplot2.tick_params(which='both', direction=self.plot_settings['tick_position_y2'], axis='y',
                    **axes2, **axeslabel2)

            elif self.plot_settings['major_ticks_y2']:
                self.subplot2.tick_params(which='major', direction=self.plot_settings['tick_position_y2'], axis='y',
                    **axes2, **axeslabel2)
                self.subplot2.tick_params(which='minor', axis='y', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            elif self.plot_settings['minor_ticks_y2']:
                self.subplot2.tick_params(which='minor', direction=self.plot_settings['tick_position_y2'], axis='y',
                    **axes2, **axeslabel2)
                self.subplot2.tick_params(which='major', axis='y', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            else:
                self.subplot2.tick_params(which='both', axis='y', left=False, right=False, top=False, bottom=False,
                    labelleft=False, labelright=False, labeltop=False, labelbottom=False)

            self.subplot2.tick_params(which='both', axis='x', labelsize=self.plot_settings['tick_x2_size'])
            self.subplot2.tick_params(which='both', axis='y', labelsize=self.plot_settings['tick_y2_size'])

            for tick in self.subplot2.get_xticklabels(which='both'):
                tick.set_fontname(self.plot_settings['tick_x2_font'])

            for tick in self.subplot2.get_yticklabels(which='both'):
                tick.set_fontname(self.plot_settings['tick_y2_font'])

    def set_axes_settings(self):

        if self.subplot1 is not None:
            if self.plot_settings['axis_left_on']:
                self.subplot1.spines['left'].set_color('black')
            else:
                self.subplot1.spines['left'].set_color('none')

            if self.plot_settings['axis_right_on']:
                self.subplot1.spines['right'].set_color('black')
            else:
                self.subplot1.spines['right'].set_color('none')

            if self.plot_settings['axis_top_on']:
                self.subplot1.spines['top'].set_color('black')
            else:
                self.subplot1.spines['top'].set_color('none')

            if self.plot_settings['axis_bottom_on']:
                self.subplot1.spines['bottom'].set_color('black')
            else:
                self.subplot1.spines['bottom'].set_color('none')

        if self.subplot2 is not None:
            if self.plot_settings['axis_left_on2']:
                self.subplot2.spines['left'].set_color('black')
            else:
                self.subplot2.spines['left'].set_color('none')

            if self.plot_settings['axis_right_on2']:
                self.subplot2.spines['right'].set_color('black')
            else:
                self.subplot2.spines['right'].set_color('none')

            if self.plot_settings['axis_top_on2']:
                self.subplot2.spines['top'].set_color('black')
            else:
                self.subplot2.spines['top'].set_color('none')

            if self.plot_settings['axis_bottom_on2']:
                self.subplot2.spines['bottom'].set_color('black')
            else:
                self.subplot2.spines['bottom'].set_color('none')
