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

import os.path
import collections
import platform

import wx
import wx.lib.agw.ultimatelistctrl as ULC
import wx.lib.scrolledpanel as scrolled

import SASFileIO


class DataPanel(wx.Panel):

    def __init__(self, *args, **kwargs):

        wx.Panel.__init__(self, *args, **kwargs)

        self._create_layout()
        self._initialize()

    def _create_layout(self):

        ctrl_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, "Data")
        static_box = ctrl_sizer.GetStaticBox()

        self.list_panel = scrolled.ScrolledPanel(static_box, -1, style=wx.BORDER_SUNKEN)
        self.list_panel.SetVirtualSize((200, 200))
        self.list_panel.SetScrollRate(20,20)
        self.list_panel.SetBackgroundColour(wx.Colour(250,250,250))

        self.list_sizer = wx.BoxSizer(wx.VERTICAL)
        self.list_panel.SetSizer(self.list_sizer)

        load = wx.Button(static_box, label='Load Data')
        remove = wx.Button(static_box, label='Remove Data')

        load.Bind(wx.EVT_BUTTON, self._on_load)
        remove.Bind(wx.EVT_BUTTON, self._on_remove)

        button_ctrl= wx.BoxSizer(wx.HORIZONTAL)
        button_ctrl.Add(load, border=5, flag=wx.RIGHT|wx.LEFT)
        button_ctrl.Add(remove, border=5, flag=wx.RIGHT)

        ctrl_sizer.Add(self.list_panel, border=5, flag=wx.ALL|wx.EXPAND, proportion=1)
        ctrl_sizer.Add(button_ctrl, border=5, flag=wx.BOTTOM|wx.TOP|wx.ALIGN_CENTER_HORIZONTAL)

        self.SetSizer(ctrl_sizer)

    def _initialize(self):
        self.loaded_files = collections.OrderedDict()

        standard_paths = wx.StandardPaths.Get()
        self.current_directory = standard_paths.GetUserLocalDataDir()

        self.top_window = self.GetParent()

    def _on_load(self, evt):

        wx.CallAfter(self._load_files)

    def _load_files(self):
        files = None

        filters = 'All files (*.*)|*.*|Dat files (*.dat)|*.dat|Txt files (*.txt)|*.txt'
        dialog = wx.FileDialog(self, 'Select a file', self.current_directory, 
            style = wx.FD_OPEN|wx.FD_MULTIPLE, wildcard = filters)

        # Show the dialog and get user input
        if dialog.ShowModal() == wx.ID_OK:
            files = dialog.GetPaths()

        # Destroy the dialog
        dialog.Destroy()

        if files is not None:
            if not isinstance(files, list):
                files = [files,]

            data = SASFileIO.load_files(files)
            self.current_directory = os.path.dirname(files[0])

        self.add_items(data)

    def add_items(self, data_list):
        self.list_panel.Freeze()

        for data in data_list:
            new_data_item = DataItemPanel(self.list_panel, data)

            item_id = self.top_window.NewControlId()
            data.id = item_id

            self.list_sizer.Add(new_data_item, flag=wx.EXPAND)
            self.loaded_files[item_id] = (data, new_data_item)

            data.item_panel = new_data_item

        self.top_window.plot_panel.load_data(data_list)

        self.list_panel.SetVirtualSize(self.list_panel.GetBestVirtualSize())
        self.list_panel.Layout()
        self.list_panel.Refresh()

        self.list_panel.Thaw()

    def _on_remove(self, evt):
        selected_items = self.get_selected_item_ids()
        wx.CallAfter(self.remove_items, selected_items)

    def remove_items(self, item_ids):
        self.list_panel.Freeze()

        for item_id in item_ids:
            data = self.loaded_files[item_id]

            data[1].Destroy()

            del self.loaded_files[item_id]

        self.list_panel.SetVirtualSize(self.list_panel.GetBestVirtualSize())
        self.list_panel.Layout()
        self.list_panel.Refresh()

        self.list_panel.Thaw()

    def deselect_all_except_one(self, data_id):
        self.list_panel.Freeze()

        for item_id, data in self.loaded_files.items():
            if item_id != data_id:
                if data[1].selected:
                    data[1].toggle_select()

        self.list_panel.Thaw()

    def select_all(self):
        self.list_panel.Freeze()

        for item_id, data in self.loaded_files.items():
            if not data[1].selected:
                data[1].toggle_select()

        self.list_panel.Thaw()

    def get_selected_items(self):
        selected_items = []

        for each in self.loaded_files.values():
            if each[1].selected:
                selected_items.append(each[1])

        return selected_items

    def get_selected_item_ids(self):
        selected_items = []

        for key, data in self.loaded_files.items():
            if data[1].selected:
                selected_items.append(key)

        return selected_items

    def get_data_item_panels(self):
        data_item_panels = [item[1] for item in self.loaded_files.values()]

        return data_item_panels

