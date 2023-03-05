#!/usr/bin/env python
import wx
import bmstools.jbd as jbd
import functools
import sys
import re
import traceback
import ctypes as ct

from . import debug_struct

rflags = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | wx.RIGHT
lflags = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.LEFT
defaultBorder = wx.EXPAND | wx.TOP | wx.BOTTOM | wx.LEFT | wx.RIGHT, 7

REG_DEBUG_CMD = 0xFF

class PluginBase:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._basicInfo = None
        self._cellInfo = None
        self._deviceInfo = None

    @property
    def basicInfo(self):
        return self._basicInfo

    @basicInfo.setter
    def basicInfo(self, i):
        self._basicInfo = i


    @property
    def cellInfo(self):
        return self._cellInfo

    @cellInfo.setter
    def cellInfo(self, i):
        self._cellInfo = i

    @property
    def deviceInfo(self):
        return self._deviceInfo

    @deviceInfo.setter
    def deviceInfo(self, i):
        self._deviceInfo = i


class FwDebugDialog(PluginBase, wx.Dialog):
    menu_name = 'FW Debug'
    ntc_RE = re.compile(r'ntc\d+')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.SetTitle(f'Debug Controls')
        self.inControl = False
        self.j = self.GetParent().j
        self.doLayout()

    def doLayout(self):
        topsizer = wx.BoxSizer()
        sb = wx.StaticBox(self, label='Basic Configuration')
        sbs = wx.StaticBoxSizer(sb, wx.VERTICAL)

        vbox0 = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer()
        vbox1 = wx.FlexGridSizer(3)
        vbox2 = wx.FlexGridSizer(3)
        hbox.Add(vbox1, 0, *defaultBorder)
        hbox.Add(vbox2, 0, *defaultBorder)

        vbox0.Add(hbox)
        sbs.Add(vbox0, 1, *defaultBorder)

        def gen_mv_ctrl(i):

            t = wx.StaticText(self, label=f'Cell {i}')
            c = wx.SpinCtrlDouble(self, name=f'cell_mv_{i}', min = 0,max = 65535)
            b = wx.Button(self, label='Set')
            f = functools.partial(self.onSetCellMv, i, c)
            b.Bind(wx.EVT_BUTTON, f)
            return [ 
                (t, 0, rflags, 5),
                (c, 0, lflags),
                (b, 0, lflags, 5)
                 ]

        for i in range(15):
            vbox1.AddMany(gen_mv_ctrl(i))

        def gen_ntc_ctrl(i):

            t = wx.StaticText(self, label=f'NTC {i}')
            c = wx.SpinCtrlDouble(self, name=f'ntc_k_{i}', min = -273.15,max = 6553.5, inc=0.1)
            b = wx.Button(self, label='Set')
            f = functools.partial(self.setNtcC, i, c)
            b.Bind(wx.EVT_BUTTON, f)
            return [ 
                (t, 0, rflags, 5),
                (c, 0, lflags),
                (b, 0, lflags, 5)
                 ]

        for i in range(8):
            vbox2.AddMany(gen_ntc_ctrl(i))


        t = wx.StaticText(self, label=f'Pack mA')
        c = wx.SpinCtrlDouble(self, name=f'pack_ma', min = -327680,max = 327670, inc=0.1)
        b = wx.Button(self, label='Set')
        f = functools.partial(self.onSetPackCa, c)
        b.Bind(wx.EVT_BUTTON, f)
        vbox1.AddMany((
            (t, 1, rflags, 5),
            (c, 1, lflags),
            (b, 1, lflags, 5)
        ))
        t = wx.StaticText(self, label=f'Pack mV')
        c = wx.SpinCtrlDouble(self, name=f'pack_mv', min = 0,max = 655360, inc=10)
        b = wx.Button(self, label='Set')
        f = functools.partial(self.onSetPackCv, c)
        b.Bind(wx.EVT_BUTTON, f)
        vbox1.AddMany((
            (t, 1, rflags, 5),
            (c, 1, lflags),
            (b, 1, lflags, 5)
        ))

        syncButton = wx.Button(self, label = 'Sync From App')
        syncButton.Bind(wx.EVT_BUTTON, self.syncFromApp)
        vbox0.Add(syncButton, 1, *defaultBorder)

        self.bkgDebugButton = wx.Button(self, label = 'Uninitialized')
        self.bkgDebugButton.Bind(wx.EVT_BUTTON, self.toggleDebugPrint)
        self.toggleDebugPrint(force = True)
        vbox0.Add(self.bkgDebugButton, 1, *defaultBorder)
        
        self.controlButton = wx.Button(self, label='Take Control')
        self.controlButton.Bind(wx.EVT_BUTTON, self.onControlButton)
        vbox0.Add(self.controlButton, 1, *defaultBorder)

        self.dumpRegsButton = wx.Button(self, label='Dump Regs')
        self.dumpRegsButton.Bind(wx.EVT_BUTTON, self.onDumpRegsButton)
        vbox0.Add(self.dumpRegsButton, 1, *defaultBorder)

        topsizer.Add(sbs, 1, *defaultBorder)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.onDestroy)

        self.SetSizerAndFit(topsizer)

    def toggleDebugPrint(self, _ = None, force = None):
        if force is not None:
            self.j.bkgRead = force
        else:
            self.j.bkgRead = not self.j.bkgRead

        if self.j.bkgRead:
            self.bkgDebugButton.SetLabel('Disable dbg print')
        else:
            self.bkgDebugButton.SetLabel('Enable dbg print')

    
    def onDestroy(self, _):
        self.j.bkgRead = False
        print("I was destroyed")
    
    def syncFromApp(self, _):
        if self.cellInfo:
            # cell mV
            for i, v in enumerate(self.cellInfo.values()):
                n = f'cell_mv_{i}'
                control = wx.FindWindowByName(n, self)
                if control:
                    control.SetValue(str(v))

        if self.basicInfo:
            # temp
            temps = [v for k,v in self.basicInfo.items() if self.ntc_RE.match(k) and v is not None]
            for i, v in enumerate(temps):
                n = f'ntc_k_{i}'
                control = wx.FindWindowByName(n, self)
                if control:
                    control.SetValue(str(v))

            # pack ma
            control = wx.FindWindowByName('pack_ma')
            if control:
                control.SetValue(str(self.basicInfo['pack_ma']))

            control = wx.FindWindowByName('pack_mv')
            if control:
                control.SetValue(str(self.basicInfo['pack_mv']))

    def onSetCellMv(self, cell_num, widget, evt):
        cell_mv = int(widget.GetValue())
        print('set cell', cell_num, 'mV', cell_mv)
        try:
            self.GetParent().accessLock.acquire()
            s = debug_struct.debug_cmd_packet_t()
            s.cmd = debug_struct.DEBUG_CMD_SET_CELL_MV;
            s.u.cell_mv.cell_num = cell_num
            s.u.cell_mv.cell_mv = cell_mv
            payload = self.j.writeCmdWaitResp(0xFF, bytes(s))
        except:
            traceback.print_exc()
        finally:
            self.GetParent().accessLock.release()

    def setNtcC(self, ntc_num, widget, evt):
        ntc_c = float(widget.GetValue())
        print('set', ntc_num, 'K', ntc_c)
        try:
            self.GetParent().accessLock.acquire()
            s = debug_struct.debug_cmd_packet_t()
            s.cmd = debug_struct.DEBUG_CMD_SET_NTC_DK;
            s.u.ntc_dk.ntc_num = ntc_num
            s.u.ntc_dk.ntc_dk = int(ntc_c * 10 + 2731)
            payload = self.j.writeCmdWaitResp(0xFF, bytes(s))
        except:
            traceback.print_exc()
        finally:
            self.GetParent().accessLock.release()

    def onSetPackCa(self, widget, evt):
        pack_ma = float(widget.GetValue())
        print('set', pack_ma, 'mA')
        try:
            self.GetParent().accessLock.acquire()
            s = debug_struct.debug_cmd_packet_t()
            s.cmd = debug_struct.DEBUG_CMD_SET_PACK_CA;
            s.u.pack_ca.pack_ca = int(pack_ma / 10)
            payload = self.j.writeCmdWaitResp(0xFF, bytes(s))
        except:
            traceback.print_exc()
        finally:
            self.GetParent().accessLock.release()

    def onSetPackCv(self, widget, evt):
        pack_mv = float(widget.GetValue())
        print('set pack', pack_mv, 'mV')
        try:
            self.GetParent().accessLock.acquire()
            s = debug_struct.debug_cmd_packet_t()
            s.cmd = debug_struct.DEBUG_CMD_SET_PACK_CV;
            s.u.pack_cv.pack_cv = int(pack_mv / 10)
            payload = self.j.writeCmdWaitResp(0xFF, bytes(s))
        except:
            traceback.print_exc()
        finally:
            self.GetParent().accessLock.release()

    def onControlButton(self, evt):
        try:
            self.GetParent().accessLock.acquire()
            s = debug_struct.debug_cmd_packet_t()
            s.cmd = debug_struct.DEBUG_CMD_SET_MANUAL_ENABLE;
            s.u.manual_enable.manual_enable = not self.inControl
            payload = self.j.writeCmdWaitResp(0xFF, bytes(s))
        except:
            traceback.print_exc()
        finally:
            self.GetParent().accessLock.release()

        self.inControl = not self.inControl
        self.controlButton.SetLabel('Release Control' if self.inControl else 'Take Control')

    def onDumpRegsButton(self, evt):
        try:
            self.GetParent().accessLock.acquire()
            s = debug_struct.debug_cmd_packet_t()
            s.cmd = debug_struct.DEBUG_CMD_DUMP_REGS;
            payload = self.j.writeCmdWaitResp(0xFF, bytes(s))
        except:
            traceback.print_exc()
        finally:
            self.GetParent().accessLock.release()

plugin_class = FwDebugDialog
plugin_short_name = 'fw_debug'
__all__ = ['plugin_class', 'plugin_short_name']

if __name__ == '__main__':
    print('This is a plugin for the main BMS GUI -- it cannot be run stand-alone', file = sys.stderr)