#!/usr/bin/env python

# BMS Tools
# Copyright (C) 2020 Eric Poulsen
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time
import re
import serial
import serial.tools.list_ports
import math
import enum
import importlib
import functools
import random
import threading
import traceback

from pprint import pprint

import wx
import wx.grid
import wx.svg
import wx.lib.scrolledpanel as scrolled
import wx.lib.newevent
import wx.lib.masked.numctrl
import wx.html2
import bmstools
import bmstools.jbd as jbd
from bmstools.jbd.logging import Logger

appName = 'JBD BMS Tools'
appVersion = bmstools.version
appUrl = 'https://gitlab.com/MrSurly/bms-tools'
author = 'Eric Poulsen'
authorEmail = 'eric@zyxod.com'
authorFullEmail = '"Eric Poulsen" <eric@zyxod.com>'
releaseDate = 'N/A'
appNameWithVersion = f'{appName} {appVersion}'

try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    base_path = sys._MEIPASS
except Exception:
    base_path = os.path.dirname(os.path.abspath(__file__))

rflags = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT
lflags = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT
defaultBorder = wx.EXPAND | wx.TOP | wx.BOTTOM | wx.LEFT | wx.RIGHT, 7
colGap = (10,1)
boxGap = (3,3)

class PluginException(Exception): pass

class FieldAnnotation:
    def __init__(self, fieldName = None, fieldLabel = None, range = None, tooltip = None):
        self.fieldName = fieldName
        self.fieldLabel = fieldLabel
        self.range = range
        self.tooltip = tooltip

cellRange       = (0, 65536, 100)
covpHighRange   = (3110, 4635, 100)
cuvpHighRange   = (1575, 3101, 100)

packRange       = (0, 655350, 100)
tempRange       = (-273.15, 6316.4, 1)
mahRange        = (0, 655350, 1000)
chgRange        = (0, 327670, 100)
dsgRange        = (-327680, 0, 100)
delayRange      = (0, 255, 1)

fa = FieldAnnotation
field_annotations = [
    fa('covp', range=cellRange, tooltip='cell over volt protection'),
    fa('covp_rel', range=cellRange, tooltip='cell over volt protection release'),
    fa('covp_delay', range=delayRange, tooltip='cell over volt protection delay'),
    fa('cuvp', range=cellRange, tooltip='cell under volt protection'),
    fa('cuvp_rel', range=cellRange, tooltip='cell under volt protection release'),
    fa('cuvp_delay', range=delayRange, tooltip='cell under volt protection delay'),
    fa('povp', range=packRange, tooltip='pack over volt protection'),
    fa('povp_rel', range=packRange, tooltip='pack over volt protection release'),
    fa('povp_delay', range=delayRange, tooltip='pack over volt protection delay'),
    fa('puvp', range=packRange, tooltip='pack under volt protection'),
    fa('puvp_rel', range=packRange, tooltip='pack under volt protection release'),
    fa('puvp_delay', range=delayRange, tooltip='pack under volt protection delay'),
    fa('chgot', range=tempRange, tooltip='charge over temp'),
    fa('chgot_rel', range=tempRange, tooltip='charge over temp release'),
    fa('chgot_delay', range=delayRange, tooltip='charge over temp delay'),
    fa('chgut', range=tempRange, tooltip='charge under temp'),
    fa('chgut_rel', range=tempRange, tooltip='charge under temp release'),
    fa('chgut_delay', range=delayRange, tooltip='charge under temp delay'),
    fa('dsgot', range=tempRange, tooltip='discharge over temp'),
    fa('dsgot_rel', range=tempRange, tooltip='discharge over temp release'),
    fa('dsgot_delay', range=delayRange, tooltip='discharge over temp delay'),
    fa('dsgut', range=tempRange, tooltip='discharge under temp'),
    fa('dsgut_rel', range=tempRange, tooltip='discharge under temp release'),
    fa('dsgut_delay', range=delayRange, tooltip='discharge under tempdelay'),
 
    fa('chgoc', range=chgRange, tooltip='charge over current'),
    fa('chgoc_rel', range=delayRange, tooltip='charge over current release'),
    fa('chgoc_delay', range=delayRange, tooltip='charge over current delay'),
    fa('dsgoc', range=dsgRange, tooltip='discharge over current'),
    fa('dsgoc_rel', range=delayRange, tooltip='discharge over current release'),
    fa('dsgoc_delay', range=delayRange, tooltip='discharge over current delay'),

    fa('covp_high', range=covpHighRange, tooltip='cell over volt protection (level 2)'),
    #fa('covp_high', range=cellRange, tooltip='cell over volt protection (level 2)'),
    fa('covp_high_delay', range=cellRange, tooltip='cell over volt protection (level 2) delay'),
    fa('cuvp_high', range=cuvpHighRange, tooltip='cell under volt protection (level 2)'),
    #fa('cuvp_high', range=cellRange, tooltip='cell under volt protection (level 2)'),
    fa('cuvp_high_delay', range=cellRange, tooltip='cell under volt protection (level 2) delay'),


    fa('sc_dsgoc_x2', tooltip='double all short circuit and discharge overcurrent values'),

    fa('sc_rel', tooltip='short circuit release'),

    fa('dsgoc2', tooltip='discharge overcurrent protection (level 2) shunt voltage'),
    fa('dsgoc2_delay', tooltip='discharge overcurrent protection (level 2) delay'),

    fa('sc', tooltip='short circuit shunt voltage'),
    fa('sc_delay', tooltip='short circuit delay'),

    fa('chgoc_err_cnt', tooltip = 'charge overcurrent error count'),
    fa('dsgoc_err_cnt', tooltip = 'discharge overcurrent error count'),
    fa('chgot_err_cnt', tooltip = 'charge overtemp error count'),
    fa('chgut_err_cnt', tooltip = 'charge undertemp error count'),
    fa('dsgot_err_cnt', tooltip = 'discharge overtemp error count'),
    fa('dsgut_err_cnt', tooltip = 'discharge undertemp error count'),
    fa('povp_err_cnt', tooltip = 'pack overvoltage error count'),
    fa('puvp_err_cnt', tooltip = 'pack undervoltage error count'),
    fa('covp_err_cnt', tooltip = 'cell overvoltage error count'),
    fa('cuvp_err_cnt', tooltip = 'cell undervoltage error count'),
    fa('sc_err_cnt', tooltip = 'short circuit error count'),

    fa('covp_err', tooltip = 'cell overvoltage error'),
    fa('cuvp_err', tooltip = 'cell undervoltage error'),
    fa('povp_err', tooltip = 'pack overvoltage error'),
    fa('puvp_err', tooltip = 'pack undervoltage error'),
    fa('chgoc_err', tooltip = 'charge overcurrent error'),
    fa('dsgoc_err', tooltip = 'discharge overcurrent error'),
    fa('chgot_err', tooltip = 'charge overtemp error'),
    fa('chgut_err', tooltip = 'charge undertemp error'),
    fa('dsgot_err', tooltip = 'discharge overtemp error'),
    fa('dsgut_err', tooltip = 'discharge undertemp error'),
    fa('sc_err', tooltip = 'short circuit error'),
    fa('afe_err', tooltip = 'analog front end error'),
    fa('software_err', tooltip = 'software error; FET(s) are disabled in calibration & misc tab'),

    fa('bal_start', range=cellRange, tooltip='balance start voltage: start balancing when above this threshold'),
    fa('bal_window', range=(*cellRange[:2], 10), tooltip='balance window: enable balancing if voltage is outside this window'),

    fa('design_cap', range=mahRange, tooltip='design capacity'),
    fa('cycle_cap', range=mahRange, tooltip='cycle capacity'),
    fa('dsg_rate', range=(0.0, 100.0, .1), tooltip='self discharge rate'),
    fa('fet_ctrl', range=(0, 65535, 1), tooltip=''),
    fa('led_timer', range=(0, 65535, 1), tooltip=''),

    fa('cap_100', range=cellRange, tooltip='full cell voltage'),
    fa('cap_80', range=cellRange, tooltip='80% cell voltage'),
    fa('cap_60', range=cellRange, tooltip='60% cell voltage'),
    fa('cap_40', range=cellRange, tooltip='40% cell voltage'),
    fa('cap_20', range=cellRange, tooltip='20% cell voltage'),
    fa('cap_0', range=cellRange, tooltip='empty cell voltage'),

    fa('cycle_cnt', range=(0, 65535, 1), tooltip='cycle count'),
    fa('shunt_res', range=(0.0, 6553.5, .1), tooltip='shunt resistor'),
]
del fa

LockClass = threading.Lock

class PulseText(wx.StaticText):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.origColors = self.GetBackgroundColour(), self.GetForegroundColour()
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._pulse)

    def SetLabel(self, *args, **kwargs):
        super().SetLabel(*args, **kwargs)
        if args and args[0]:
            self._startPulse()

    def _startPulse(self):
        self._pulseCnt = 0
        self.timer.Start(250)

    def _pulse(self, evt):
        self._pulseCnt += 1
        print(f'pulse {self._pulseCnt}')
        if self._pulseCnt == 5:
            self.timer.Stop()





class DebugWindow(wx.Frame):
    CloseEvent, EVT_TEXTFRAME_CLOSE = wx.lib.newevent.NewEvent()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.txt = wx.TextCtrl(self, style = wx.TE_RICH | wx.TE_MULTILINE | wx.TE_BESTWRAP | wx.TE_READONLY)
        clearButton = wx.Button(self, label = 'Clear', name = 'clear_btn')
        vbox.Add(self.txt, 1, wx.EXPAND)
        vbox.Add(clearButton)
        self.SetSizer(vbox)
        self.outStyle = wx.TextAttr(wx.BLACK, wx.WHITE)
        self.errStyle = wx.TextAttr(wx.WHITE, wx.RED)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_BUTTON, self.onButton)

    def onClose(self, evt):
        evt.StopPropagation()
        wx.PostEvent(self.Parent, self.CloseEvent())

    def onButton(self, evt):
        n = evt.EventObject.Name
        if n == 'clear_btn':
            self.txt.Clear()

    def trim(self):
        value = self.txt.GetValue()
        value = value.replace('\n\n', '\n') # this is stupid
        lines = value.splitlines()
        lines = lines[-500:]
        self.txt.SetValue(''.join([i+'\n' for i in lines]))
        self.txt.SetScrollPos(wx.VERTICAL, self.txt.GetScrollRange(wx.VERTICAL))
        self.txt.SetInsertionPoint(-1)

    def stdout(self, text):
        self.txt.SetDefaultStyle(self.outStyle)
        self.txt.write(text)
        self.trim()

    def stderr(self, text):
        self.txt.SetDefaultStyle(self.errStyle)
        self.txt.write(text)
        self.trim()
        self.Show()

    write = stdout

# we have to do all this convoluted writing
# via events else `print` statements from 
# background threads will clog up the works.

class TextDataType(enum.Enum):
    STDOUT = 1
    STDERR = 2

