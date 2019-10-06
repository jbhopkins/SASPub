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

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import object, range, map
from io import open

if __name__ == "__main__" and __package__ is None:
    __package__ = "SASPub"

from itertools import cycle
import copy

import numpy as np
import wx
import wx.lib.agw.ultimatelistctrl as ULC
import wx.aui as aui
import matplotlib as mpl
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg
from matplotlib.figure import Figure
import matplotlib.colors as mplcol

mpl.rcParams['backend'] = 'WxAgg'

import Data


class PlotPanel(wx.Panel):

    def __init__(self, *args, **kwargs):

        wx.Panel.__init__(self, *args, **kwargs)

        self._create_layout()
        self._initialize()

        self.Layout()

    def _create_layout(self):

        ctrl_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, "Plot Controls")
        static_box = ctrl_sizer.GetStaticBox()

        self.plot_notebook = aui.AuiNotebook(self, style = aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_SCROLL_BUTTONS)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(ctrl_sizer, border=5, flag=wx.ALL)
        top_sizer.Add(self.plot_notebook, border=5, flag=wx.ALL|wx.EXPAND, proportion=1)


        self.SetSizer(top_sizer)

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
            'min_x_scale'       : 0.97,
            'max_x_scale'       : 1.03,
            'min_y_scale'       : 0.97,
            'max_y_scale'       : 1.03,
            }

        self.default_line_settings = {
            'show_error_bars'       : False,
            'default_line_style'    : 'None',
            'default_marker_style'  : 'Auto',
            'default_marker_cycler' : cycle(['o', 'v', 's', '^',  'D', '<', 'X', '>', 'p', '*', 'h']),
            }

        self.plotted_data = {}
        self.line_settings = {}

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
                lines1 = self.subplot1.errorbar(x, y, err, zorder=1)
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

        min_x_scale = self.plot_settings['min_x_scale']
        max_x_scale = self.plot_settings['max_x_scale']
        min_y_scale = self.plot_settings['min_y_scale']
        max_y_scale = self.plot_settings['max_y_scale']

        if self.plot_type == 'guinier':
            plot_q_min = 0
            plot_q_max = 0

            residual_min = None
            residual_max = None

            intensity_min = None
            intensity_max = None

            for key in self.plotted_data:
                if self.plotted_data[key]['lines'][0] is not None:
                    data = self.plotted_data[key]['data']
                    
                    q_min = data.guinier_qmin
                    q_max = data.guinier_qmax

                    plot_q_min = min(plot_q_min, q_min)
                    plot_q_max = max(plot_q_max, q_max)

                    rmin = np.min(data.guinier_residual[data.q_idx_min:data.q_idx_max+1])
                    rmax = np.max(data.guinier_residual[data.q_idx_min:data.q_idx_max+1])

                    imin = np.min(data.guinier_fit[data.q_idx_min:data.q_idx_max+1])
                    imax = np.max(data.guinier_fit[data.q_idx_min:data.q_idx_max+1])
                    imin2 = np.min(data.i[data.q_idx_min:data.q_idx_max+1])
                    imax2 = np.max(data.i[data.q_idx_min:data.q_idx_max+1])

                    if residual_min is None:
                        residual_min = rmin
                    else:
                        residual_min = min(rmin, residual_min)

                    if residual_max is None:
                        residual_max = rmax
                    else:
                        residual_max = max(rmax, residual_max)

                    if intensity_min is None:
                        intensity_min = min(imin, imin2)
                    else:
                        intensity_min = min(imin, imin2, intensity_min)

                    if intensity_max is None:
                        intensity_max = max(imax, imax2)
                    else:
                        intensity_max = max(imax, imax2, intensity_max)

            if plot_q_max == 0:
                plot_q_max = 0.1

            if residual_min is None:
                residual_min = 0

            if residual_max is None:
                residual_max = 0.1

            if intensity_min is None:
                intensity_min = 0.01

            if intensity_max is None:
                intensity_max = 0.1

            self.subplot1.set_xlim(plot_q_min**2*min_x_scale, plot_q_max**2*max_x_scale)
            self.subplot1.set_ylim(intensity_min*min_y_scale, intensity_max*max_y_scale)
            self.subplot2.set_ylim(residual_min*min_y_scale, residual_max*max_y_scale)

        elif self.plot_type == 'loglog' or self.plot_type == 'loglin':

            plot_q_min = None
            plot_q_max = None

            intensity_min = None
            intensity_max = None

            for key in self.plotted_data:
                if self.plotted_data[key]['lines'][0] is not None:
                    data = self.plotted_data[key]['data']

                    q_min = data.q[0]
                    q_max = data.q[-1]

                    imin = np.min(data.i[data.i>0])
                    imax = np.max(data.i)

                    if plot_q_min is None:
                        plot_q_min = q_min
                    else:
                        plot_q_min = min(plot_q_min, q_min)

                    if plot_q_max is None:
                        plot_q_max = q_max
                    else:
                        plot_q_max = max(plot_q_max, q_max)

                    if intensity_min is None:
                        intensity_min = imin
                    else:
                        intensity_min = min(imin, intensity_min)

                    if intensity_max is None:
                        intensity_max = imax
                    else:
                        intensity_max = max(imax, intensity_max)

            if plot_q_min is None:
                plot_q_min = 0

            if plot_q_max is None:
                plot_q_max = 0.1

            if intensity_min is None:
                intensity_min = 0.01

            if intensity_max is None:
                intensity_max = 0.1

            self.subplot1.set_xlim(plot_q_min*min_x_scale, plot_q_max*max_x_scale)
            self.subplot1.set_ylim(intensity_min*min_y_scale, intensity_max*max_y_scale)

        elif self.plot_type == 'dimkratky':

            plot_q_min = None
            plot_q_max = None

            intensity_min = None
            intensity_max = None

            for key in self.plotted_data:
                if self.plotted_data[key]['lines'][0] is not None:
                    data = self.plotted_data[key]['data']


                    q_min = data.q[0]*data.rg
                    q_max = data.q[-1]*data.rg

                    y = (data.q*data.rg)**2*data.i/data.i0

                    imin = np.min(y[y>0])
                    imax = np.max(y[y>0])


                    if plot_q_min is None:
                        plot_q_min = q_min
                    else:
                        plot_q_min = min(plot_q_min, q_min)

                    if plot_q_max is None:
                        plot_q_max = q_max
                    else:
                        plot_q_max = max(plot_q_max, q_max)

                    if intensity_min is None:
                        intensity_min = imin
                    else:
                        intensity_min = min(imin, intensity_min)

                    if intensity_max is None:
                        intensity_max = imax
                    else:
                        intensity_max = max(imax, intensity_max)

            if plot_q_min is None:
                plot_q_min = 0

            if plot_q_max is None:
                plot_q_max = 0.1

            if intensity_min is None:
                intensity_min = 0

            if intensity_max is None:
                intensity_max = 0.1

            self.subplot1.set_xlim(plot_q_min*min_x_scale, plot_q_max*max_x_scale)
            self.subplot1.set_ylim(intensity_min*min_y_scale, intensity_max*max_y_scale)

        elif self.plot_type == 'ift':
            pass

        elif self.plot_type == 'series':
            pass

        self.canvas.draw()

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