class DataItemPanel(wx.Panel):

    def __init__(self, parent, data, *args, **kwargs):

        wx.Panel.__init__(self, parent, *args, style=wx.BORDER_RAISED, **kwargs)

        self.data = data
        self.data_panel = parent.GetParent().GetParent()

        self._create_layout()

        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_mouse_button)
        self.Bind(wx.EVT_RIGHT_DOWN, self._on_right_mouse_button)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_press)

        opsys = platform.system()

        if opsys != 'Darwin':
            self.name.Bind(wx.EVT_LEFT_DOWN, self._on_left_mouse_button)
            self.name.Bind(wx.EVT_RIGHT_DOWN, self._on_right_mouse_button)
            self.name.Bind(wx.EVT_KEY_DOWN, self._on_key_press)

        self._initialize()

    def _create_layout(self):

        self.name = wx.StaticText(self, label=self.data.short_filename)
        top_sizer = wx.BoxSizer()
        top_sizer.Add(self.name, border=5, flag=wx.ALL)

        self.SetSizer(top_sizer)
        self.SetBackgroundColour(wx.Colour(250,250,250))

    def _initialize(self):
        self.selected = False

        self.highlight_bkg_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)

    def _on_key_press(self, evt):

        key = evt.GetKeyCode()

        if ((key == wx.WXK_DELETE) or (key == wx.WXK_BACK and evt.CmdDown())) and self.selected == True:
            self.removeSelf()
        elif key == 65 and evt.CmdDown(): #A
            self.data_panel.select_all()

    def _on_right_mouse_button(self, evt):
        if not self.selected:
            self.toggle_select()
            self.data_panel.deselect_all_except_one(self.data.id)

        # if int(wx.__version__.split('.')[0]) >= 3 and platform.system() == 'Darwin':
        #     wx.CallAfter(self._showPopupMenu)
        # else:
        #     self._showPopupMenu()

    def _on_left_mouse_button(self, evt):

        ctrl_is_down = evt.CmdDown()
        shift_is_down = evt.ShiftDown()

        if shift_is_down:
            self.data_panel.list_panel.Freeze()

            try:
                selected_items = self.data_panel.get_selected_items()
                data_item_panels = self.data_panel.get_data_item_panels()

                first_item = selected_items[0]
                first_item_idx = data_item_panels.index(first_item)

                last_item = selected_items[-1]
                last_item_idx = data_item_panels.index(last_item)

                this_item_idx = data_item_panels.index(self)

                if last_item_idx > this_item_idx:
                    adj = 0
                    idxs = [first_item_idx, this_item_idx]
                else:
                    idxs = [last_item_idx, this_item_idx]
                    adj = 1

                top_item = max(idxs)
                bottom_item = min(idxs)

                item_list = data_item_panels[bottom_item+adj:top_item+adj]
                for each in item_list:
                    each.toggle_select()
            except IndexError:
                pass

            self.data_panel.list_panel.Thaw()

        elif ctrl_is_down:
            self.toggle_select()
        else:
            self.data_panel.deselect_all_except_one(self.data.id)
            self.toggle_select()

        evt.Skip()

    def toggle_select(self):

        if self.selected:
            self.selected = False
            self.SetBackgroundColour(wx.Colour(250,250,250))
        else:
            self.selected = True

            self.SetBackgroundColour(self.highlight_bkg_color)

        self.Refresh()