class WriteRedirect:
    TextEvent, EVT_TEXT = wx.lib.newevent.NewEvent()
    def __init__(self, parent, type):
        self.parent = parent
        self.type = type

    def write(self, text):
        wx.PostEvent(self.parent, self.TextEvent(text = text, type = self.type))

    def flush(self): pass



class AboutDialog(wx.Dialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.SetTitle(f'About {appName}')
        self.SetSize((700,700))

        vbox = wx.BoxSizer(wx.VERTICAL)

        if 1:
            lines = [
                appName,
                appVersion,
                '',
                authorEmail, 
                '',
                appUrl
            ]
            t = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_AUTO_URL, size = (200,200))
            t.SetValue('\n'.join(lines))
            vbox.Add(t, 1, wx.EXPAND)

        if 0:
            outer = wx.BoxSizer()
            outer.Add(vbox, 1, wx.EXPAND | wx.ALL, 10)

        self.SetSizerAndFit(vbox)
        #self.SetSizer(outer)

    def onLoad(self, evt):
        try:
            js = 'document.getElementById("main").scrollHeight'
            height = int(self.h.RunScript(js)[1])
            js = 'document.getElementById("main").scrollWidth'
            width = int(self.h.RunScript(js)[1])
        except: 
            return
        #self.h.SetSize(-1, -1, width * 3, height * 3, sizeFlags = wx.SIZE_FORCE)

        w,h = self.h.GetSize()

        self.h.SetMinSize(wx.Size(400, height))
        self.SetMinSize(wx.Size(width*2, height*2))
        print(f'onload called: {width}x{height}')

class PasswordErrorDialog(wx.Dialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.SetTitle('Password Error')

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer()
        hbox.Add(wx.StaticText(self, label="BMS reports incorrect password"), 0, wx.ALIGN_CENTER , border = 5)
        vbox.Add(hbox, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)

        clearButton = wx.Button(self, label='Clear Password')
        clearButton.SetDefault()
        closeButton = wx.Button(self, label='Ok', name = 'close_btn')
        hbox.Add(clearButton, flag=wx.ALL, border = 5)
        hbox.Add(closeButton, flag=wx.ALL, border=5)

        #vbox.Add(hbox, flag=wx.ALIGN_CENTER|wx.ALL, border=10)
        vbox.Add(hbox)

        clearButton.Bind(wx.EVT_BUTTON, self.onButton)
        closeButton.Bind(wx.EVT_BUTTON, self.onButton)
        self.SetSizerAndFit(vbox)

    def onButton(self, e):
        n = e.EventObject.Name
        if n == 'close_btn':
            self.EndModal(wx.ID_CANCEL)
        else:
            self.EndModal(wx.ID_OK)

class SerialPortDialog(wx.Dialog):

    def __init__(self, *args, **kwargs):
        self.curPort = kwargs.pop('port', None)
        super().__init__(*args, **kwargs)

        self.SetTitle('Serial Port Settings')

        vbox = wx.BoxSizer(wx.VERTICAL)

        self.portBox = BetterChoice(self, choices=[], name='port')
        self.refresh()

        hbox = wx.BoxSizer()

        hbox.Add(self.portBox, 0, wx.ALIGN_CENTER)
        hbox.Add(wx.StaticText(self, label="9600 8N1"), 0, wx.ALIGN_CENTER | wx.LEFT, border = 5)
        vbox.Add(hbox, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, label='Ok')
        okButton.SetDefault()
        refreshButton = wx.Button(self, label='Refresh', name='refresh_btn')
        closeButton = wx.Button(self, label='Close', name = 'close_btn')
        hbox.Add(okButton, flag=wx.ALL, border = 5)
        hbox.Add(refreshButton, flag=wx.ALL, border = 5)
        hbox.Add(closeButton, flag=wx.ALL, border=5)

        #vbox.Add(hbox, flag=wx.ALIGN_CENTER|wx.ALL, border=10)
        vbox.Add(hbox)

        okButton.Bind(wx.EVT_BUTTON, self.onButton)
        refreshButton.Bind(wx.EVT_BUTTON, self.onButton)
        closeButton.Bind(wx.EVT_BUTTON, self.onButton)
        self.SetSizerAndFit(vbox)

    def refresh(self):
        self.ports = serial.tools.list_ports.comports()
        self.portBox.Set([p.device for p in self.ports])
        if not self.portBox.SetValue(self.curPort):
            if self.portBox.GetCount():
                self.portBox.SetSelection(0)

    def onButton(self, e):
        n = e.EventObject.Name
        if n == 'refresh_btn':
            self.refresh()
            return

        self.selectedPort = None
        i = self.portBox.GetSelection()
        if i != wx.NOT_FOUND:
            self.selectedPort = self.ports[i].device
        
        if n == 'close_btn':
            self.EndModal(wx.ID_CANCEL)
        else:
            self.EndModal(wx.ID_OK)

class BetterChoice(wx.Choice):
    def __init__(self, parent, **kwargs):
        choices = kwargs.get('choices')
        kwargs['choices'] = [str(i) for i in choices]
        super().__init__(parent, **kwargs)
        self.SetSelection(0)

    def GetValue(self):
        idx = self.GetSelection()
        if idx == wx.NOT_FOUND:
            return None
        return self.GetString(idx)

    def SetValue(self, value):
        idx = self.FindString(str(value))
        if idx == wx.NOT_FOUND: 
            print(f'{self.__class__.__name__}: "{self.Name}" set to unknown choice {value}')
            return False
        self.SetSelection(idx)
        return True

class EnumChoice(BetterChoice):
    def __init__(self, parent, **kwargs):
        choices = kwargs.get('choices')
        assert issubclass(choices, jbd.LabelEnum)
        self.__enum_cls = choices
        super().__init__(parent, **kwargs)
        self.SetSelection(0)
    
    def GetValue(self):
        idx = self.GetSelection()
        s = self.GetString(idx)
        return self.__enum_cls.byDisplay(int(s))

class SVGImage(wx.Panel):
    def __init__(self, parent, img, name = 'SvgImage'):
        super().__init__(parent, name = name)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.SetImage(img)
        self.Bind(wx.EVT_SIZE, self.onSize)
        self.Refresh()

    def SetImage(self, img):
        if isinstance(img, wx.svg.SVGimage):
            self.img = img
        else:
            self.img = wx.svg.SVGimage.CreateFromFile(img)
        self.Refresh()

    def onSize(self, evt):
        w,h = self.Size
        if any([i < 2 for i in (w,h)]):
            w = h = max(w,h)
            self.SetMinSize((w,h))

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(wx.GREEN, wx.TRANSPARENT))
        dc.Clear()
        hscale = self.Size.width / self.img.width
        vscale = self.Size.height / self.img.height
        scale = min(hscale, vscale)
        w,h = [int(i * scale) for i in (self.img.width, self.img.height)]

        bm = self.img.ConvertToScaledBitmap(self.Size)
        dc2 = wx.MemoryDC(bm)
        xoff = (dc.Size.width - w)//2
        yoff = (dc.Size.height - h)//2
        dc.Blit(xoff,yoff,*dc2.Size,dc2,0,0)

class BoolImage(SVGImage):
    def __init__(self, parent, img1, img2, name):
        if isinstance(img1, wx.svg.SVGimage):
            self.img1 = fn
        else:
            self.img1 = wx.svg.SVGimage.CreateFromFile(img1)
        if isinstance(img2, wx.svg.SVGimage):
            self.img2 = fn
        else:
            self.img2 = wx.svg.SVGimage.CreateFromFile(img2)

        super().__init__(parent, img1, name)
    
    def SetValue(self, which):
        self.SetImage(self.img1 if bool(which) else self.img2)
        self.Refresh()

