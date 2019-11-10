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


import wx
import wx.lib.agw.ultimatelistctrl as ULC
import wx.aui as aui


class FigurePanel(wx.Panel):

    def __init__(self, *args, **kwargs):

        wx.Panel.__init__(self, *args, **kwargs)

        self._create_layout()

    def _create_layout(self):

        ctrl_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, "Figure Controls")
        static_box = ctrl_sizer.GetStaticBox()

        self.figure_notebook = aui.AuiNotebook(self, style = aui.AUI_NB_TAB_MOVE | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_SCROLL_BUTTONS)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(ctrl_sizer, border=5, flag=wx.ALL)
        top_sizer.Add(self.figure_notebook, border=5, flag=wx.ALL)


        self.SetSizer(top_sizer)

    def _on_load(self, evt):
        pass

    def _on_remove(self, evt):
        pass