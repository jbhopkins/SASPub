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

import threading

import wx
import wx.aui as aui

import DataPanel
import PlotPanel
import FigurePanel

class MainFrame(wx.Frame):
    """
    .. todo::
        Support for scalers, measuring and taking dark counts

    This frame is the top level frame for the sector controls. it consists of a
    tab panel and several buttons for adding new controls. Each tab is a
    control group, the button opens a control set. It calls the :mod:`scancon`
    and :mod:`motorcon` and :mod:`ampcon` libraries to actually do anything.
    It communicates with the devices by calling ``Mp``, the python wrapper for ``MX``.
    """
    def __init__(self, *args, **kwargs):
        """
        Initializes the main frame. It takes the standard arguments for a
        :mod:`wx.Frame`, except parent should not be specified.
        """
        wx.Frame.__init__(self, None, *args, **kwargs)

        self._create_layout()

        self.Bind(wx.EVT_CLOSE, self._on_close)

        # self.Layout()
        # self.Fit()

    def _create_layout(self):
        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self.data_panel = DataPanel.DataPanel(self)
        self.plot_panel = PlotPanel.PlotPanel(self)
        self.figure_panel = FigurePanel.FigurePanel(self)

        self._mgr.AddPane(self.data_panel, aui.AuiPaneInfo().CloseButton(False).Left().
            Layer(0).Caption("Data Panel").PinButton(True).Row(0).Position(0))
        self._mgr.AddPane(self.plot_panel, aui.AuiPaneInfo().CloseButton(False).Center().
            Layer(0).Caption("Plot Panel").PinButton(True).Row(0).Position(0))
        self._mgr.AddPane(self.figure_panel, aui.AuiPaneInfo().CloseButton(False).Right().
            Layer(0).Caption("Figure Panel").PinButton(True).Row(0).Position(0))

        

        size = self.GetSize()
        self._mgr.GetPane(self.data_panel).MinSize(300,-1)
        self._mgr.GetPane(self.plot_panel).MinSize((size[0]-300.)/2., -1)
        self._mgr.GetPane(self.figure_panel).MinSize((size[0]-300.)/2., -1)

        self._mgr.GetPane(self.data_panel).FloatingSize(300, size[1])
        self._mgr.GetPane(self.plot_panel).FloatingSize((size[0]-300.)/2., size[1])
        self._mgr.GetPane(self.figure_panel).FloatingSize((size[0]-300.)/2., size[1])

        self._mgr.Update()

    def _on_close(self, event):
        self._mgr.UnInit()
        event.Skip()


#########################################
#This gets around not being able to catch errors in threads
#Code from: https://bugs.python.org/issue1230540
def setup_thread_excepthook():
    """
    Workaround for `sys.excepthook` thread bug from:
    http://bugs.python.org/issue1230540

    Call once from the main thread before creating any threads.
    """

    init_original = threading.Thread.__init__

    def init(self, *args, **kwargs):

        init_original(self, *args, **kwargs)
        run_original = self.run

        def run_with_except_hook(*args2, **kwargs2):
            try:
                run_original(*args2, **kwargs2)
            except Exception:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook

    threading.Thread.__init__ = init


class MyApp(wx.App):
    """The top level wx.App that we subclass to add an exceptionhook."""

    def OnInit(self):
        """Initializes the app. Calls the :class:`MainFrame`"""

        frame = MainFrame(title="SASPub", size=(1000, 600))
        frame.Show()

        return True

    def BringWindowToFront(self):
        """
        Overwrites this default method to deal with the possibility that it
        is called when the frame is closed.
        """
        try: # it's possible for this event to come when the frame is closed
            self.GetTopWindow().Raise()
        except:
            pass

    def ExceptionHook(self, errType, value, trace):
        """
        Creates an exception hook that catches all uncaught exceptions and informs
        users of them, instead of letting the program crash. From
        http://apprize.info/python/wxpython/10.html
        """
        err = traceback.format_exception(errType, value, trace)
        errTxt = "\n".join(err)
        msg = ("An unexpected error has occurred, please report it to the "
                "developers. You may need to restart SASPub to continue working"
                "\n\nError:\n%s" %(errTxt))

        if self and self.IsMainLoopRunning():
            if not self.HandleError(value):
                wx.CallAfter(wx.lib.dialogs.scrolledMessageDialog, None, msg, "Unexpected Error")
        else:
            sys.stderr.write(msg)

    def HandleError(self, error):
        """
        Override in subclass to handle errors

        :return: True to allow program to continue running without showing error.
            False to show the error.
        """
        return False


if __name__ == '__main__':
    setup_thread_excepthook()

    app = MyApp(0)   #MyApp(redirect = True)
    # wx.lib.inspection.InspectionTool().Show()
    app.MainLoop()