class LayoutGen: 
    def __init__(self, parent):
        tc = wx.TextCtrl(parent)
        self.txtSize31 = tc.GetSizeFromTextSize(parent.GetTextExtent('9' * 31))
        self.txtSize30 = tc.GetSizeFromTextSize(parent.GetTextExtent('9' * 30))
        self.txtSize25 = tc.GetSizeFromTextSize(parent.GetTextExtent('9' * 25))
        self.txtSize20 = tc.GetSizeFromTextSize(parent.GetTextExtent('9' * 20))
        self.txtSize10 = tc.GetSizeFromTextSize(parent.GetTextExtent('9' * 10))
        self.txtSize8  = tc.GetSizeFromTextSize(parent.GetTextExtent('99999999'))
        self.txtSize6  = tc.GetSizeFromTextSize(parent.GetTextExtent('999999'))
        self.txtSize5  = tc.GetSizeFromTextSize(parent.GetTextExtent('99999'))
        self.txtSize4  = tc.GetSizeFromTextSize(parent.GetTextExtent('9999'))
        self.txtSize3  = tc.GetSizeFromTextSize(parent.GetTextExtent('999'))
        self.txtSize2  = tc.GetSizeFromTextSize(parent.GetTextExtent('99'))
        self.txtSize1  = tc.GetSizeFromTextSize(parent.GetTextExtent('9'))
        tc.Destroy()
    
    ####
    ##### Info tab methods 
    ####

    def infoTabLayout(self, tab):
        hsizer = wx.BoxSizer()
        tab.SetSizer(hsizer)
        self.cellsInfoLayout(tab, hsizer, colGap, boxGap)
        self.packInfoLayout(tab, hsizer, colGap, boxGap)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer.Add(vsizer, 1, wx.EXPAND)
        self.deviceInfoLayout(tab, vsizer, colGap, boxGap)
        self.deviceStatusLayout(tab, vsizer, colGap, boxGap)

        tab.Layout()
        tab.Fit()

    def cellsInfoLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 0, *defaultBorder)

        sb = wx.StaticBox(panel, label='Cells')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        sp = scrolled.ScrolledPanel(sb)

        sbs.Add(sp, 1, *defaultBorder)
        bs = wx.BoxSizer(wx.VERTICAL)
        sp.SetSizer(bs)

        if isinstance(sp, scrolled.ScrolledPanel):
            sp.SetupScrolling(scroll_x=False)

        rows = 4
        cols = 4
        g = wx.grid.Grid(sp, name='cell_grid')
        g.CreateGrid(rows, cols)
        g.EnableEditing(False)
        g.DisableDragColSize()
        g.DisableDragRowSize()
        g.SetColLabelSize(self.txtSize4[1])

        g.SetColLabelValue(0, 'Cell')
        g.SetColLabelValue(1, 'mV')
        g.SetColLabelValue(2, 'Bal')
        g.SetColLabelValue(3, 'Temp')
        g.SetRowLabelSize(1)
        for i in range(cols):
            g.SetColSize(i, self.txtSize4[0])

        bs.Add(g, 1, wx.EXPAND)

    def packInfoLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 0, *defaultBorder)

        sb = wx.StaticBox(panel, label='Pack')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        fgs = wx.FlexGridSizer(3, gap = boxGap)
        sbs.Add(fgs, 0, *defaultBorder)

        def gen(label, fn, unit = ''):
            t = wx.TextCtrl(sb, name=fn, size=self.txtSize6, style=wx.TE_RIGHT)
            t.Enable(False)
            return [
                (wx.StaticText(sb, label=label + ':'), 0, rflags),
                (t, 0, lflags),
                (wx.StaticText(sb, label=unit), 0, lflags),
            ]
        fgs.AddMany(gen('Pack V', 'pack_mv', 'mV'))
        fgs.AddMany(gen('Pack I', 'pack_ma', 'mA'))
        fgs.AddMany(gen('Avg V', 'cell_avg_mv', 'mV'))
        fgs.AddMany(gen('Max V', 'cell_max_mv', 'mV'))
        fgs.AddMany(gen('Min V', 'cell_min_mv', 'mV'))
        fgs.AddMany(gen('Δ V', 'cell_delta_mv', 'mV'))
        fgs.AddMany(gen('Cycles', 'cycle_cnt'))
        fgs.AddMany(gen('Capacity', 'full_cap', 'mAh'))
        fgs.AddMany(gen('Cap Rem', 'cur_cap', 'mAh'))
        sbs.Add(RoundGauge(sb, name='cap_pct'), 1, wx.EXPAND)
        bs = wx.BoxSizer()
        sbs.Add(bs, 1, wx.EXPAND)
        bs.AddStretchSpacer()
        bs.Add(wx.StaticText(sb, label='Remaining Capacity'), 0,  wx.TOP)
        bs.AddStretchSpacer()

    def deviceInfoLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 1, *defaultBorder)

        sb = wx.StaticBox(panel, label='Device')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        fgs = wx.FlexGridSizer(2, gap = boxGap)
        sbs.Add(fgs, 0, *defaultBorder)

        # device name
        fgs.Add(wx.StaticText(sb, label='Name:'), 0, rflags)
        t = wx.TextCtrl(sb, name='device_name', size=self.txtSize30)
        t.Enable(False)
        fgs.Add(t, 0, lflags)

        # mfg date
        fgs.Add(wx.StaticText(sb, label='Mfg Date:'), 0, rflags)
        t = wx.TextCtrl(sb, name='mfg_date', size=self.txtSize10)
        t.Enable(False)
        fgs.Add(t, 0, lflags)

        # version
        fgs.Add(wx.StaticText(sb, label='Version:'), 0, rflags)
        t = wx.TextCtrl(sb, name='version', size=self.txtSize4)
        t.Enable(False)
        fgs.Add(t, 0, lflags)

    def deviceStatusLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 3, *defaultBorder)

        sb = wx.StaticBox(panel, label='Status')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        cf_en_svg = os.path.join(base_path, 'img', 'chg_fet_enabled.svg')
        cf_dis_svg = os.path.join(base_path, 'img', 'chg_fet_disabled.svg')
        df_en_svg = os.path.join(base_path, 'img', 'dsg_fet_enabled.svg')
        df_dis_svg = os.path.join(base_path, 'img', 'dsg_fet_disabled.svg')

        chg_fet_img = BoolImage(sb, cf_en_svg, cf_dis_svg, 'chg_fet_status_img')
        dsg_fet_img = BoolImage(sb, df_en_svg, df_dis_svg, 'dsg_fet_status_img')

        bsh = wx.BoxSizer()
        sbs.Add(bsh, 1, wx.EXPAND)

        bsv1 = wx.BoxSizer(wx.VERTICAL)
        bsv2 = wx.BoxSizer(wx.VERTICAL)
        bsh.Add(bsv1, 8, wx.EXPAND | wx.ALL, 3)
        bsh.AddStretchSpacer(2)
        bsh.Add(bsv2, 8, wx.EXPAND | wx.ALL, 3)

        bsg = wx.BoxSizer()
        bsg.AddStretchSpacer(1)
        bsg.Add(chg_fet_img, 5,  wx.EXPAND)
        bsg.AddStretchSpacer(1)
        bsv1.Add(bsg, 1, wx.EXPAND)
        bst = wx.BoxSizer()
        bsv1.Add(bst, 1, wx.ALIGN_CENTER_HORIZONTAL)
        bst.Add(wx.StaticText(sb, label='Charge FET:'), 0)
        bst.Add(wx.StaticText(sb, label='ENABLED', name='chg_fet_status_txt'), 0)

        bsg = wx.BoxSizer()
        bsg.AddStretchSpacer(1)
        bsg.Add(dsg_fet_img, 5,  wx.EXPAND)
        bsg.AddStretchSpacer(1)
        bsv2.Add(bsg, 1, wx.EXPAND)
        bst = wx.BoxSizer()
        bsv2.Add(bst, 1, wx.ALIGN_CENTER_HORIZONTAL)
        bst.Add(wx.StaticText(sb, label='Discharge FET:'), 0)
        bst.Add(wx.StaticText(sb, label='ENABLED', name='dsg_fet_status_txt'), 0)

        ok_svg = os.path.join(base_path, 'img', 'ok.svg')
        err_svg = os.path.join(base_path, 'img', 'err.svg')

        # error flags
        gbs = wx.GridBagSizer(3,3)
        sbs.Add(gbs, 1, *defaultBorder)

        class Gen:
            size = (self.txtSize8[1], self.txtSize8[1])
            def __init__(self, l):
                self.row = 0
                self.col = 0
                self.cols = 11
                self.l = l

            def incLine(self):
                self.row += 1
                self.col = 0

            def __call__(self, label, img1, img2, fn):
                bi = BoolImage(sb, img1, img2, fn)
                bi.SetMinSize(self.size)
                bi.SetValue(False)
                txt = wx.StaticText(sb, label = label + ':', name = f'label_{fn}')
                gbs.Add(txt, (self.row, self.col), flag = rflags)
                self.col += 1
                gbs.Add(bi, (self.row, self.col), flag = rflags)
                self.col += 1

                if self.col == self.cols:
                    self.incLine()
                else:
                    gbs.Add(*self.l.txtSize2,(self.row, self.col))
                    self.col += 1

        gen = Gen(self)
        gen('COVP', err_svg, ok_svg, 'covp_err')
        gen('CUVP', err_svg, ok_svg, 'cuvp_err')
        gen('POVP', err_svg, ok_svg, 'povp_err')
        gen('PUVP', err_svg, ok_svg, 'puvp_err')
        gen('CHGOT', err_svg, ok_svg, 'chgot_err')
        gen('CHGUT', err_svg, ok_svg, 'chgut_err')
        gen('DSGOT', err_svg, ok_svg, 'dsgot_err')
        gen('DSGUT', err_svg, ok_svg, 'dsgut_err')
        gen('CHGOC', err_svg, ok_svg, 'chgoc_err')
        gen('DSGOC', err_svg, ok_svg, 'dsgoc_err')
        gen.incLine()
        gen('Short', err_svg, ok_svg, 'sc_err')
        gen.incLine()
        gen('AFE', err_svg, ok_svg, 'afe_err')
        gen('SW Lock', err_svg, ok_svg, 'software_err')

    ####
    ##### Settings tab methods 
    ####

    def settingsTabLayout(self, tab):
        vbox = wx.BoxSizer(wx.VERTICAL)
        tab.SetSizer(vbox)

        hbox  = wx.BoxSizer(wx.HORIZONTAL)
        vbox.Add(hbox)
        col1Sizer = wx.BoxSizer(wx.VERTICAL)
        col2Sizer = wx.FlexGridSizer(1)
        col3Sizer = wx.FlexGridSizer(1)
        hbox.AddMany([col1Sizer, col2Sizer, col3Sizer])

        self.basicConfigLayout(tab, col1Sizer, colGap, boxGap)
        self.highProtectConfigLayout(tab, col1Sizer, colGap, boxGap)
        self.functionConfigLayout(tab, col2Sizer, colGap, boxGap)
        self.ntcConfigLayout(tab, col2Sizer, colGap, boxGap)
        self.balanceConfigLayout(tab, col2Sizer, colGap, boxGap)
        self.otherConfigLayout(tab, col2Sizer, colGap, boxGap)
        self.capacityConfigLayout(tab, col3Sizer, colGap, boxGap)
        self.faultCountsLayout(tab, col3Sizer, colGap, boxGap)

        hbox  = wx.BoxSizer(wx.HORIZONTAL)
        vbox.Add(hbox, 1, wx.EXPAND)
        self.controlConfigLayout(tab, hbox, colGap, boxGap)

        tab.Layout()
        tab.Fit()

    def basicConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)

        sb = wx.StaticBox(panel, label='Basic Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(11, gap=boxGap)
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 0, *defaultBorder)

        def gen(fn, unit1, unit2 = None, unit3 = 's', spacing=10, digits = 0):
            unit2 = unit2 or unit1
            fn_rel = fn + '_rel'
            fn_delay = fn + '_delay'

            c1 = wx.SpinCtrlDouble(sb, name = fn)
            c2 = wx.SpinCtrlDouble(sb, name = fn_rel)
            c3 = wx.SpinCtrlDouble(sb, name = fn_delay)
            c1.SetDigits(digits)
            c2.SetDigits(digits)

            items = [
                (wx.StaticText(sb, label = fn.upper(), name = f'label_{fn}'), 0, rflags),
                (c1, 0, lflags),
                (wx.StaticText(sb, label = unit1), 0, lflags),
                colGap,
                (wx.StaticText(sb, label = 'Rel', name = f'label_{fn_rel}'), 0, rflags),
                (c2, 0, lflags),
                (wx.StaticText(sb, label = unit2), 0, lflags),
                colGap,
                (wx.StaticText(sb, label = 'Delay', name = f'label_{fn_delay}'), 0, rflags),
                (c3, 0, lflags),
                (wx.StaticText(sb, label = unit3), 0, lflags),
            ]
            return items

        fgs.AddMany(gen('covp', 'mV'))
        fgs.AddMany(gen('cuvp', 'mV'))
        fgs.AddMany(gen('povp', 'mV'))
        fgs.AddMany(gen('puvp', 'mV'))
        fgs.AddMany(gen('chgot', 'C', digits = 1))
        fgs.AddMany(gen('chgut', 'C', digits = 1))
        fgs.AddMany(gen('dsgot', 'C', digits = 1))
        fgs.AddMany(gen('dsgut', 'C', digits = 1))
        fgs.AddMany(gen('chgoc', 'mA', 's'))
        fgs.AddMany(gen('dsgoc', 'mA', 's'))

        fgs.Fit(panel)

    def highProtectConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='High Protection Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(5, gap=boxGap)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)
        
        fgs.AddGrowableCol(2)
        a = wx.ALIGN_CENTER_VERTICAL
        sbs.Add(wx.CheckBox(sb, label='2X OC and SC values', name = 'sc_dsgoc_x2'))
        sbs.Add(fgs, 0, *defaultBorder)
        # DSGOC2
        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()

        s1.AddMany([
            (EnumChoice(sb, choices = jbd.Dsgoc2Enum, name='dsgoc2'), 0, a),
            (wx.StaticText(sb, label = 'mV'), 0, a),
        ])
        s2.AddMany([ 
                (EnumChoice(sb, choices = jbd.Dsgoc2DelayEnum, name='dsgoc2_delay'), 0, a),
                (wx.StaticText(sb, label = 'ms'), 0, a),
        ])
        

        fgs.AddMany([
            (wx.StaticText(sb, label = 'DSGOC2', name = 'label_dsgoc2'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Delay', name = 'label_dsgoc2_delay'), 0, a), (s2,)
            ])

        # SC value / delay
        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()
        s1.AddMany([     
                (EnumChoice(sb, choices = jbd.ScEnum, name = 'sc'), 0, a),
                (wx.StaticText(sb, label = 'mV'), 0, a)
        ])
        s2.AddMany([ 
                (EnumChoice(sb, choices = jbd.ScDelayEnum, name = 'sc_delay'), 0, a),
                (wx.StaticText(sb, label = 'µs'), 0, a)
        ])

        fgs.AddMany([
            (wx.StaticText(sb, label = 'SC Value', name = 'label_sc'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Delay', name = 'label_sc_delay'), 0, a), (s2,)
            ])

        # COVP High
        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()
        s1.AddMany([
                (wx.SpinCtrlDouble(sb, name = 'covp_high'), 0, a),
                (wx.StaticText(sb, label = 'mV'), 0, a),
        ])
        s2.AddMany([
                (EnumChoice(sb, choices = jbd.CovpHighDelayEnum, name = 'covp_high_delay'), 0, a),
                (wx.StaticText(sb, label = 's'), 0, a),
        ])

        fgs.AddMany([
            (wx.StaticText(sb, label = 'COVP High', name = 'label_covp_high'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Delay', name = 'label_covp_high_delay'), 0, a), (s2,)
            ])

        # CUVP High
        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()
        s1.AddMany([
                (wx.SpinCtrlDouble(sb, name = 'cuvp_high'), 0, a),
                (wx.StaticText(sb, label = 'mV'), 0, a),
        ])
        s2.AddMany([
                (EnumChoice(sb, choices = jbd.CuvpHighDelayEnum, name = 'cuvp_high_delay'), 0, a),
                (wx.StaticText(sb, label = 's'), 0, a),
        ])
        fgs.AddMany([
            (wx.StaticText(sb, label = 'CUVP High', name = 'label_cuvp_high'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Delay', name = 'label_cuvp_high_delay'), 0, a), (s2,)
            ])

        # SC Release
        s1 = wx.BoxSizer()
        s1.AddMany([
                (BetterChoice(sb, choices = [str(i) for i in range(256)], name = 'sc_rel'), 0, lflags),
                (wx.StaticText(sb, label = 's'), 0, lflags),
        ])
        fgs.AddMany([
            (wx.StaticText(sb, label = 'SC Rel', name = f'label_sc_rel'), 0, a), (s1,), 
            ])

    def functionConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Function Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(3, gap=boxGap)
        sbs.Add(fgs, 1, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        fgs.AddMany([
            (wx.CheckBox(sb, name='switch', label='Switch'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='scrl', label='SC Rel'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='balance_en', label='Bal En'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='led_en', label='LED En'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='led_num', label='LED Num'),0, wx.EXPAND),
            (wx.CheckBox(sb, name='chg_balance_en', label='Chg Bal En'),0, wx.EXPAND),
        ])
        for c in range(fgs.Cols):
            fgs.AddGrowableCol(c)

    def ntcConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='NTC Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(4, gap=boxGap)
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        fgs.AddMany([
            (wx.CheckBox(sb, name=f'ntc{i}', label=f'NTC{i}'),) for i in range(1,9)
        ])
        for c in range(fgs.Cols):
            fgs.AddGrowableCol(c)

    def balanceConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Balance Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(3, gap=boxGap)
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        fgs.AddMany([
            (wx.StaticText(sb, label='Start Voltage'), 0, rflags),
            (wx.SpinCtrlDouble(sb, name='bal_start'), 0, lflags),
            (wx.StaticText(sb, label='mV'), 0, lflags),

            (wx.StaticText(sb, label='Balance Window'), 0, rflags),
            (wx.SpinCtrlDouble(sb, name='bal_window'), 0, lflags),
            (wx.StaticText(sb, label='mV'), 0, lflags),
        ])

    def otherConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Other Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(5, gap=boxGap)
        fgs.AddGrowableCol(2)
        a = wx.ALIGN_CENTER_VERTICAL
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()

        sr = wx.SpinCtrlDouble(sb, name='shunt_res')
        sr.SetDigits(1)
        sr.SetIncrement(0.1)
        s1.AddMany([
            (sr, 0, a),
            (wx.StaticText(sb, label = 'mΩ'), 0, a),
        ])
        s2.AddMany([ 
                (BetterChoice(sb, choices = [str(i) for i in range(1,33)], name='cell_cnt'), 0, a),
        ])
        fgs.AddMany([
            (wx.StaticText(sb, label = 'Shunt res'), 0, a | wx.ALIGN_RIGHT), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Cell cnt'), 0, a | wx.ALIGN_RIGHT), (s2,)
            ])

        s1 = wx.BoxSizer()
        s2 = wx.BoxSizer()

        s1.AddMany([
            (wx.SpinCtrlDouble(sb, name='cycle_cnt'), 0, a),
        ])
        s2.AddMany([ 
            (wx.TextCtrl(sb, name='serial_num', size=self.txtSize6), 0, a),
        ])
        fgs.AddMany([
            (wx.StaticText(sb, label = 'Cycle cnt'), 0, a), (s1,), 
            (0,0),
            (wx.StaticText(sb, label = 'Serial num'), 0, a), (s2,)
            ])


        fgs = wx.FlexGridSizer(2, gap=boxGap)
        sbs.Add(fgs, 0, *defaultBorder)

        d = wx.BoxSizer()
        year = wx.TextCtrl(sb, name='year', size=self.txtSize4)
        month = wx.TextCtrl(sb, name='month', size=self.txtSize2)
        day = wx.TextCtrl(sb, name='day', size=self.txtSize2)
        year.SetMaxLength(4)
        month.SetMaxLength(2)
        day.SetMaxLength(2)
        d.AddMany([
            (year, 0, a),
            (wx.StaticText(sb,label='-'), 0, a),
            (month, 0, a),
            (wx.StaticText(sb,label='-'), 0, a),
            (day, 0, a),
        ])

        mfg_name = wx.TextCtrl(sb, name='mfg_name', size=self.txtSize31)
        device_name = wx.TextCtrl(sb, name='device_name', size=self.txtSize31)
        barcode = wx.TextCtrl(sb, name='barcode', size=self.txtSize31)
        for c in (mfg_name, device_name, barcode):
            c.SetMaxLength(31)

        fgs.AddMany([
            (wx.StaticText(sb, label='Mfg Name'), 0, a),
            (mfg_name, 0, a),

            (wx.StaticText(sb, label='Device Name'), 0, a),
            (device_name, 0, a),

            (wx.StaticText(sb, label='Mfg Date'), 0, a),
            d,

            (wx.StaticText(sb, label='Barcode'), 0, a),
            (barcode, 0, a),
        ])

    def controlConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Control')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        bs = wx.BoxSizer()
        a = wx.ALIGN_CENTER_VERTICAL
        #sbs.Add(bs, 1, *defaultBorder)
        sbs.Add(bs, 1, wx.EXPAND)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        read_btn = wx.Button(sb, label='Read settings From BMS', name='read_eeprom_btn')
        write_btn = wx.Button(sb, label='Write settings to BMS', name='write_eeprom_btn')
        load_btn = wx.Button(sb, label='Load settings from file', name='load_eeprom_btn')
        save_btn = wx.Button(sb, label='Save settings to file', name='save_eeprom_btn')
        write_btn.Enable(False)
        save_btn.Enable(False)



        #batt_svg.SetMinSize((20,20))
        box = wx.FlexGridSizer(11)
        #bs.Add(box, 1, wx.EXPAND)
        bs.Add(box)

        box.Add(SVGImage(sb, os.path.join(base_path, 'img', 'battery_icon_h.svg')), 1 , wx.EXPAND)
        box.Add(5,1)
        box.Add(SVGImage(sb, os.path.join(base_path, 'img', 'arrow_right.svg')), 1, wx.EXPAND)
        box.Add(5,1)
        box.Add(read_btn, 1, wx.EXPAND)

        box.Add(15,1)

        box.Add(write_btn, 1, wx.EXPAND)
        box.Add(5,1)
        box.Add(SVGImage(sb, os.path.join(base_path, 'img', 'arrow_right.svg')), 1, wx.EXPAND)
        box.Add(5,1)
        box.Add(SVGImage(sb, os.path.join(base_path, 'img', 'battery_icon_h.svg')), 1 , wx.EXPAND)

        bs.AddStretchSpacer()

        box = wx.FlexGridSizer(11)
        bs.Add(box)
        box.Add(SVGImage(sb, os.path.join(base_path, 'img', 'floppy.svg')), 1, wx.EXPAND)
        box.Add(5,1)
        box.Add(SVGImage(sb, os.path.join(base_path, 'img', 'arrow_right.svg')), 1, wx.EXPAND)
        box.Add(5,1)
        box.Add(load_btn, 1, wx.EXPAND)

        box.Add(15,1)

        box.Add(save_btn, 1, wx.EXPAND)
        box.Add(5,1)
        box.Add(SVGImage(sb, os.path.join(base_path, 'img', 'arrow_right.svg')), 1, wx.EXPAND)
        box.Add(5,1)
        box.Add(SVGImage(sb, os.path.join(base_path, 'img', 'floppy.svg')), 1, wx.EXPAND)

    def capacityConfigLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Capacity Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(3, gap=boxGap)
        fgs.AddGrowableCol(2)
        a = wx.ALIGN_CENTER_VERTICAL
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        def gen(label, fn, unit, digits = 0):
            c = wx.SpinCtrlDouble(sb, name = fn)
            c.SetDigits(digits)
            c.SetIncrement(10 ** -digits)
            items = [
                (wx.StaticText(sb, label = label), 0, rflags),
                (c, 0, lflags),
                (wx.StaticText(sb, label = unit), 0, lflags),
            ]
            return items

        fgs.AddMany(gen('Design Cap', 'design_cap', 'mAh'))
        fgs.AddMany(gen('Cycle Cap', 'cycle_cap', 'mAh'))
        fgs.AddMany(gen('Cell 100%', 'cap_100', 'mV'))
        fgs.AddMany(gen('Cell 80%', 'cap_80', 'mV'))
        fgs.AddMany(gen('Cell 60%', 'cap_60', 'mV'))
        fgs.AddMany(gen('Cell 40%', 'cap_40', 'mV'))
        fgs.AddMany(gen('Cell 20%', 'cap_20', 'mV'))
        fgs.AddMany(gen('Cell 0%', 'cap_0', 'mV'))
        fgs.AddMany(gen('Dsg Rate', 'dsg_rate', '%', 1))
        fgs.AddMany(gen('FET ctrl', 'fet_ctrl', 's'))
        fgs.AddMany(gen('LED timer', 'led_timer', 's'))

    def faultCountsLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sb = wx.StaticBox(panel, label='Fault Counts')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        fgs = wx.FlexGridSizer(4, gap=boxGap)
        fgs.AddGrowableCol(2)
        a = wx.ALIGN_CENTER_VERTICAL
        sbs.Add(fgs, 0, *defaultBorder)
        panel.SetSizer(sbs)
        sizer.Add(panel, 1, *defaultBorder)

        def gen(label1, field1, label2 = None, field2 = None):
            items = [
                (wx.StaticText(sb, label = label1+':', name = f'label_{field1}'), 0, rflags),
                (wx.StaticText(sb, name = field1, label='----'), 0, lflags)
            ]
            if field2:
                items += [
                (wx.StaticText(sb, label = label2+':', name = f'label_{field2}'), 0, rflags),
                (wx.StaticText(sb, name = field2, label='----'), 0, lflags),
            ]
            return items

        fgs.AddMany(gen('CHGOC', 'chgoc_err_cnt', 'DSGOC', 'dsgoc_err_cnt'))
        fgs.AddMany(gen('CHGOT', 'chgot_err_cnt', 'CHGUT', 'chgut_err_cnt'))
        fgs.AddMany(gen('DSGOT', 'dsgot_err_cnt', 'DSGUT', 'dsgut_err_cnt'))
        fgs.AddMany(gen('POVP',  'povp_err_cnt',  'PUVP',  'puvp_err_cnt'))
        fgs.AddMany(gen('COVP',  'covp_err_cnt',  'CUVP',  'cuvp_err_cnt'))
        fgs.AddMany(gen('SC',    'sc_err_cnt'))
        fgs.Add(wx.Button(sb, label='Clear', name='clear_errors_btn'))

    ####
    ##### Calibration tab methods 
    ####

    def calTabLayout(self, tab):
        vsizer  = wx.BoxSizer(wx.VERTICAL)
        tab.SetSizer(vsizer)
        self.voltCalLayout(tab, vsizer, colGap, boxGap)
        self.ampCalLayout(tab, vsizer, colGap, boxGap)
        self.miscCalLayout(tab, vsizer, colGap, boxGap)

        tab.Layout()
        tab.Fit()

    def voltCalLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 0, *defaultBorder)

        sb = wx.StaticBox(panel, label='Voltage and Temperature Calibration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        gbs = wx.GridBagSizer(5,5)
        sbs.Add(gbs, 1, *defaultBorder)

        def gen_cell(index):
            cell_label = wx.StaticText(sb, label=f'Cell {index + 1}')
            cell_read = wx.TextCtrl(sb, value='0', name=f'cell_read{i}', size=self.txtSize4)
            cell_act = wx.TextCtrl(sb, value='', name=f'cell_act{i}', size=self.txtSize4)
            cell_ma = wx.StaticText(sb, label=f'mV')
            cell_read.Enable(False)
            return cell_label, cell_read, cell_act, cell_ma

        def gen_ntc(index):
            ntc_label = wx.StaticText(sb, label=f'NTC {index + 1}')
            ntc_read = wx.TextCtrl(sb, value='0', name=f'ntc_read{i}', size=self.txtSize4)
            ntc_act = wx.TextCtrl(sb, value='', name=f'ntc_act{i}', size=self.txtSize4)
            ntc_read.Enable(False)
            ntc_c = wx.StaticText(sb, label=f'C')
            return ntc_label, ntc_read, ntc_act, ntc_c


        for i in range(32):
            col = i // 8 * 5
            row = i % 8
            for j, item in enumerate(gen_cell(i)):
                gbs.Add(item, wx.GBPosition(row, col + j), flag = wx.ALIGN_CENTER_VERTICAL)

        for i in range(8):
            col = 21 
            row = i
            for j, item in enumerate(gen_ntc(i)):
                gbs.Add(item, wx.GBPosition(row, col + j), flag = wx.ALIGN_CENTER_VERTICAL)
        
        for i in range(4):
            gbs.AddGrowableCol((i+1) * 5 - 1)

        vbs = wx.BoxSizer(wx.VERTICAL)
        sbs.Add(vbs, 0, *defaultBorder)
        vbs.Add(wx.Button(sb, label='Calibrate', name='cal_volt_ntc_btn'), 0, wx.ALIGN_CENTER_HORIZONTAL)

    def ampCalLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 0, *defaultBorder)

        sb = wx.StaticBox(panel, label='Ampere Calibration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)
        
        hbs = wx.BoxSizer(wx.HORIZONTAL)
        sbs.Add(hbs, 0, *defaultBorder)
        t = wx.TextCtrl(sb, name='pack_ma', size=self.txtSize6, style=wx.TE_RIGHT)
        t.Enable(False)
        hbs.Add(t, 0, lflags)
        hbs.AddSpacer(4)
        hbs.Add(wx.StaticText(sb, label = 'mA'), 0, lflags)
        hbs.AddSpacer(10)
        hbs.Add(wx.Button(sb, label='Idle Calibration', name='cal_idle_btn'), 0)
        hbs.AddSpacer(10)
        hbs.Add(wx.TextCtrl(sb, value='', name=f'chg_ma', size=self.txtSize5), 0)
        hbs.AddSpacer(4)
        hbs.Add(wx.Button(sb, label='Charge Calibration', name='cal_chg_btn'), 0)
        hbs.AddSpacer(10)
        hbs.Add(wx.TextCtrl(sb, value='', name=f'dsg_ma', size=self.txtSize5), 0)
        hbs.AddSpacer(4)
        hbs.Add(wx.Button(sb, label='Discharge Calibration', name='cal_dsg_btn'), 0)

    def miscCalLayout(self, parent, sizer, colGap, boxGap):
        panel = wx.Panel(parent)
        sizer.Add(panel, 0, *defaultBorder)

        sb = wx.StaticBox(panel, label='Miscellaneous')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)
        panel.SetSizer(sbs)

        gbs = wx.GridBagSizer(2,2)
        sbs.Add(gbs)

        row = 0
        hbs = wx.BoxSizer(wx.HORIZONTAL)
        gbs.Add(wx.StaticText(sb, label = 'FET Control:'), wx.GBPosition(row,0), flag = rflags)
        gbs.Add(hbs, wx.GBPosition(row,1))
        cb = wx.CheckBox(sb, label='Charge Enable', name='chg_enable')
        cb.SetValue(True)
        hbs.Add(cb, 0, lflags)
        hbs.AddSpacer(10)
        cb = wx.CheckBox(sb, label='Discharge Enable', name='dsg_enable')
        cb.SetValue(True)
        hbs.Add(cb, 0, lflags)
        hbs.AddSpacer(20)
        hbs.Add(wx.Button(sb, label='Set', name='chg_dsg_enable_btn'))
        hbs.AddSpacer(20)
        hbs.Add(wx.StaticText(sb, label = 'Note: The state of the FET Control cannot be queried; these checkboxes do not represent the state.'), 0, lflags)

        row += 1
        row += 1
        hbs = wx.BoxSizer(wx.HORIZONTAL)
        gbs.Add(wx.StaticText(sb, label = 'Balance Testing:'), wx.GBPosition(row,0), flag = rflags)
        gbs.Add(hbs, wx.GBPosition(row,1))
        hbs.Add(wx.Button(sb, label='Open Odd Bal', name='open_odd_bal_btn'))
        hbs.Add(wx.Button(sb, label='Open Even Bal', name='open_even_bal_btn'))
        hbs.Add(wx.Button(sb, label='Close All Bal', name='close_all_bal_btn'))
        hbs.Add(wx.Button(sb, label='Exit', name='exit_bal_btn'))

        row += 1
        row += 1
        hbs = wx.BoxSizer(wx.HORIZONTAL)
        hbs = wx.BoxSizer(wx.HORIZONTAL)
        gbs.Add(wx.StaticText(sb, label = 'Set remaining capacity:'), wx.GBPosition(row,0), flag = rflags)
        gbs.Add(hbs, wx.GBPosition(row,1))
        hbs.Add(wx.TextCtrl(sb, value='', name=f'set_pack_cap_rem', size=self.txtSize5), 0)
        hbs.Add(wx.Button(sb, label='Set', name='set_pack_cap_rem_btn'))
        hbs.AddSpacer(20)
        hbs.Add(wx.Button(sb, label='Clear Password', name = 'clear_password_btn'))
 
class RoundGauge(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer)
        self.width = 15
        self.value = 0
        self.SetRange(0, 100)
        self.SetArc(135, 405)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.SetDoubleBuffered(True)
        self.font = wx.Font(kwargs.get('font_size', 12), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        self.bgColor = '#707070'
        self.fgColor = '#20d020'
        self.valueSuffix = '%'
        self.SetTransparent(0)

    def onTimer(self, event):
        # smooooooooove
        cutoff = (self.max - self.min) / 500
        delta = self.targetValue - self.value
        step = math.copysign(max(cutoff, abs(delta) *.08), delta)
        if abs(delta) < cutoff:
            self.value = self.targetValue
            self.timer.Stop()
        else:
            self.value += math.copysign(step, delta)
        self.Refresh()

    def SetArc(self, start, end):
        self.arcStart = start
        self.arcEnd = end

    def SetRange(self, min, max):
        self.min = min
        self.max = max
        self.SetValue(self.value) # for range checking
        self.Refresh()

    def SetValue(self, val):
        val = int(val)
        self.targetValue = val
        self.targetValue = max(self.min, self.targetValue)
        self.targetValue = min(self.max, self.targetValue)
        self.timer.Start(5)
        self.Refresh()

    def SetWidth(self):
        self.width = width

    def OnPaint(self, event=None):
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(wx.WHITE, wx.TRANSPARENT))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        self.Draw(gc)

    def Draw(self, gc):
        size = gc.GetSize()

        center = [i//2 for i in size]
        radius = min(size)//2 - self.width//1.8

        # background
        radStart = math.radians(self.arcStart)
        radEnd = math.radians(self.arcEnd)
        path = gc.CreatePath()
        path.AddArc(*center, radius, radStart, radEnd, True)
        pen = wx.Pen(self.bgColor, self.width)
        pen.SetCap(wx.CAP_BUTT)
        gc.SetPen(pen)
        gc.SetBrush(wx.Brush('#000000', wx.TRANSPARENT))
        gc.DrawPath(path)

        #progress bar
        pct = self.value / (self.max - self.min)
        end = (self.arcEnd - self.arcStart) * pct + self.arcStart
        start = math.radians(self.arcStart)
        end = math.radians(end)
        path = gc.CreatePath()
        path.AddArc(*center, radius, start, end, True)
        pen = wx.Pen(self.fgColor, self.width)
        pen.SetCap(wx.CAP_BUTT)
        gc.SetPen(pen)
        gc.SetBrush(wx.Brush('#000000', wx.TRANSPARENT))
        gc.DrawPath(path)

        #text

        gc.SetFont(self.font, '#000000')
        s = str(int(self.value)) + self.valueSuffix
        w,h = self.GetTextExtent(s)
        x,y = center[0] - w // 2, center[1] - h // 2

        gc.DrawText(s, x,y)

class ChildIter:
    ignoredNames = {
        'staticText', 
        'panel', 
        'GridWindow', 
        'SvgImage', 
        'text', 
        'wxSpinButton',
        'groupBox', 
        'scrolledpanel',
        }
    ignoredRE = [
        re.compile(r'^.*?_btn$')
    ]

    class Brk(Exception): pass

    @classmethod
    def iter(cls, w):
        for c in w.GetChildren():
            yield c
            yield from cls.iter(c)

    @classmethod
    def iterNamed(cls, w):
        for c in cls.iter(w):
            try:
                if c.Name in cls.ignoredNames: raise cls.Brk()
                for r in cls.ignoredRE:
                    if r.match(c.Name): raise cls.Brk()
                yield c
            except cls.Brk:
                pass

class Main(wx.Frame):
    ntc_RE = re.compile(r'ntc\d+')
    def __init__(self, *args, **kwargs):
        self.icon = kwargs.pop('icon', None)
        cli_args = kwargs.pop('cli_args', None)
        kwargs['style'] = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        wx.Frame.__init__(self, *args, **kwargs)
        self.sys_stdout = sys.stdout
        self.sys_stderr = sys.stderr

        self.logger = None

        # plugins
        self.loadPlugins()

        # debug window
        self.debugWindow = DebugWindow(self, title=f'{appName} debug window')
        self.Bind(DebugWindow.EVT_TEXTFRAME_CLOSE, self.onDebugWindowClose)
        if cli_args and cli_args.open_debug:
            self.debugWindow.Show()

        if self.icon: 
            self.SetIcon(self.icon)
            self.debugWindow.SetIcon(self.icon)

        if not cli_args or not cli_args.no_redirect:
            sys.stdout = WriteRedirect(self, TextDataType.STDOUT)
            
        self.Bind(WriteRedirect.EVT_TEXT, self.onText)
        print(f'Welcome to {appNameWithVersion}\n')
        if cli_args.clear_config:
            print('deleting config info')
            config = wx.Config.Get()
            config.DeleteAll()
            config.Flush()


        if cli_args.port:
            port = serial.Serial(cli_args.port)
        else:
            port = self.getLastSerialPort()
        print(f'Using port: {port.name or "None"} {repr(port)}')
        self.j = jbd.JBD(port)
        self.accessLock = LockClass()
        self.worker = BkgWorker(self, self.j)

        font = wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.SetFont(font)


        # menu
        self.menuBar = wx.MenuBar()
        self.fileMenu = wx.Menu()
        self.pluginMenu = wx.Menu()
        self.debugWindowItem = self.fileMenu.Append(wx.ID_ANY, 'Debug Window', 'Show debug window', kind = wx.ITEM_CHECK)
        self.aboutItem = self.fileMenu.Append(wx.ID_ABOUT, 'About', f'About {appName}')
        self.websiteItem = self.fileMenu.Append(wx.ID_ANY, f'{appName} website', f'{appName} website')

        for n,m in self.plugins.items():
            try:
                cls = getattr(m, 'plugin_class', None)
                if cls is None:
                    raise PluginException(f'plugin "{n}" is missing "plugin_class" attribute')
                menu_name = getattr(cls, 'menu_name', None)
                if menu_name is None:
                    raise PluginException(f'plugin "{n}" class "{cls.__name__}" is missing "menu_name" attribute')
                menuItem = self.pluginMenu.Append(wx.ID_ANY, menu_name, menu_name)
                opener = functools.partial(self.pluginOpenHandler, cls)
                self.Bind(wx.EVT_MENU, opener, menuItem)
            except PluginException:
                print(f'plugin "{n}" failed to initialize:', file = sys.stderr)
                traceback.print_exc()

        self.quitItem = self.fileMenu.Append(wx.ID_ANY, 'Quit')
        self.menuBar.Append(self.fileMenu, '&File')
        if self.pluginMenu.GetMenuItemCount():
            self.menuBar.Append(self.pluginMenu, '&Plugins')
        self.SetMenuBar(self.menuBar)
        self.Bind(wx.EVT_MENU, self.onDebugWindowToggle, self.debugWindowItem)
        self.Bind(wx.EVT_MENU, self.onWebsite, self.websiteItem)
        self.Bind(wx.EVT_MENU, self.onAbout, self.aboutItem)
        self.Bind(wx.EVT_MENU, self.onQuit, self.quitItem)

        layout = LayoutGen(self)

        # tabs layout
        nb_panel = wx.Panel(self)

        nb = wx.Notebook(nb_panel)
        self.infoTab = wx.Panel(nb, name = 'info')
        self.settingsTab = wx.Panel(nb, name='settings')
        self.calTab = wx.Panel(nb, name = 'cal')

        layout.infoTabLayout(self.infoTab)
        layout.settingsTabLayout(self.settingsTab)
        layout.calTabLayout(self.calTab)

        nb.AddPage(self.infoTab, 'Info')
        nb.AddPage(self.settingsTab, 'Settings')
        nb.AddPage(self.calTab, 'Calibration && Misc')

        for c in ChildIter.iterNamed(self.settingsTab):
            c.Name = 'eeprom_' + c.Name

        for c in ChildIter.iterNamed(self.infoTab):
            c.Name = 'info_' + c.Name

        for c in ChildIter.iterNamed(self.calTab):
            c.Name = 'cal_' + c.Name
        
        # apply field annotations

        children_by_name = {c.Name:c for c in ChildIter.iterNamed(self)}
        children_by_label = {c.GetLabel() for c in children_by_name.values()}
        for fa in field_annotations:
            for prefix in ('eeprom_', 'eeprom_label_', 'info_', 'info_label_'):
                fieldName = prefix+fa.fieldName
                field = self.FindWindowByName(fieldName)
                if not field: 
                    continue

                if fa.tooltip:
                    field.SetToolTip(fa.tooltip)

                if fa.range:
                    try:
                        min, max, increment = fa.range
                        field.SetRange(min, max)
                        field.SetIncrement(increment)
                    except Exception as e:
                        print(f'unable to call SetRange on {fieldName}')

        nb_sizer = wx.BoxSizer()
        nb_sizer.Add(nb, 1, wx.EXPAND | wx.ALL, 5)
        nb_panel.SetSizer(nb_sizer)

        # self layout

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(nb_panel, 1, wx.EXPAND)
        self.SetSizer(sizer)

        bot_sizer = wx.BoxSizer()
        serialButton = wx.Button(self, label='Serial', name = 'serial_btn')
        self.startStopScanButton = wx.Button(self, label='Start Scan', name = 'start_stop_scan_btn')
        self.startStopLogButton = wx.Button(self, label='Start Log', name = 'start_stop_log_btn')
        self.progressGauge = wx.Gauge(self)
        self.statusText = PulseText(self)
        bot_sizer.AddSpacer(5)
        bot_sizer.Add(serialButton)
        bot_sizer.AddSpacer(10)
        bot_sizer.Add(self.startStopScanButton)
        bot_sizer.AddSpacer(10)
        bot_sizer.Add(self.startStopLogButton )
        bot_sizer.AddSpacer(10)
        bot_sizer.Add(self.statusText, 0, lflags)
        bot_sizer.Add(self.progressGauge, 1 , wx.EXPAND | wx.LEFT, 20)
        sizer.Add(bot_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.Bind(BkgWorker.EVT_EEP_PROG, self.onProgress)
        self.Bind(BkgWorker.EVT_EEP_DONE, self.onEepromDone)
        self.Bind(BkgWorker.EVT_SCAN_DATA, self.onScanData)
        self.Bind(BkgWorker.EVT_CAL_DONE, self.onCalDone)
        self.Bind(wx.EVT_BUTTON, self.onButtonClick)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.updateSerialPort()

        # ---

        def sizeFix(event):
            # https://trac.wxwidgets.org/ticket/16088#comment:4
            win = event.GetEventObject()
            win.GetSizer().SetSizeHints(self)
            win.Bind(wx.EVT_SHOW, None)

        self.Bind(wx.EVT_SHOW, sizeFix)

        # do this last to catch errors on the CLI
        if not cli_args or not cli_args.no_redirect:
            sys.stderr = WriteRedirect(self, TextDataType.STDERR)

        if cli_args and cli_args.tab:
            for i in range(nb.GetPageCount()):
                p = nb.GetPage(i)
                if p.Name == cli_args.tab:
                    nb.SetSelection(i)
                    break
        if cli_args and cli_args.plugin:
            for pluginName, plugin in self.plugins.items():
                print(plugin.plugin_short_name.lower(), 'vs', cli_args.plugin.lower())
                if plugin.plugin_short_name.lower() == cli_args.plugin.lower():
                    self.openPlugin(plugin.plugin_class)


    def openPlugin(self, pluginClass): 
        for i in self.pluginsOpen:
            if isinstance(i, pluginClass):
                i.SetFocus()
                return
        obj = pluginClass(self)
        self.pluginsOpen.add(obj)
        obj.Bind(wx.EVT_CLOSE, self.pluginCloseHandler)
        obj.Show();

    def pluginOpenHandler(self, pluginClass, evt):
        self.openPlugin(pluginClass)

    def pluginCloseHandler(self, evt):
        obj = evt.GetEventObject()
        self.pluginsOpen.remove(obj)
        obj.Destroy()

    def loadPlugins(self):
        self.plugins = {}
        self.pluginsOpen = set()
        pluginDir = os.path.join(base_path, 'plugins')
        oldPath = sys.path
        try:
            sys.path.insert(0, pluginDir)
            for _, dirs, files in os.walk(pluginDir):
                for fn in files + dirs:
                    if fn.endswith('.py'):
                        fn = fn[:-3]
                    try:
                        l = importlib.import_module(fn)
                        self.plugins[fn] = l
                        print(f'plugin "{fn}" successfully loaded')
                    except:
                        print(f'plugin "{fn}" loading failed:', file = sys.stderr)
                        traceback.print_exc()
                break
        finally:
            sys.path = oldPath

    def onQuit(self, evt):
        self.Close()

    def onClose(self, evt):
        print('on close')
        self.worker.stopScan()
        print('scan stopped')
        self.Destroy()

    def onText(self, evt):
        if evt.type == TextDataType.STDOUT:
            self.debugWindow.stdout(evt.text)
        elif evt.type == TextDataType.STDERR:
            self.debugWindow.stderr(evt.text)
        #self.sys_stdout.write(evt.text)

    def onAbout(self, evt):
        a = AboutDialog(self)
        a.SetIcon(self.icon)
        a.ShowModal()


    def onWebsite(self, evt):
        wx.BeginBusyCursor()
        import webbrowser
        webbrowser.open(appUrl)
        wx.EndBusyCursor() 
    
    def onDebugWindowToggle(self, evt):

        if self.debugWindowItem.IsChecked():
            self.debugWindow.Show()
        else:
            self.debugWindow.Hide()

    def onDebugWindowClose(self, evt):
        self.debugWindow.Hide()
        self.debugWindowItem.Check(False)

    def showPasswordError(self):
        with PasswordErrorDialog(None) as d:
            ret = d.ShowModal()

            if ret == wx.ID_CANCEL:
                return
            else:
                self.clearPassword()

    def chooseSerialPort(self):
        with SerialPortDialog(None, port = self.j.serial.port) as d:
            if d.ShowModal() == wx.ID_CANCEL:
                return
            self.j.serial.port = d.selectedPort
            if self.j.serial.port is not None:
                config = wx.Config.Get() 
                config.Write('serial_port', self.j.serial.port)
                config.Flush()
            self.updateSerialPort()

    def updateSerialPort(self):
        self.FindWindowByName('serial_btn').SetLabel(str(self.j.serial.port))

    def getLastSerialPort(self):
        ports = serial.tools.list_ports.comports()
        config = wx.Config.Get()
        serialPortName = config.Read('serial_port')
        print(f'last stored port name is {serialPortName}')
        s = serial.Serial()
        for p in ports:
            if p.device == serialPortName:
                s.port = p.device
                break
        else: 
            if ports: 
                s.port = ports[0].device
                print(f'com port {repr(serialPortName)} not found, defaulting to {repr(s.port)}')
        return s

    def onScanData(self, evt):

        if hasattr(evt, 'err'):
            print(evt.err)
            print(''.join(traceback.format_tb(evt.err.__traceback__)))
            self.setStatus('Scan Error')
            return

        self.setStatus('')

        self.logData(evt.basicInfo, evt.cellInfo)

        #sometimes we get data after stopping ...
        if self.worker.scanRunning:
            self.progressGauge.Pulse()
        # Populate cell grid
        temps = [v for k,v in evt.basicInfo.items() if self.ntc_RE.match(k) and v is not None]
        bals  = [v for k,v in evt.basicInfo.items() if k.startswith('bal') and v is not None]
        volts = [v for v in evt.cellInfo.values() if v is not None]

        # send data to any open plugins

        for p in self.pluginsOpen:
            try:
                p.basicInfo = evt.basicInfo
                p.cellInfo = evt.cellInfo
                p.deviceInfo = evt.deviceInfo
            except:
                traceback.print_exc()
        
        grid = self.FindWindowByName('info_cell_grid')
        gridRowsNeeded = max(len(volts), len(temps))
        gridRowsCurrent = grid.GetNumberRows()
        if gridRowsNeeded != gridRowsCurrent:
            grid.DeleteRows(numRows = gridRowsCurrent)
            grid.InsertRows(numRows = gridRowsNeeded)

        # info tab grid
        for i in range(gridRowsNeeded):
            grid.SetCellValue(i, 0, str(i))
            grid.SetCellValue(i, 1, str(volts[i]) if i < len(volts) else '')
            grid.SetCellValue(i, 2, 'BAL' if i < len(bals) and bals[i] else '--')
            grid.SetCellValue(i, 3, str(temps[i]) if i < len(temps) else '')

        # cal tab values
        for i,v in enumerate(volts):
            self.set(f'cal_cell_read{i}', v)

        for i,t in enumerate(temps):
            self.set(f'cal_ntc_read{i}', t)

        cell_max_mv = max(volts)
        cell_min_mv = min(volts)
        cell_delta_mv = cell_max_mv - cell_min_mv
        self.set('info_pack_mv', evt.basicInfo['pack_mv'])
        self.set('info_pack_ma', evt.basicInfo['pack_ma'])
        self.set('cal_pack_ma', evt.basicInfo['pack_ma'])
        self.set('info_cell_avg_mv', sum(volts) // len(volts))
        self.set('info_cell_max_mv', cell_max_mv)
        self.set('info_cell_min_mv', cell_min_mv)
        self.set('info_cell_delta_mv', cell_delta_mv)
        self.set('info_cycle_cnt', evt.basicInfo['cycle_cnt'])
        self.set('info_full_cap', evt.basicInfo['full_cap'])
        self.set('info_cur_cap', evt.basicInfo['cur_cap'])
        self.set('info_cap_pct', evt.basicInfo['cap_pct'])

        self.set('info_device_name', evt.deviceInfo['device_name'])
        date = f"{evt.basicInfo['year']}-{evt.basicInfo['month']}-{evt.basicInfo['day']}"
        self.set('info_mfg_date', date)
        self.set('info_version', f"0x{evt.basicInfo['version']:02X}")

        cfe = evt.basicInfo['chg_fet_en']
        dfe = evt.basicInfo['dsg_fet_en']
        self.set('info_chg_fet_status_txt', 'ENABLED' if cfe else 'DISABLED')
        self.set('info_dsg_fet_status_txt', 'ENABLED' if dfe else 'DISABLED')
        self.set('info_chg_fet_status_img', cfe)
        self.set('info_dsg_fet_status_img', dfe)

        err_fn = [i for i in evt.basicInfo.keys() if i.endswith('_err')]
        for f in err_fn:
            self.set('info_' + f,evt.basicInfo[f])

    def onProgress(self, evt):
        self.progressGauge.SetValue(evt.value)

    def onEepromDone(self, evt):
        self.accessLock.release()
        self.settingsTab.Enable(True)
        self.worker.join()
        if isinstance(evt.data, Exception):
            traceback.print_tb(evt.data.__traceback__)
            print(f'eeprom error: {repr(evt.data)}', file=sys.stderr)
            if isinstance(evt.data, jbd.BMSPasswordError):
                self.showPasswordError()
            elif isinstance(evt.data, jbd.BMSError):
                wx.LogError(f'Unable to communicate with BMS{f" ({evt.data})" if evt.data else ""}')
        elif evt.data is not None:
            self.scatterEeprom(evt.data)
        else:
            pass # was eeprom write ...

    def scatterEeprom(self, data): # AKA "populate GUI fields"
        for k,v in data.items():
            self.set('eeprom_'+k,v)
        self.FindWindowByName('write_eeprom_btn').Enable(True)
        self.FindWindowByName('save_eeprom_btn').Enable(True)

    def gatherEeprom(self): # AKA "get data from GUI fields"
        data = {}
        for c in ChildIter.iterNamed(self):
            if not c.Name.startswith('eeprom_'): continue
            if c.Name.startswith('eeprom_label'): continue
            n = c.Name[7:]
            data[n] = self.get(c.Name)
        return data

    def set(self, name, value):
        svalue = str(value)
        w = self.FindWindowByName(name)
        if w is None:
            print(f'set: unknown field: {name}')
            return
        if isinstance(w, wx.TextCtrl):
            w.SetValue(svalue)
        elif isinstance(w, wx.StaticText):
            w.SetLabel(svalue)
        elif (isinstance(w, wx.SpinCtrlDouble) or
              isinstance(w, RoundGauge)):
            w.SetValue(float(value))
        elif (isinstance(w, BoolImage) or 
              isinstance(w, wx.CheckBox) or 
              isinstance(w, BetterChoice)):
            w.SetValue(value)
        else:
            print(f'set: unknown control type: {type(w)}')

    def get(self, name):
        w = self.FindWindowByName(name)
        if w is None:
            print(f'get: unknown field: {name}')
            return
        if (isinstance(w, EnumChoice) or 
            isinstance(w, wx.TextCtrl) or 
            isinstance(w, wx.SpinCtrlDouble) or 
            isinstance(w, wx.CheckBox) or
            isinstance(w, BetterChoice)):
            return w.GetValue()
        elif isinstance(w, wx.StaticText):
            return None
        else:
            print(f'get: unknown control type {type(w)}, name: {w.Name}')

    def onButtonClick(self, evt):
        n = evt.EventObject.Name
        
        if n == 'read_eeprom_btn':
            self.readEeprom()
        elif n == 'write_eeprom_btn':
            self.writeEeprom()
        elif n == 'load_eeprom_btn':
            self.loadEeprom()
        elif n == 'save_eeprom_btn':
            self.saveEeprom()
        elif n == 'serial_btn':
            self.chooseSerialPort()
        elif n == 'clear_errors_btn':
            self.clearErrors()
        elif n == 'start_stop_scan_btn':
            self.startStopScan()
        elif n == 'start_stop_log_btn':
            self.startStopLog()
        elif n == 'cal_volt_ntc_btn':
            self.voltNtcCal()
        elif n == 'cal_idle_btn':
            self.idleCalMa()
        elif n == 'cal_chg_btn':
            self.chgCalMa()
        elif n == 'cal_dsg_btn':
            self.dsgCalMa()
        elif n == 'chg_dsg_enable_btn':
            self.chgDsgEnable()
        elif n == 'close_all_bal_btn':
            self.balCloseAll()
        elif n == 'open_even_bal_btn':
            self.balOpenEven()
        elif n == 'open_odd_bal_btn':
            self.balOpenOdd()
        elif n == 'exit_bal_btn':
            self.balExit()
        elif n == 'set_pack_cap_rem_btn':
            self.setPackCapRem()
        elif n == 'clear_password_btn':
            self.clearPassword()
        else:
            print(f'unknown button {n}')

    def startStopScan(self):
        if self.worker.scanRunning:
            self.startStopScanButton.Enable(False)
            self.worker.stopScan()
            self.startStopScanButton.SetLabel('Start Scan')
            self.startStopScanButton.Enable(True)
            self.progressGauge.SetValue(0)
        else:
            self.startStopScanButton.Enable(False)
            self.worker.startScan()
            self.startStopScanButton.SetLabel('Stop Scan')
            self.startStopScanButton.Enable(True)
            self.progressGauge.Pulse()

    def voltNtcCal(self):
        try:
            data = self.gatherCal()

            # volts
            prefix = 'cell_act'
            prefix_len = len(prefix)
            cellCal = {}
            for k,v in [(k,v) for k,v in data.items() if k.startswith(prefix)]:
                n = int(k[prefix_len:])
                try:
                    v = int(float(v))
                    print(repr(k), n, repr(v))
                    cellCal[n] = v
                except ValueError:
                    pass
                    #print(f'bad value {repr(v)} for cell {n+1}')

            # Kelvin
            prefix = 'ntc_act'
            prefix_len = len(prefix)
            ntcCal = {}
            for k,v in [(k,v) for k,v in data.items() if k.startswith(prefix)]:
                n = int(k[prefix_len:])
                try:
                    v = float(v)
                    print(repr(k), n, repr(v))
                    ntcCal[n] = v
                except ValueError:
                    pass
                    #print(f'bad value {repr(v)} for cell {n+1}')
            self.accessLock.acquire()
            self.calTab.Enable(False)
            self.worker.runOnce(self.worker.calWorker, cellCal, ntcCal)
        except:
            traceback.print_exc()
            self.accessLock.release()

    def idleCalMa(self):
        try:
            self.accessLock.acquire()
            self.calTab.Enable(False)
            self.j.calIdleCurrent()
        finally:
            self.calTab.Enable(True)
            traceback.print_exc()
            self.accessLock.release()

    def chgCalMa(self):
        try:
            self.accessLock.acquire()
            self.calTab.Enable(False)
            self.j.calChgCurrent(self.get('cal_chg_ma'))
        except:
            traceback.print_exc()
        finally:
            self.calTab.Enable(True)
            self.accessLock.release()

    def dsgCalMa(self):
        try:
            self.accessLock.acquire()
            self.calTab.Enable(False)
            self.j.calDsgCurrent(self.get('cal_dsg_ma'))
        except:
            traceback.print_exc()
        finally:
            self.calTab.Enable(True)
            self.accessLock.release()

    def chgDsgEnable(self):
        try:
            self.accessLock.acquire()
            self.calTab.Enable(False)
            ce = self.get('cal_chg_enable')
            de = self.get('cal_dsg_enable')
            self.j.chgDsgEnable(ce, de)
        except:
            traceback.print_exc()
        finally:
            self.calTab.Enable(True)
            self.accessLock.release()

    def balCloseAll(self):
        try:
            self.accessLock.acquire()
            self.calTab.Enable(False)
            self.j.balCloseAll()
        except:
            traceback.print_exc()
        finally:
            self.calTab.Enable(True)
            self.accessLock.release()

    def balOpenEven(self):
        try:
            self.accessLock.acquire()
            self.calTab.Enable(False)
            self.j.balOpenEven()
        except:
            traceback.print_exc()
        finally:
            self.calTab.Enable(True)
            self.accessLock.release()

    def balOpenOdd(self):
        try:
            self.accessLock.acquire()
            self.calTab.Enable(False)
            self.j.balOpenOdd()
        except:
            traceback.print_exc()
        finally:
            self.calTab.Enable(True)
            self.accessLock.release()

    def balExit(self):
        try:
            self.accessLock.acquire()
            self.calTab.Enable(False)
            self.j.balExit()
        except:
            traceback.print_exc()
        finally:
            self.calTab.Enable(True)
            self.accessLock.release()
    
    def clearPassword(self):
        try:
            self.accessLock.acquire()
            self.calTab.Enable(False)
            self.j.clearPassword()
            wx.LogMessage(f'Password successfully cleared')
        except:
            wx.LogMessage(f'Password clear failed')
            traceback.print_exc()
        finally:
            self.calTab.Enable(True)
            self.accessLock.release()

    def setPackCapRem(self):
        try:
            self.accessLock.acquire()
            try:
                value = int(float(self.get('cal_set_pack_cap_rem')))
            except:
                return
            self.calTab.Enable(False)
            self.j.setPackCapRem(value)
        except:
            traceback.print_exc()
        finally:
            self.calTab.Enable(True)
            self.accessLock.release()

    def onCalDone(self, evt):
        self.accessLock.release()
        self.calTab.Enable(True)
        self.worker.join()
        if isinstance(evt.err, Exception):
            traceback.print_tb(evt.err.__traceback__)
            print(f'cal error: {repr(evt.err)}', file=sys.stderr)
            if isinstance(evt.err, jbd.BMSError):
                wx.LogError(f'Unable to communicate with BMS')

    def gatherCal(self):
        data = {}
        for c in ChildIter.iterNamed(self):
            if not c.Name.startswith('cal_'): continue
            if not '_act' in c.Name: continue
            n = c.Name[4:]
            data[n] = self.get(c.Name)
        return data

    def readEeprom(self):
        self.accessLock.acquire()
        self.settingsTab.Enable(False)
        self.worker.runOnce(self.worker.readEepromWorker)

    def writeEeprom(self):
        data = self.gatherEeprom()
        self.accessLock.acquire()
        self.settingsTab.Enable(False)
        self.worker.runOnce(self.worker.writeEepromWorker, data)

    def loadEeprom(self):
        with wx.FileDialog(self, 'Load EEPROM', wildcard='Data files (*.fig)|*.fig|All files (*.*)|*.*',
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL: return
            try:
                fn = fileDialog.GetPath()
                data = self.j.loadEepromFile(fn)
                self.scatterEeprom(data)
            except:
                traceback.print_exc()
                wx.LogError('Cannot open file "{fn}".')

    def saveEeprom(self):
        with wx.FileDialog(self, 'Save EEPROM', wildcard='Data files (*.fig)|*.fig|All files (*.*)|*.*',
                        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL: return
            try:
                fn = fileDialog.GetPath()
                if '.' not in fn: fn += '.fig'
                data = self.gatherEeprom()
                self.j.saveEepromFile(fn, data)
            except:
                traceback.print_exc()
                wx.LogError(f'Cannot save current data in file "{fn}".')

    def startStopLog(self):
        if not self.logger:
            with wx.FileDialog(self, 'Log Data', wildcard='Data files (*.xlsx)|*.xlsx|CSV files (*.csv)|*.csv|All files (*.*)|*.*',
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

                if fileDialog.ShowModal() == wx.ID_CANCEL: return
                try:
                    fn = fileDialog.GetPath()
                    if '.' not in fn: fn += '.xlsx'
                    self.logger = Logger(fn)
                    self.startStopLogButton.SetLabel('Stop Log')
                except:
                    traceback.print_exc()
                    wx.LogError(f'Cannot save current data in file "{fn}".')
        else:
            self.logger.close()
            self.logger = None
            self.startStopLogButton.SetLabel('Start Log')

    def logData(self, *args, **kwargs):
        if self.logger:
            self.logger.log(*args, **kwargs)

    def clearErrors(self):
        with self.accessLock:
            try:
                self.j.clearErrors()
                for c in ChildIter.iterNamed(self):
                    if 'label_' in c.Name: continue
                    if not c.Name.endswith('_err_cnt'): continue
                    if not c.Name.startswith('eeprom_'): continue
                    print(f'changing {c.Name}')
                    c.SetLabel('0')
            except jbd.BMSError:
                self.setStatus('BMS comm error')

    def setStatus(self, t):
        self.statusText.SetLabel(t)
        self.Layout()

class BkgWorker:
    EepProg, EVT_EEP_PROG = wx.lib.newevent.NewEvent()
    EepDone, EVT_EEP_DONE = wx.lib.newevent.NewEvent()
    ScanData, EVT_SCAN_DATA = wx.lib.newevent.NewEvent()
    CalDone, EVT_CAL_DONE = wx.lib.newevent.NewEvent()

    def __init__(self, parent, jbd):
        self.parent = parent
        self.j = jbd
        self.worker_thread = None
        self.scan_thread = None
        self.scan_run = False
        self.scan_delay = 1

    def progress(self, value):
        wx.PostEvent(self.parent, self.EepProg(value = value))

    def readEepromWorker(self):
        try:
            data = self.j.readEeprom(self.progress)
            wx.PostEvent(self.parent, self.EepDone(data = data))
        except Exception  as e:
            wx.PostEvent(self.parent, self.EepDone(data = e))
        finally:
            wx.PostEvent(self.parent, self.EepProg(value = 100))

    def writeEepromWorker(self, data):
        try:
            self.j.writeEeprom(data, self.progress)
            wx.PostEvent(self.parent, self.EepDone(data = None))
        except Exception as e:
            wx.PostEvent(self.parent, self.EepDone(data = e))
        finally:
            wx.PostEvent(self.parent, self.EepProg(value = 100))

    def runOnce(self, func, *args, **kwargs):
        if self.worker_thread: return
        self.worker_thread = threading.Thread(target = func, args = args, kwargs = kwargs)
        self.worker_thread.start()

    @property
    def scanRunning(self):
        return bool(self.scan_thread)

    def calWorker(self, cellData, ntcData):

        cnt = len(cellData) + len(ntcData)
        cur = 0

        def progAdapter(n):
            nonlocal cnt, cur
            pct = int(cur / cnt * 100)
            print('cal prog', pct)
            self.progress(pct)
            cur += 1

        try:
            print('calibrate start')
            self.j.calCell(cellData, progAdapter)
            self.j.calNtc(ntcData, progAdapter)
            wx.PostEvent(self.parent, self.CalDone(err = None))
        except Exception as e:
            wx.PostEvent(self.parent, self.CalDone(err = e))
        finally:
            self.progress(100)
            print('calibrate end')

    def scanWorker(self):
        try:
            print('scan start')
            while True:
                then = time.time()
                if self.parent.accessLock.acquire(timeout=0):
                    try:

                        basicInfo, cellInfo, deviceInfo = self.j.readInfo()
                        wx.PostEvent(self.parent, self.ScanData(basicInfo = basicInfo, cellInfo = cellInfo, deviceInfo = deviceInfo))
                    except Exception as e:
                        wx.PostEvent(self.parent, self.ScanData(err = e))
                    finally:
                        self.parent.accessLock.release()
                else:
                    print('scan skipped -- BMS busy')

                # attempt to compensate for read time
                elapsed = time.time() - then
                delay = self.scan_delay - elapsed

                if delay < 0:
                    delay = 0
                if delay > .2:
                    cnt = int(delay //.2)
                    slp = delay / cnt
                else:
                    cnt = 1
                    slp = delay

                for i in range(cnt):
                    if not self.scan_run: return
                    time.sleep(slp)
        finally:
            print('scan terminated')
    
    def startScan(self):
        if self.scan_thread: return
        self.scan_thread = threading.Thread(target = self.scanWorker)
        self.scan_run = True
        self.scan_thread.start()

    def stopScan(self):
        if not self.scan_thread: return
        self.scan_run = False
        self.scan_thread.join(3)
        ret = not self.scan_thread.is_alive()
        self.scan_thread = None
        return ret

    def join(self):
        if not self.worker_thread: return True
        self.worker_thread.join(1)
        ret = not self.worker_thread.is_alive()
        self.worker_thread = None

warningMsg = f'''Hi,

Thanks for trying out {appName}. 
This is an beta version, and 
may contain bugs.  If you encounter
any problems, please file an issue 
by selecting "{appName} website" 
from the File menu, and then 
selecting the "Issues" tab.

Thanks.

-- Eric'''
class JBDApp(wx.App):
    def __init__(self, *args, **kwargs):
        self.cli_args = kwargs.pop('cli_args', None)
        super().__init__(*args, **kwargs)

    def OnInit(self):
        configAppName = appName.lower().replace(' ','_') 
        self.SetAppName(configAppName)
        self.SetAppDisplayName(appName)
        icon = wx.Icon(os.path.join(base_path, 'img', 'batt_icon_128.ico'))
        main = Main(None, title = appNameWithVersion, style = wx.DEFAULT_FRAME_STYLE | wx.WS_EX_VALIDATE_RECURSIVELY, icon = icon, cli_args = self.cli_args)
        main.Show()

        if not self.cli_args or not self.cli_args.no_warning:
            # startup warning
            d = wx.MessageDialog(None, warningMsg)
            d.ShowModal()

        return True

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('-n', '--no-redirect', action='store_true')
    p.add_argument('-o', '--open-debug', action='store_true')
    p.add_argument('-c', '--clear-config', action='store_true')
    p.add_argument('-w', '--no-warning', action='store_true')
    p.add_argument('-P', '--plugin', help='open plugin <plugin> on launch')
    p.add_argument('-t', '--tab')
    p.add_argument('-p', '--port')
    cli_args = p.parse_args()

    app = JBDApp(cli_args = cli_args)
    app.MainLoop()

if __name__ == "__main__":
    main()