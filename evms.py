######################################################################################################################
#
#   Copyright (c) 2022 Newport Electric Boats, LLC. All rights reserved.
#   Electric Vessel Management System (EVMS)
#   Filename: evms.py
#
######################################################################################################################

import gi
# import os
import sys
# from sys import argv
import logging
# from dateutil import tz
import gobject

import remote
import glob
import csv
import os

# import panzoom

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk as gtk
from gi.repository import GLib

from dateutil import tz
import serial, can
import time
from time import sleep, tzname, timezone
import concurrent.futures
from sys import argv
import os
import numpy as np

from evms_data_holder import DataHolder
from evms_can import evms_can
from mapPlots import mapPlots
from datetime import datetime, timedelta
import subprocess

import pynmea2
# import math
from math import pi


# import decimal as dc

log_window_buffer = ''

appStartDateString = datetime.now().strftime("%Y-%m-%d")
appStartTimeString = datetime.now().strftime("%H:%M:%S")

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, handlers=[
    logging.FileHandler('logs/' + appStartDateString + '_evms_app.log'),
    logging.StreamHandler(sys.stdout)])


def log(message):
    global log_window_buffer
    log_window_buffer += message + '\n'
    logging.info(message)


class App:

    def __init__(self):

        self.sw_ver_evms = "0.15.4"
        self.appStartTimeString = appStartTimeString
        self.appStartDateString = appStartDateString
        self.SysLog = None
        self.GPSLog = None
        self.app_logging_enabled = True  # ALWAYS TRUE
        self.sys_logging_enabled = True

        self.config_info = self.read_evms_system_settings()

        self.dat = DataHolder()#'logs/' + appStartDateString + '_evms_app.log', log_window_buffer)
        self.mapPlots = mapPlots('logs/' + appStartDateString + '_evms_app.log', log_window_buffer)
        self.evms_can = evms_can('logs/' + appStartDateString + '_evms_app.log', log_window_buffer)
        self.evms_about_top_text = 'EVMS text box message goes here...  this is a long string to discribe the application..'

        try:
            self.init_AppLog()
            self.init_SysLog()
        except Exception as e:
            log('App / SysLog init ERROR: ' + str(e))

        # --- argv parsing -----
        try:
            self.can_if_name = argv[1]
        except Exception as e:
            log('Exception __init__ argv[1]' + str(e))
        try:
            self.syslog_replay_file = argv[3]
            self.replaying_logfile = True
            log("syslog_replay_file = " + str(self.syslog_replay_file))
        except Exception as e:
            self.syslog_replay_file = None
            self.replaying_logfile = False
            log("Replay log not provided, replaying_logfile = False")  # + str(e))
        try:
            self.gpsPort = None
            self.gps_baudrate = 9600  # Default baud rate
            self.gps_ports = ["/dev/ttyUSB0", "/dev/ttyACM0", "/dev/ttyUSB1", "/dev/ttyACM1"]
            self.gps_from_file = False
            if sys.argv[2] != 'usb':
                self.gps_ports = [sys.argv[2]]# Default port name
                self.gps_from_file = True
            self.SER_TIMEOUT = 1  # Timeout for serial Rx
            self.CANInterface = None
            self.stop_gps_thread = False
            self.stop_can_thread = False
            self.stop_timing_thread = False

            self.init_gps_serial()
            self.init_can_interface()

        except Exception as e:
            log('Exception __init__ part 2: ' + str(e))
        try:
            self.a_data = ''
            self.b_data = ''
            self.c_data = ''

            self.builder = gtk.Builder()
            # if self.display_size == '1280x720':
            self.builder.add_from_file("evms_1280x720.glade")

        except Exception as e:
            log('Exception __init__ part 3: ' + str(e))

        try:
            self.dat.max_y_scale_bar_hist = 150  # widow height is 220
            self.dat.y_offset = 0  # 10 pix margin at bottom and top
            self.dat.pwr_graph_x_ofst = 0
            self.dat.pwr_graph_width_pix = 1280
            self.dat.pwr_bin_width = 22
            self.dat.pwr_bin_shade = 18
            self.dat.GPS_FORMAT = 'DECIMAL'
            self.dat.HDG_UNITS = 'MAG'

            self.builder.connect_signals(self)
            self.window = self.builder.get_object("evms_window")

            self.bar_history_combobox = self.builder.get_object('id_bar_history_combobox')

            self.trip_viewport = self.builder.get_object('id_map_viewport')
            self.wifi_combobox = self.builder.get_object('id_wifi_combobox')
            self.wifi_password_box = self.builder.get_object('id_wifi_password')

            # uncomment the following line to make window frameless (unable to kill via titlebar)
            #self.window.set_decorated(False)
            self.window.set_decorated(True)

            # ---------------------- application variables ---
            self.plot_power_history = True
            self.power_history_started = False
            self.ttd_max = 10
            self.ttd_min = -100

            self.id_about_txtbox_top = self.builder.get_object("id_about_txtbox_top")
            self.about_cfg_txtbox = self.builder.get_object("id_about_txtbox")
            self.btn_software_update = self.builder.get_object("id_software_update")
            self.btn_wifi_connect = self.builder.get_object('id_btn_wifi_connect')

            # ---------- Setup About Tab Label Connections
            self.tripBtn_STOP = self.builder.get_object("id_btn1_stop")
            self.tripBtn_PLAY = self.builder.get_object("id_btn2_play_1x")
            self.tripBtn_FF = self.builder.get_object("id_btn3_play_10x")
            self.tripBtn_RR = self.builder.get_object("id_btn_back10")
            self.tripBtn_Rs = self.builder.get_object("id_btn_restart")
            self.tripBtn_select = self.builder.get_object("id_trip_combo_box")
            self.triplog_select = self.builder.get_object("id_triplog_combobox")
            self.wifi_list = self.builder.get_object('id_list_wifi')
            self.chrg_label = self.builder.get_object('charging_lbl')
            self.gps_units = self.builder.get_object('id_gps_units')
            self.hdg_combo = self.builder.get_object('id_hdg_combo')
            self.gps_units.remove(2)
            self.hdg_combo.remove(2)
            self.gps_units.insert_text(0, 'GPS FORMAT')
            self.hdg_combo.insert_text(0, 'HDG UNITS')
            self.gps_units.set_active(0)
            self.hdg_combo.set_active(0)
            self.neb_logo = self.builder.get_object('id_neb_logo')
            self.bar_history = self.builder.get_object('id_bar_history_combobox')
            self.bar_history_type = 'Power'
            self.wifi_txtbox = self.builder.get_object('id_wifi_txtbox')
            self.text_log_buffer = self.wifi_txtbox.get_buffer()
            self.about_top_buffer = self.id_about_txtbox_top.get_buffer()
            self.scroll_window = self.builder.get_object('id_wifi_scrolled_window')
            self.shift = False
            self.caps = False
            self.bar_history.set_active(0)
            self.wifi_status = self.builder.get_object('id_label_wifi_status1')
            self.wifi_name = ''
            self.trip_data_type = ''
            self.line_skip = 1
            self.tz_dict = {'-12': ('Etc/GMT+12', 'GMT+12'), '-11': ('US/Samoa', 'SMST'), '-10': ('US/Hawaii', 'HAST'),
                            '-9': ('America/Anchorage', 'AK'),
                            '-8': ('America/Los Angeles', 'PST'), '-7': ('America/Denver', 'MT'),
                            '-6': ('America/Chicago', 'CT'), '-5': ('America/New_York', 'ET'),
                            '-4': ('America/Santiago', 'PSAST'), '-3': ('America/Buenos_Aires', 'ART'),
                            '-2': ('Atlantic/South_Georgia', 'GST'), '-1': ('Atlantic/Cape_Verde', 'CVT'),
                            'UTC': ('Etc/UTC', 'UTC'), '+1': ('Europe/Brussels', 'CET'),
                            '+2': ('Africa/Tripoli', 'EET'), '+3': ('Europe/Minsk', 'MSK'), '+4': ('Asia/Dubai', 'GST'),
                            '+5': ('Indian/Maldives', 'MHT'),
                            '+6': ('Asia/Dhaka', 'BST'), '+7': ('Asia/Bangkok', 'ICT'), '+8': ('Asia/Taipei', 'CST'),
                            '+9': ('Asia/Tokyo', 'JST'), '+10': ('Australia/Canberra', 'AEST'),
                            '+11': ('Pacific/Guadalcanal', 'SBT'), '+12': ('Pacific/Auckland', 'NZST')}
        except Exception as e:
            log('Exception __init__ ' + str(e))


        def fill_time():
            model = gtk.ListStore(str)
            model.append(['TIMEZONE'])
            for idx in range(1, 25):
                if idx < 13:
                    model.append(['UTC -' + str(13 - idx) + ':00'])
                if idx == 13:
                    model.append(['UTC'])
                elif idx > 13:
                    model.append(['UTC +' + str(idx - 13) + ':00'])
            self.time_combo.set_model(model)
            self.time_combo.set_active(0)


        def change_timezone(box):
            text = self.time_combo.get_active_text()
            if text != 'TIMEZONE':
                if text == 'UTC':
                    zone = self.tz_dict[text]
                else:
                    text = text.split(' ')[1]
                    text = text.split(':')[0]
                    zone = self.tz_dict[text]
                subprocess.run('echo Nebcloud! | sudo -S timedatectl set-timezone ' + zone[0], shell=True)
                time.tzset()
                GLib.idle_add(self.lbl_eng_timezone.set_label, zone[1])
                GLib.idle_add(self.lbl_eng_offsetFromUtc.set_label, str(-timezone / 60 / 60))


        def get_trip_logs():
            model = gtk.ListStore(str)
            list_of_files = glob.glob('logs/*system.log')
            list_of_files.sort(key=os.path.getctime, reverse=True)
            for idx, file in enumerate(list_of_files):
                model.append([file])
            self.triplog_select.set_model(model)
            self.triplog_select.set_active(1)

        def on_switch_tab(notebook, tab, index):
            try:
                tab_list = ['Instruments', 'CAN Data', 'TripLog', 'WiFi', 'About']
                log('Selected ' + tab_list[index] + ' Tab')
            except:
                log('Exception on_switch_tab' + str(e))
        
        def update_line_skip(button, skip):
            self.line_skip = skip

        self.notebook = self.builder.get_object('id_top_notebook')
        self.notebook.connect('switch-page', on_switch_tab)
        self.time_combo = self.builder.get_object('id_combo_4')
        fill_time()
        self.time_combo.connect('changed', change_timezone)
        self.about_text_buffer = self.about_cfg_txtbox.get_buffer()
        self.about_text_buffer.set_text(''.join(self.config_info))
        self.about_cfg_txtbox = self.builder.get_object("id_about_txtbox")
        self.btn_software_update = self.builder.get_object("id_software_update")
        self.btn_wifi_connect = self.builder.get_object('id_btn_wifi_connect')
        self.wifi_list = self.builder.get_object('btn_wifi_network')

        # ---------- Setup About Tab Label Connections
        self.tripBtn_STOP = self.builder.get_object("id_btn1_stop")
        self.tripBtn_PLAY = self.builder.get_object("id_btn2_play_1x")
        self.tripBtn_FF = self.builder.get_object("id_btn3_play_10x")
        self.tripBtn_RR = self.builder.get_object("id_btn_back10")
        self.tripBtn_Rs = self.builder.get_object("id_btn_restart")
        self.tripBtn_select = self.builder.get_object("id_trip_combo_box")
        self.triplog_select = self.builder.get_object("id_triplog_combobox")

        self.notification_textbox = self.builder.get_object('notification_textbox')
        self.notification_icon = self.builder.get_object('notification_icon')

        self.neb_logo = self.builder.get_object('id_neb_logo')
        self.bar_history = self.builder.get_object('id_bar_history_combobox')
        #self.keyboard = self.builder.get_object('id_keyboard')
        #self.keyboard_btn = self.builder.get_object('btn_keyboard_dialog')
        self.keyboard_dialog = self.builder.get_object('id_keyboard')
        self.spare_btn = self.builder.get_object('btn_spare_btn')
        self.bar_history_type = 'Power'
        self.wifi_box_list = ''
        self.wifi_idx = 0
        self.wifi_name = ''
        self.trip_data_type = ''
        self.line_skip = 1
        self.notebook = self.builder.get_object('id_top_notebook')
        self.notebook.connect('switch-page', on_switch_tab)
        self.about_text_buffer = self.about_cfg_txtbox.get_buffer()
        self.about_text_buffer.set_text(''.join(self.config_info))
        self.about_top_buffer.set_text(self.evms_about_top_text)
        #self.about_text_buffer_header = ''
        #self.about_text_buffer_header.set_text("")
        self.bar_history.set_active(0)

        self.active_txtbox = None
        self.active_txt_buffer = None
      #  self.active_end_iter = None
        self.kbd_esc = self.builder.get_object('kbd_escape')
        self.kbd_1 = self.builder.get_object('kbd_1')
        self.kbd_2 = self.builder.get_object('kbd_2')
        self.kbd_3 = self.builder.get_object('kbd_3')
        self.kbd_4 = self.builder.get_object('kbd_4')
        self.kbd_5 = self.builder.get_object('kbd_5')
        self.kbd_6 = self.builder.get_object('kbd_6')
        self.kbd_7 = self.builder.get_object('kbd_7')
        self.kbd_8 = self.builder.get_object('kbd_8')
        self.kbd_9 = self.builder.get_object('kbd_9')
        self.kbd_0 = self.builder.get_object('kbd_0')
        self.kbd_dash = self.builder.get_object('kbd_dash')
        self.kbd_equal = self.builder.get_object('kbd_equal')
        self.kbd_BKSP6 = self.builder.get_object('kbd_BKSP6')
        self.kbd_q = self.builder.get_object('kbd_q')
        self.kbd_w = self.builder.get_object('kbd_w')
        self.kbd_e = self.builder.get_object('kbd_e')
        self.kbd_r = self.builder.get_object('kbd_r')
        self.kbd_t = self.builder.get_object('kbd_t')
        self.kbd_y = self.builder.get_object('kbd_y')
        self.kbd_u = self.builder.get_object('kbd_u')
        self.kbd_i = self.builder.get_object('kbd_i')
        self.kbd_o = self.builder.get_object('kbd_o')
        self.kbd_p = self.builder.get_object('kbd_p')
        self.kbd_bslash = self.builder.get_object('kbd_bslash')
        self.kbd_a = self.builder.get_object('kbd_a')
        self.kbd_s = self.builder.get_object('kbd_s')
        self.kbd_d = self.builder.get_object('kbd_d')
        self.kbd_f = self.builder.get_object('kbd_f')
        self.kbd_g = self.builder.get_object('kbd_g')
        self.kbd_h = self.builder.get_object('kbd_h')
        self.kbd_j = self.builder.get_object('kbd_j')
        self.kbd_k = self.builder.get_object('kbd_k')
        self.kbd_l = self.builder.get_object('kbd_l')
        self.kbd_semicolon = self.builder.get_object('kbd_semicolon')
        self.kbd_apostrophe = self.builder.get_object('kbd_apostrophe')
        self.kbd_ENTER = self.builder.get_object('kbd_ENTER')
        self.kbd_z = self.builder.get_object('kbd_z')
        self.kbd_x = self.builder.get_object('kbd_x')
        self.kbd_c = self.builder.get_object('kbd_c')
        self.kbd_v = self.builder.get_object('kbd_v')
        self.kbd_b = self.builder.get_object('kbd_b')
        self.kbd_n = self.builder.get_object('kbd_n')
        self.kbd_m = self.builder.get_object('kbd_m')
        self.kbd_coma = self.builder.get_object('kbd_coma')
        self.kbd_period = self.builder.get_object('kbd_period')
        self.kbd_fslash = self.builder.get_object('kbd_fslash')
        self.kbd_SHIFT = self.builder.get_object('kbd_SHIFT')
        self.kbd_CAPS = self.builder.get_object('kbd_lshift')
        self.kbd_openbracket = self.builder.get_object('kbd_openbracket')
        self.kbd_closebracket = self.builder.get_object('kbd_closebracket')
        self.kbd_space = self.builder.get_object('kbd_space')
        self.kbd_tab = self.builder.get_object('kbd_tab')
        self.shift_dict = {'1':'!','2':'@','3':'#','4':'$',
                           '5':'%','6':'^','7':'&','8':'*',
                           '9':'(','0':')','-':'_','=':'+',
                           '\\':'|',';':':','\'':'"',',':'<',
                           '.':'>','/':'?','[':'{',']':'}'}

        # self.bar_history.connect('changed', select_bar_history_type)


        def connect_to_wifi(button):
            try:
                wifi_name = self.wifi_combobox.get_active_text()
                pswd = self.wifi_password_box.get_text()
                p = subprocess.run(
                    'echo Nebcloud! | sudo -S nmcli d wifi connect ' + wifi_name + ' password ' + pswd + ' ifname wlp3s0',
                    shell=True)
                self.text_log_buffer = self.wifi_txtbox.get_buffer()
                if p.returncode == 0:
                    msg = 'Connected on ' + wifi_name
                    log(msg)
                    self.text_log_buffer.set_text(msg)
                    self.wifi_name = wifi_name
                    with open('logs/Wifi_Connections.csv', mode='a+') as wifi_file:
                        wifi_writer = csv.writer(wifi_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                        wifi_writer.writerow([wifi_name])
                else:
                    msg = 'Could not connect on ' + wifi_name
                    log(msg)
                    self.text_log_buffer.set_text(msg)
            except Exception as e:
                log('Exception connect_to_wifi' + str(e))

        def wifi_check(button):
            try:
                self.text_log_buffer = self.wifi_txtbox.get_buffer()
                ssid = subprocess.check_output('nmcli -t -f name connection show --active', shell=True).decode('utf-8')
                end_iter = self.text_log_buffer.get_end_iter()
                if len(ssid) == 0:
                    self.text_log_buffer.insert(end_iter,'You are not currently connected to a network.')
                self.wifi_combobox.append_text('Searching...')
                self.wifi_combobox.set_active(0)
                sleep(1)
                self.wifi_box_list = subprocess.check_output(
                     "echo Nebcloud! | for i in $(ls /sys/class/net/ | egrep -v ^lo$); do sudo -S iw dev $i scan | grep SSID | awk '{print substr($0, index($0,$2)) }'; done 2>/dev/null | sort -u",
                     shell=True).decode('utf-8')
                self.wifi_box_list = self.wifi_box_list.replace('\t', '')
                self.wifi_box_list = self.wifi_box_list.replace('SSID: \nSSID List\n', '').split('\n')
                for idx, ssid in enumerate(self.wifi_box_list):
                    if ssid != '':
                        self.wifi_box_list[idx] = ssid
                known_networks = []
                try:
                    with open('logs/Wifi_Connections.csv') as csv_file:
                        csv_reader = csv.reader(csv_file, delimiter=',')
                        for row in csv_reader:
                            known_networks.append(row[0])
                    for ssid in known_networks:
                        if ssid in self.wifi_box_list:
                             self.wifi_box_list.remove(ssid)
                    self.wifi_box_list = known_networks + self.wifi_box_list
                except Exception as e:
                    pass
                page_swap()
            except Exception as e:
                log('Exception list_wifi' + str(e))


        def page_swap():
            model = gtk.ListStore(str)
            model.append(['---Select WiFi---'])
            model.append(['>'])
            count = 0
            ssid = ''
            for _ in range(5):
                index = self.wifi_idx + count
                if index < len(self.wifi_box_list):
                    ssid = self.wifi_box_list[self.wifi_idx + count]
                if ssid != '' and [ssid] not in model:
                    model.append([ssid])
                count += 1
            model.append(['<'])
            if len(model) > 3:
                self.wifi_combobox.set_model(model)
                self.wifi_combobox.set_active(0)



        def switch_wifi_page(button):
            if self.wifi_combobox.get_active_text() == '>':
                self.wifi_idx+=5
                page_swap()
                self.wifi_combobox.emit('popup')
            elif self.wifi_combobox.get_active_text() == '<':
                self.wifi_idx-=5
                page_swap()
                self.wifi_combobox.emit('popup')

        def run_software_update(widget, data=None):
            try:
                if self.dat.charging:
                    remote.main()
                else:
                    end_iter = self.about_text_buffer.get_end_iter()
                    if end_iter != 'Battery not charging. Please ensure the battery is charging before proceeding with a software update.':
                        self.about_text_buffer.insert(end_iter,
                                                      "\n\n\nBattery not charging. Please ensure the battery is "
                                                      "charging before proceeding with a software update.")
            except Exception as e:
                log('Exception run_software_update' + str(e))

        def on_check_for_update(widget, data=None):
            log("checking for software update...")
            try:
                files = remote.version_sync(True)
                self.about_text_buffer.set_text(
                    'Files That Can Be Updated:\n\n' + files + '\n\nThe software update will take '
                                                               'several minutes, and will require the EVMS to reboot.  '
                                                               'For safety purposes, a software update can only be made while the EV battery is charging. ')
                self.btn_software_update.set_label('Update Now')
                self.btn_software_update.connect('clicked', run_software_update)
            except Exception as e:
                log('Exception on_check_for_update ' + str(e))


        def change_map_type(button):
            if self.triplog_select.get_active_text():
                update_image(self.triplog_select)

      #  def show_keyboard(button):
          #  self.keyboard.show()

        def show_kbd(button, arg):
            self.active_txtbox = button
            self.active_txt_buffer = self.active_txtbox.get_buffer()
            self.active_txtbox.set_state_flags(0, True)
            self.keyboard_dialog.show()

        def handle_caps():
            if self.shift == True or self.caps == True:
                self.kbd_1.set_label('!')
                self.kbd_2.set_label('@')
                self.kbd_3.set_label('#')
                self.kbd_4.set_label('$')
                self.kbd_5.set_label('%')
                self.kbd_6.set_label('^')
                self.kbd_7.set_label('&')
                self.kbd_8.set_label('*')
                self.kbd_9.set_label('(')
                self.kbd_0.set_label(')')
                self.kbd_dash.set_label('_')
                self.kbd_equal.set_label('+')
                self.kbd_q.set_label('Q')
                self.kbd_w.set_label('W')
                self.kbd_e.set_label('E')
                self.kbd_r.set_label('R')
                self.kbd_t.set_label('T')
                self.kbd_y.set_label('Y')
                self.kbd_u.set_label('U')
                self.kbd_i.set_label('I')
                self.kbd_o.set_label('O')
                self.kbd_p.set_label('P')
                self.kbd_bslash.set_label('|')
                self.kbd_a.set_label('A')
                self.kbd_s.set_label('S')
                self.kbd_d.set_label('D')
                self.kbd_f.set_label('F')
                self.kbd_g.set_label('G')
                self.kbd_h.set_label('H')
                self.kbd_j.set_label('J')
                self.kbd_k.set_label('K')
                self.kbd_l.set_label('L')
                self.kbd_semicolon.set_label(':')
                self.kbd_apostrophe.set_label('"')
                self.kbd_z.set_label('Z')
                self.kbd_x.set_label('X')
                self.kbd_c.set_label('C')
                self.kbd_v.set_label('V')
                self.kbd_b.set_label('B')
                self.kbd_n.set_label('N')
                self.kbd_m.set_label('M')
                self.kbd_coma.set_label('<')
                self.kbd_period.set_label('>')
                self.kbd_fslash.set_label('?')
                self.kbd_openbracket.set_label('{')
                self.kbd_closebracket.set_label('}')
            else:
                self.kbd_1.set_label('1')
                self.kbd_2.set_label('2')
                self.kbd_3.set_label('3')
                self.kbd_4.set_label('4')
                self.kbd_5.set_label('5')
                self.kbd_6.set_label('6')
                self.kbd_7.set_label('7')
                self.kbd_8.set_label('8')
                self.kbd_9.set_label('9')
                self.kbd_0.set_label('0')
                self.kbd_dash.set_label('-')
                self.kbd_equal.set_label('=')
                self.kbd_q.set_label('q')
                self.kbd_w.set_label('w')
                self.kbd_e.set_label('e')
                self.kbd_r.set_label('r')
                self.kbd_t.set_label('t')
                self.kbd_y.set_label('y')
                self.kbd_u.set_label('u')
                self.kbd_i.set_label('i')
                self.kbd_o.set_label('o')
                self.kbd_p.set_label('p')
                self.kbd_bslash.set_label('\\')
                self.kbd_a.set_label('a')
                self.kbd_s.set_label('s')
                self.kbd_d.set_label('d')
                self.kbd_f.set_label('f')
                self.kbd_g.set_label('g')
                self.kbd_h.set_label('h')
                self.kbd_j.set_label('j')
                self.kbd_k.set_label('k')
                self.kbd_l.set_label('l')
                self.kbd_semicolon.set_label(';')
                self.kbd_apostrophe.set_label('\'')
                self.kbd_z.set_label('z')
                self.kbd_x.set_label('x')
                self.kbd_c.set_label('c')
                self.kbd_v.set_label('v')
                self.kbd_b.set_label('b')
                self.kbd_n.set_label('n')
                self.kbd_m.set_label('m')
                self.kbd_coma.set_label(',')
                self.kbd_period.set_label('.')
                self.kbd_fslash.set_label('/')
                self.kbd_openbracket.set_label('[')
                self.kbd_closebracket.set_label(']')

        def handle_shift(char):
            if char == 'del' or char == '\t' or char == ' ' or char == '\n':
                return char
            else:
                if char.isalpha():
                    return char.upper()
                else:
                    return self.shift_dict[char]

        def keyboard_handle(button, char):
            if self.shift == True or self.caps == True:
                char = handle_shift(char)
                handle_caps()
            if char == 'ESCAPE' or char == '\n':
                self.keyboard_dialog.hide()
            elif char == 'del':
                self.active_txtbox.set_text(self.active_txt_buffer.get_text()[:-1])
            elif char == 'SHIFT':
                self.shift = True
                handle_caps()
            elif char == 'CAPS':
                self.caps = not self.caps
                handle_caps()
            else:
                #self.active_end_iter = self.active_txt_buffer.get_end_iter()
                self.active_txt_buffer.insert_text(self.active_txt_buffer.get_length(), char, 1)
            if char != 'SHIFT' and self.shift == True:
                self.shift = False
                handle_caps()

        self.tripBtn_STOP.connect('clicked', update_line_skip, 0)
        self.tripBtn_PLAY.connect('clicked', update_line_skip, 1)
        self.tripBtn_FF.connect('clicked', update_line_skip, 10)
        self.tripBtn_RR.connect('clicked', update_line_skip, -10)
        self.tripBtn_Rs.connect('clicked', update_line_skip, -1000)
        self.btn_software_update.connect('clicked', on_check_for_update)
        self.btn_wifi_connect.connect('clicked', connect_to_wifi)
        self.tripBtn_select.connect('changed', change_map_type)
        self.wifi_combobox.connect('changed', switch_wifi_page)
        self.wifi_list.connect('clicked', wifi_check)
        self.wifi_password_box.connect('state-flags-changed', show_kbd)
       #self.keyboard_btn.connect('clicked', show_keyboard)
        #self.spare_btn.connect('clicked', show_kbd)
        self.kbd_esc.connect('clicked', keyboard_handle, 'ESCAPE')
        self.kbd_1.connect('clicked', keyboard_handle, '1')
        self.kbd_2.connect('clicked', keyboard_handle, '2')
        self.kbd_3.connect('clicked', keyboard_handle, '3')
        self.kbd_4.connect('clicked', keyboard_handle, '4')
        self.kbd_5.connect('clicked', keyboard_handle, '5')
        self.kbd_6.connect('clicked', keyboard_handle, '6')
        self.kbd_7.connect('clicked', keyboard_handle, '7')
        self.kbd_8.connect('clicked', keyboard_handle, '8')
        self.kbd_9.connect('clicked', keyboard_handle, '9')
        self.kbd_0.connect('clicked', keyboard_handle, '0')
        self.kbd_dash.connect('clicked', keyboard_handle, '-')
        self.kbd_equal.connect('clicked', keyboard_handle, '=')
        self.kbd_BKSP6.connect('clicked', keyboard_handle, 'del')
        self.kbd_q.connect('clicked', keyboard_handle, 'q')
        self.kbd_w.connect('clicked', keyboard_handle, 'w')
        self.kbd_e.connect('clicked', keyboard_handle, 'e')
        self.kbd_r.connect('clicked', keyboard_handle, 'r')
        self.kbd_t.connect('clicked', keyboard_handle, 't')
        self.kbd_y.connect('clicked', keyboard_handle, 'y')
        self.kbd_u.connect('clicked', keyboard_handle, 'u')
        self.kbd_i.connect('clicked', keyboard_handle, 'i')
        self.kbd_o.connect('clicked', keyboard_handle, 'o')
        self.kbd_p.connect('clicked', keyboard_handle, 'p')
        self.kbd_bslash.connect('clicked', keyboard_handle, '\\')
        self.kbd_a.connect('clicked', keyboard_handle, 'a')
        self.kbd_s.connect('clicked', keyboard_handle, 's')
        self.kbd_d.connect('clicked', keyboard_handle, 'd')
        self.kbd_f.connect('clicked', keyboard_handle, 'f')
        self.kbd_g.connect('clicked', keyboard_handle, 'g')
        self.kbd_h.connect('clicked', keyboard_handle, 'h')
        self.kbd_j.connect('clicked', keyboard_handle, 'j')
        self.kbd_k.connect('clicked', keyboard_handle, 'k')
        self.kbd_l.connect('clicked', keyboard_handle, 'l')
        self.kbd_semicolon.connect('clicked', keyboard_handle, ';')
        self.kbd_apostrophe.connect('clicked', keyboard_handle, '\'')
        self.kbd_ENTER.connect('clicked', keyboard_handle, '\n')
        self.kbd_z.connect('clicked', keyboard_handle, 'z')
        self.kbd_x.connect('clicked', keyboard_handle, 'x')
        self.kbd_c.connect('clicked', keyboard_handle, 'c')
        self.kbd_v.connect('clicked', keyboard_handle, 'v')
        self.kbd_b.connect('clicked', keyboard_handle, 'b')
        self.kbd_n.connect('clicked', keyboard_handle, 'n')
        self.kbd_m.connect('clicked', keyboard_handle, 'm')
        self.kbd_coma.connect('clicked', keyboard_handle, ',')
        self.kbd_period.connect('clicked', keyboard_handle, '.')
        self.kbd_fslash.connect('clicked', keyboard_handle, '/')
        self.kbd_SHIFT.connect('clicked', keyboard_handle, 'SHIFT')
        self.kbd_CAPS.connect('clicked', keyboard_handle, 'CAPS')
        self.kbd_openbracket.connect('clicked', keyboard_handle, '[')
        self.kbd_closebracket.connect('clicked', keyboard_handle, ']')
        self.kbd_space.connect('clicked', keyboard_handle, ' ')
        self.kbd_tab.connect('clicked', keyboard_handle, '\t')
        self.tripBtn_select.set_active(0)
        self.neb_logo.set_from_file('neb_logo_100x100.jpg')
        image_area = self.trip_viewport


        def handle_unit_change(box, type):
            text = box.get_active_text()
            if text != 'GPS FORMAT' or 'HDG UNITS':
                if type == 'GPS':
                    self.dat.GPS_FORMAT = text
                    log('GPS FORMAT: ' + self.dat.GPS_FORMAT)
                elif type == 'HDG':
                    self.dat.HDG_UNITS = text
                    log('HDG UNITS: ' + self.dat.HDG_UNITS)

        self.gps_units.connect('changed', handle_unit_change, 'GPS')
        self.hdg_combo.connect('changed', handle_unit_change, 'HDG')


        def on_gps_logging(button):
            self.gps_logging_enabled = not self.gps_logging_enabled
            if self.gps_logging_enabled == False:
                try:
                    if self.GPSLog != None:
                        self.GPSLog.close()
                except Exception as e:
                    log("on_gps_logging ERROR: " + str(e))
            else:
                try:
                    self.GPSLog = open(self.GPSLogName, 'a+')
                    self.GPSLog.write('\n\n ******  Newport Electric Boats, LLC  ****** \n'
                                      'EVMS GPS Logfile, generated '+ self.appStartDateString + ' ' + datetime.now().strftime("%H:%M:%S") + ' with software version: '
                                      + str( self.sw_ver_evms) + '\n')
                    self.GPSLog.write('\n\n\n')
                    self.GPSLog.flush()

                except Exception as e:
                    self.gps_logging_enabled = False
                    log("Error opening GPSLog: " + str(e))

            log("gps_logging_enabled = " + str(self.gps_logging_enabled))


        def on_can_logging(button):
            self.can_logging_enabled = not self.can_logging_enabled
            log("can_logging_enabled = " + str(self.can_logging_enabled))
            try:
                if self.can_logging_enabled == True:
                    os.system("candump -L " + argv[1] + " >> " + self.CANLogName + " & ")
                    log("started candump process")
                else:
                    os.system("killall candump")
                    log("killing candump process")
            except Exception as e:
                log("on_can_logging ERROR: " + str(e))

        def on_show_passwd(button):
            self.show_pswd = not self.show_pswd
            self.chk_show_passwd.set_visibility(self.show_pswd)


        def update_image(triplog, data=None):
            try:
                if triplog != None:
                    # remove the previous image
                    for child in image_area.get_children():
                        image_area.remove(child)
                    name = self.triplog_select.get_active_text()
                    # add a new image
                    stat = self.tripBtn_select.get_active_text()
                    plot_stat = 'pwr'
                    if stat == 'Battery State of Charge':
                        plot_stat = 'soc'
                    elif stat == 'Speed':
                        plot_stat = 'spd'
                    elif stat == 'Pack Amp Hours':
                        plot_stat = 'pack_amp_hrs'
                    image_name = self.mapPlots.plot_coords(name, plot_stat)
                    image = gtk.Image()
                    image.set_from_file(image_name)
                    image_area.add(image)
                    image_area.show_all()
            except Exception as e:
                log('update_image ERROR: ' + str(e))

        get_trip_logs()

        #update_image(self.triplog_select) #fixme - do we need to call this on init?

        self.triplog_select.connect('changed', update_image)

        #setup aboutbox software version connections
        self.evms_sw_ver       = self.builder.get_object("evms_sw_ver")
        self.data_sw_ver       = self.builder.get_object("data_sw_ver")
        self.can_sw_ver       = self.builder.get_object("can_sw_ver")
        self.map_sw_ver       = self.builder.get_object("map_sw_ver")
        self.net_sw_ver       = self.builder.get_object("net_sw_ver")


        # ---------- Setup Instruments Tab Label Connections
        self.lbl_Batt_val = self.builder.get_object("lbl_Batt_val")
        self.lbl_MotTemp_val = self.builder.get_object("lbl_MotTemp_val")
        self.lbl_CtlrTemp_val = self.builder.get_object("lbl_CtlrTemp_val")
        self.lbl_TTD_val = self.builder.get_object("lbl_TTD_val")
        self.lbl_PackAmps_val = self.builder.get_object("lbl_PackAmps_val")
        self.lbl_PackVolts_val = self.builder.get_object("lbl_PackVolts_val")
        self.lbl_PackAh_val = self.builder.get_object("lbl_PackAh_val")
        self.lbl_HighTemp_val = self.builder.get_object("lbl_HighTemp_val")
        self.lbl_LowTemp_val = self.builder.get_object("lbl_LowTemp_val")
        self.lbl_Resistance_val = self.builder.get_object("lbl_Resistance_val")
        self.lbl_OpenVolts_val = self.builder.get_object("lbl_OpenVolts_val")
        self.lbl_TotalCycles_val = self.builder.get_object("lbl_TotalCycles_val")
        self.lbl_LAT_val = self.builder.get_object("lbl_LAT_val")
        self.lbl_LON_val = self.builder.get_object("lbl_LON_val")
        self.lbl_DATE_val = self.builder.get_object("lbl_DATE_val")
        self.lbl_TIME_val = self.builder.get_object("lbl_TIME_val")

        self.lbl_spd_val = self.builder.get_object("lbl_spd_val")
        self.lbl_rpm_val = self.builder.get_object("lbl_rpm_val")
        self.lbl_pwr_val = self.builder.get_object("lbl_pwr_val")

        self.lbl_HDG_val = self.builder.get_object("lbl_HDG_val")
        self.lbl_fwd_rev_val = self.builder.get_object("lbl_fwd_rev_val")

        self.plotRingGaugeArea = self.builder.get_object("plotRingGaugeView")
        self.plotGaugeKeyArea = self.builder.get_object("plotGaugeKeyView")
        self.plotMotTempArea = self.builder.get_object("plotMotTempView")
        self.plotCtrlTempArea = self.builder.get_object("plotCtrlTempView")
        self.plotBattSocArea = self.builder.get_object("plotBattSocView")

        self.plotPwrHistAreaSec = self.builder.get_object("plotPwrHistSecView")
        self.plotPwrHistAreaMin = self.builder.get_object("plotPwrHistMinView")
        self.plotPwrHistAreaHrs = self.builder.get_object("plotPwrHistHrsView")

        self.txtSysLogView = self.builder.get_object("txtSysLogView")
        self.lbl_runTime_val = self.builder.get_object("lbl_runTime_val")

        self.chk_gps_logging = self.builder.get_object("id_gps_logging")
        self.chk_can_logging = self.builder.get_object("id_can_logging")
        self.chk_show_passwd = self.builder.get_object('id_sys_ckbox_6')
        self.show_pswd = False
        if self.can_logging_enabled == True:
            self.chk_can_logging.emit('clicked')
        if self.gps_logging_enabled == True:
            self.chk_gps_logging.emit('clicked')
        self.chk_can_logging.connect('clicked', on_can_logging)
        self.chk_gps_logging.connect('clicked', on_gps_logging)
        self.chk_show_passwd.connect('clicked', on_show_passwd)
        # ------------- SET UP CAN TAB WIDGETS -------------------
        self.lbl_eng_rpm = self.builder.get_object("lbl_eng_rpm")
        self.lbl_eng_motTemp = self.builder.get_object("lbl_eng_motTemp")
        self.lbl_eng_CtrlTemp = self.builder.get_object("lbl_eng_CtrlTemp")
        self.lbl_eng_motAmps = self.builder.get_object("lbl_eng_motAmps")
        self.lbl_eng_motVolts = self.builder.get_object("lbl_eng_motVolts")
        self.lbl_eng_motStatFreq = self.builder.get_object("lbl_eng_motStatFreq")
        self.lbl_eng_ctrlFault1 = self.builder.get_object("lbl_eng_ctrlFault1")
        self.lbl_eng_ctrlFault2 = self.builder.get_object("lbl_eng_ctrlFault2")
        self.lbl_eng_throttleInput = self.builder.get_object("lbl_eng_throttleInput")
        self.lbl_eng_brakeInput = self.builder.get_object("lbl_eng_brakeInput")
        self.lbl_eng_econBit = self.builder.get_object("lbl_eng_econBit")
        self.lbl_eng_regenBit = self.builder.get_object("lbl_eng_regenBit")
        self.lbl_eng_revBit = self.builder.get_object("lbl_eng_revBit")
        self.lbl_eng_brakeLightBit = self.builder.get_object("lbl_eng_brakeLightBit")
        self.lbl_eng_packLoCellV = self.builder.get_object("lbl_eng_packLoCellV")
        self.lbl_eng_packHiCellV = self.builder.get_object("lbl_eng_packHiCellV")
        self.lbl_eng_PackAvgCellV = self.builder.get_object("lbl_eng_PackAvgCellV")
        self.lbl_eng_packMaxCellNum = self.builder.get_object("lbl_eng_packMaxCellNum")
        self.lbl_eng_packPopCells = self.builder.get_object("lbl_eng_packPopCells")
        self.lbl_eng_dischRlyEnbl = self.builder.get_object("lbl_eng_dischRlyEnbl")
        self.lbl_eng_chgRlyEnbl = self.builder.get_object("lbl_eng_chgRlyEnbl")
        self.lbl_eng_chgSftyEnbl = self.builder.get_object("lbl_eng_chgSftyEnbl")
        self.lbl_eng_mlfctnIndActive = self.builder.get_object("lbl_eng_mlfctnIndActive")
        self.lbl_eng_mltprpsInpSig = self.builder.get_object("lbl_eng_mltprpsInpSig")
        self.lbl_eng_alwaysOnSigStat = self.builder.get_object("lbl_eng_alwaysOnSigStat")
        self.lbl_eng_isRdySigStat = self.builder.get_object("lbl_eng_isRdySigStat")
        self.lbl_eng_charging = self.builder.get_object("lbl_eng_charging")
        self.lbl_eng_pack12v = self.builder.get_object("lbl_eng_pack12v")
        self.lbl_eng_packAmps = self.builder.get_object("lbl_eng_packAmps")
        self.lbl_eng_packVolts = self.builder.get_object("lbl_eng_packVolts")
        self.lbl_eng_packAh = self.builder.get_object("lbl_eng_packAh")
        self.lbl_eng_packHiTemp = self.builder.get_object("lbl_eng_packHiTemp")
        self.lbl_eng_packLoTemp = self.builder.get_object("lbl_eng_packLoTemp")
        self.lbl_eng_packSoc = self.builder.get_object("lbl_eng_packSoc")
        self.lbl_eng_packRes = self.builder.get_object("lbl_eng_packRes")
        self.lbl_eng_packHealth = self.builder.get_object("lbl_eng_packHealth")
        self.lbl_eng_packOpenV = self.builder.get_object("lbl_eng_packOpenV")
        self.lbl_eng_packTotCyc = self.builder.get_object("lbl_eng_packTotCyc")
        self.lbl_eng_packCcl = self.builder.get_object("lbl_eng_packCcl")
        self.lbl_eng_packDcl = self.builder.get_object("lbl_eng_packDcl")
        self.lbl_eng_packMaxCellV = self.builder.get_object("lbl_eng_packMaxCellV")
        self.lbl_eng_packMinCellV = self.builder.get_object("lbl_eng_packMinCellV")
        self.lbl_eng_pidRespMin = self.builder.get_object("lbl_eng_pidRespMin")
        self.lbl_eng_pidRespMax = self.builder.get_object("lbl_eng_pidRespMax")
        self.lbl_eng_pidFaultCnt = self.builder.get_object("lbl_eng_pidFaultCnt")
        self.lbl_eng_pidErr1 = self.builder.get_object("lbl_eng_pidErr1")
        self.lbl_eng_pidErr2 = self.builder.get_object("lbl_eng_pidErr2")
        self.lbl_eng_gpsTime = self.builder.get_object("lbl_eng_gpsTime")
        self.lbl_eng_gpsDate = self.builder.get_object("lbl_eng_gpsDate")
        self.lbl_eng_latitude = self.builder.get_object("lbl_eng_latitude")
        self.lbl_eng_longitude = self.builder.get_object("lbl_eng_longitude")
        self.lbl_eng_kts = self.builder.get_object("lbl_eng_kts")
        self.lbl_eng_hdg = self.builder.get_object("lbl_eng_hdg")
        self.lbl_eng_sysDatetime = self.builder.get_object("lbl_eng_sysDatetime")
        self.lbl_eng_gpsDatetime = self.builder.get_object("lbl_eng_gpsDatetime")
        self.lbl_eng_timeDelta = self.builder.get_object("lbl_eng_timeDelta")
        self.lbl_eng_timezone = self.builder.get_object("lbl_eng_timezone")
        self.lbl_eng_offsetFromUtc = self.builder.get_object("lbl_eng_offsetFromUtc")

        # -----------------------------------------------------------------------------------------------
        self.window.set_title('Electric Vessel Monitoring System')
        self.window.set_border_width(0)
        self.window.connect_after('destroy', self.on_window_destroy)

        # -----------------------------------------------------------------------------------------------
        self.plotRingGaugeArea.connect('draw', self.on_draw_ring_gauge)
        self.plotGaugeKeyArea.connect('draw', self.on_draw_gauge_key)
        self.plotMotTempArea.connect('draw', self.on_draw_mot_temp)
        self.plotCtrlTempArea.connect('draw', self.on_draw_mot_ctrl_temp)
        self.plotBattSocArea.connect('draw', self.on_draw_batt_soc)

        self.plotPwrHistAreaSec.connect('draw', self.on_draw_pwr_hist_sec)
        self.plotPwrHistAreaMin.connect('draw', self.on_draw_pwr_hist_min)
        self.plotPwrHistAreaHrs.connect('draw', self.on_draw_pwr_hist_hrs)

        self.window.show_all()
        #self.keyboard.hide()
        self.keyboard_dialog.hide()
        self.chrg_label.hide()
        self.notification_icon.hide()
        self.notification_textbox.hide()


        with concurrent.futures.ThreadPoolExecutor() as executor:
            #executor.submit(self.applog_thread)
            if self.syslog_replay_file is None:
                # fixme:
                executor.submit(self.gps_reader_thread)
                executor.submit(self.can_reader_thread, self.CANInterface)
                executor.submit(gtk.main)
                executor.submit(self.tenHz_timer_thread)
            else:
                try:
                    executor.submit(gtk.main)
                    executor.submit(self.tenHz_timer_thread)
                except Exception as e:
                    log("Replay file not availble, check filename: " + str(e))

    def on_window_destroy(self, widget, data=None):
        self.stop_gps_thread = True
        self.stop_can_thread = True
        self.stop_timing_thread = True

        gtk.main_quit()

    def read_evms_system_settings(self):
        file = open('evms_system_settings.cfg', 'r+')
        lines = file.readlines()
        for line in lines:
            if line != '\n':
                line = line.rstrip()
                line = line.replace(' ', '')
                line = line.split(',')
                if line[0] == 'max_rpm':
                    self.max_rpm = float(line[1])
                elif line[0] == 'max_spd':
                    self.max_spd = float(line[1])
                elif line[0] == 'max_pwr':
                    self.max_pwr = float(line[1])
                elif line[0] == 'max_mot_temp':
                    self.max_mot_temp = float(line[1])
                elif line[0] == 'max_mot_ctrl_temp':
                    self.max_mot_ctrl_temp = float(line[1])
                elif line[0] == 'battery_size':
                    self.battery_size = float(line[1])
                elif line[0] == 'system_logging_level':
                    self.system_logging_level = float(line[1])
                elif line[0] == 'system_logging_frequency':
                    self.system_logging_frequency = float(line[1])
                elif line[0] == 'battery_warning_threshold':
                    self.batt_warn_threshold = float(line[1])
                elif line[0] == 'battery_crit_threshold':
                    self.batt_crit_threshold = float(line[1])
                elif line[0] == 'mot_temp_warn_threshold':
                    self.mot_temp_warn_threshold = float(line[1])
                elif line[0] == 'mot_temp_crit_threshold':
                    self.mot_temp_crit_threshold = float(line[1])
                elif line[0] == 'ctrlr_temp_warn_threshold':
                    self.ctrlr_temp_warn_threshold = float(line[1])
                elif line[0] == 'ctrlr_temp_crit_threshold':
                    self.ctrlr_temp_crit_threshold = float(line[1])
                elif line[0] == 'can_logging_enabled':
                    if line[1] == 'True':
                        self.can_logging_enabled = True
                    elif line[1] == 'False':
                        self.can_logging_enabled = False
                elif line[0] == 'gps_logging_enabled':
                    if line[1] == 'True':
                        self.gps_logging_enabled = True
                    elif line[1] == 'False':
                        self.gps_logging_enabled = False
        return lines[13:]


    # ----------------------------- timing_thread -----------------------------

    def tenHz_timer_thread(self):

        log("starting timer thread")
        self.dat.runTime_100ms = 0

        if self.replaying_logfile == True:  # process new data from logfile
            log("Running SIMULATION mode from Logfile")
            try:
                with open(self.syslog_replay_file, 'r') as replay_file:
                    line_read = 0
                    # syslog file format is CSV, starting on line 3
                    # date,time,rpm,motor_tmp,ibat,vbat,pack_hlth,pack_cycles,lo_cell_v,hi_cell_v,pack_lo_tmp,pack_hi_tmp,pack_amp_hrs,soc,lat,lon,spd,hdg,rev,charging
                    # filedescriptors = termios.tcgetattr(sys.stdin)
                    # tty.setcbreak(sys.stdin)
                    lines = replay_file.readlines()
                    index = 0
                    line = lines[index]
                    sw_ver = 0
                    while line:
                        if self.dat.get_dataholder_log() != '':
                            log(self.dat.get_dataholder_log())
                            self.dat.clear_dataholder_log()

                        line_read = line_read + 1
                        # self.log_message ("processing replay_file line#: " + str(line_read))
                        # log(line)
                        if line_read == 2:
                            sw_ver = int(line.split(' ')[-1].rstrip().split('.')[1])
                        if line_read >= 5:
                            try:
                                if line[1:3] == ',2':
                                    columns = line.split(",")
                                else:
                                    index +=1
                                    line = lines[index]
                                    continue
                            except Exception as e:
                                log("Convert: " + str(e))

                            # METHOD 2: Auto-detect zones:
                            from_zone = tz.tzutc()
                            to_zone = tz.tzlocal()

                            # utc = datetime.utcnow()
                            utc = datetime.strptime(columns[2], '%H:%M:%S')

                            # Tell the datetime object that it's in UTC time zone since
                            # datetime objects are 'naive' by default
                            utc = utc.replace(tzinfo=from_zone)

                            # Convert time zone
                            local_time = utc.astimezone(to_zone)
                            local_time = local_time.time()
                            self.dat.date = columns[0]
                            self.dat.time = str(local_time)
                            if sw_ver < 10:
                                if columns[2] is not None:
                                    self.dat.rpm = float(columns[2])
                                if columns[3] is not None and columns[3] != "None":
                                    self.dat.mot_temp = float(columns[3])
                                if columns[4] is not None and columns[4] != "None":
                                    self.dat.pack_amps = int(float(columns[4]))
                                if columns[5] is not None and columns[5] != "None":
                                    self.dat.pack_volts = float(columns[5])
                                if columns[6] is not None and columns[6] != "None":
                                    self.dat.pack_hlth = float(columns[6])
                                if columns[7] is not None and columns[7] != "None":
                                    self.dat.pack_total_cyc = float(columns[7])
                                if columns[8] is not None and columns[8] != "None":
                                    self.dat.pack_lo_cell_v = float(columns[8])
                                if columns[9] is not None and columns[9] != "None":
                                    self.dat.pack_hi_cell_v = float(columns[9])
                                if columns[10] is not None and columns[10] != "None":
                                    self.pack_lo_tmp = float(columns[10])
                                if columns[11] is not None and columns[11] != "None":
                                    self.pack_hi_tmp = float(columns[11])
                                if columns[12] is not None and columns[12] != "None":
                                    self.pack_amp_hrs = float(columns[12])
                                if columns[13] is not None and columns[13] != "None":
                                    self.dat.soc = float(columns[13])
                                if columns[14] is not None and columns[14] != "None":
                                    self.dat.latitude = columns[14]
                                if columns[15] is not None and columns[15] != "None":
                                    self.dat.longitude = columns[15]
                                if columns[16] is not None and columns[16] != "None":
                                    self.dat.spd = float(columns[16])
                                if columns[17] is not None and columns[17] != "None":
                                    self.dat.hdg = float(columns[17])
                                if columns[18] is not None and columns[18] != "None":
                                    self.dat.rev = columns[18]
                                if columns[19] is not None and columns[19] != "None":
                                    self.dat.charging = columns[19]
                            else:
                                if columns[1] is not None:
                                    self.dat.date = columns[1]
                                if columns[2] is not None and columns[2] != "None":
                                    self.dat.time = columns[2]
                                if columns[3] is not None and columns[3] != "None":
                                    self.dat.latitude = int(float(columns[3]))
                                if columns[4] is not None and columns[4] != "None":
                                    self.dat.longitude = float(columns[4])
                                if columns[5] is not None and columns[5] != "None":
                                    self.dat.spd = float(columns[5])
                                if columns[6] is not None and columns[6] != "None":
                                    self.dat.hdg = float(columns[6])
                                if columns[7] is not None:
                                    self.dat.rpm = float(columns[7])
                                if columns[8] is not None and columns[8] != "None":
                                    self.dat.soc = float(columns[8])
                                if columns[9] is not None and columns[9] != "None":
                                    self.dat.pack_amps = int(float(columns[9]))
                                if columns[10] is not None and columns[10] != "None":
                                    self.dat.pack_volts = float(columns[10])
                                if columns[11] is not None and columns[11] != "None":
                                    self.dat.mot_temp = float(columns[11])
                                if columns[12] is not None and columns[12] != "None":
                                    self.dat.mot_ctrl_temp = float(columns[12])
                                if columns[13] is not None and columns[13] != "None":
                                    self.dat.pack_amp_hrs = float(columns[13])
                                if columns[14] is not None and columns[14] != "None":
                                    self.dat.thrtl_inp = float(columns[14])
                                if columns[15] is not None and columns[15] != "None":
                                    self.dat.brake_inp = float(columns[15])
                                if columns[16] is not None and columns[16] != "None":
                                    self.dat.mot_amps = float(columns[16])
                                if columns[17] is not None and columns[17] != "None":
                                    self.dat.rev = float(columns[17])
                                if columns[18] is not None and columns[18] != "None":
                                    self.dat.charging = float(columns[18])
                                if columns[19] is not None and columns[19] != "None":
                                    self.dat.econ_bit = float(columns[19])
                                if columns[20] is not None and columns[20] != "None":
                                    self.dat.regen_bit = float(columns[20])

                            if self.dat.charging:
                                self.chrg_label.show()
                            # -- motor power calculation --
                            self.dat.pwr = self.dat.get_motor_pwr()[0]
                            # log("self.dat.runTime_100ms={:.d}".format(self.dat.runTime_100ms))

                            # NOTE: add 0.900 seconds to the runTimer in Simulation Mode
                            #       because we step at 1hz rather than 10hz when replaying logfiles...
                            self.dat.runTime_100ms = self.dat.runTime_100ms + 9
                            self.update_runTimer()
                            if self.dat.OneSecTick == True:  # -------------- One Hz Tasks --------------
                                self.do_OneSecTasks()

                            if self.dat.OneMinTick == True:  # -------------- One Min Tasks --------------
                                self.do_OneMinTasks()

                            if self.dat.OneHrTick == True:  # -------------- One Hr Tasks --------------
                                self.do_OneHrTasks()

                            self.updateGUI()
                            sleep(1)
                        if self.line_skip == -1000:
                            index = 3
                            line = lines[index]
                            self.line_skip = 1
                        else:
                            index += self.line_skip
                            line = lines[index]
                            if index < 0:
                                index = 3
                                line = lines[index]
                                self.line_skip = 1
                log("End of Replay File...")
            except Exception as e:
                log("tenHz_timer_thread, logfile_replay exception: " + str(e))


        else:  # process new data from CAN input (we're not replaying a logfile)
            while True:
                if self.stop_timing_thread:
                    break

                try:

                    if self.dat.get_dataholder_log() != '': # -------------- process any data_holder logs --------------
                        dhlog_entry = self.dat.get_dataholder_log()
                        log(dhlog_entry)
                        self.dat.clear_dataholder_log()

                    # -- motor power calculations --
                    self.dat.pwr = self.dat.get_motor_pwr()[0]
                    # print("self.dat.runTime_100ms={:.d}".format(self.dat.runTime_100ms))
                    self.dat.pwr_10hz = np.roll(self.dat.pwr_10hz, 1)
                    self.dat.pwr_10hz[0] = self.dat.pwr
                    
                    self.dat.rpm_10hz = np.roll(self.dat.rpm_10hz, 1)
                    self.dat.rpm_10hz[0] = self.dat.rpm
                    
                    self.dat.spd_10hz = np.roll(self.dat.spd_10hz, 1)
                    self.dat.spd_10hz[0] = self.dat.spd
                    
                    
                    # print("self.dat.pwr_10hz[{:d}] = {:0.4f}".format(self.dat.runTime_100ms,self.dat.pwr_10hz[self.dat.runTime_100ms]))

                    self.update_runTimer()

                    if self.dat.OneSecTick == True:  # -------------- One Hz Tasks --------------
                        self.do_OneSecTasks()

                    if self.dat.OneMinTick == True:  # -------------- One Min Tasks --------------
                        self.do_OneMinTasks()

                    if self.dat.OneHrTick == True:  # -------------- One Hr Tasks --------------
                        self.do_OneHrTasks()

                except Exception as e:
                    log("tenHz_timer_thread: " + str(e))

                self.updateGUI()
                sleep(0.1)

    # ---------------------------------------------------------------------------------------------------------------
    def do_OneSecTasks(self):
        self.dat.OneSecTick = False
        self.dat.UpdateBarHistPlot = True
        self.dat.pwr_sec = np.roll(self.dat.pwr_sec, 1)
        self.dat.rpm_sec = np.roll(self.dat.rpm_sec, 1)
        self.dat.spd_sec = np.roll(self.dat.spd_sec, 1)
        self.dat.calc_ttd(self.dat.rpm, self.dat.pack_amps, self.dat.pack_amp_hrs)

        if self.dat.active_notification == True:
            self.notification_icon.show()
            self.notification_textbox.show()

        if self.replaying_logfile == True:
            self.dat.pwr_sec[0] = self.dat.pwr
            self.dat.rpm_sec[0] = self.dat.rpm
            self.dat.spd_sec[0] = self.dat.spd
        else:
            self.dat.pwr_sec[0] = np.average(self.dat.pwr_10hz)
            self.dat.rpm_sec[0] = np.average(self.dat.rpm_10hz)
            self.dat.spd_sec[0] = np.average(self.dat.spd_10hz)

        if self.CANInterface != None:
            a_dataline = self.dat.get_SysLog_str('a')
            b_dataline = self.dat.get_SysLog_str('b')
            c_dataline = self.dat.get_SysLog_str('c')

            try:
                if self.a_data != a_dataline:
                    self.a_data = a_dataline
                    # log(a_dataline)
                    if self.sys_logging_enabled == True:
                        self.SysLog.write(a_dataline + '\n')
                if self.b_data != b_dataline:
                    self.b_data = b_dataline
                    # log(b_dataline)
                    if self.sys_logging_enabled == True:
                        self.SysLog.write(b_dataline + '\n')
                if self.c_data != c_dataline:
                    self.c_data = c_dataline
                    log(c_dataline)
                    if self.sys_logging_enabled == True:
                        self.SysLog.write(c_dataline + '\n')
                self.SysLog.flush()
            except Exception as e:
                log("ERROR: do_OneSecTask: write_SysLogfile - " + str(e))

        global log_window_buffer
        log_data = log_window_buffer
        log_window_buffer = ''
        end_iter = self.text_log_buffer.get_end_iter()
        self.text_log_buffer.insert(end_iter, log_data)
        position = self.scroll_window.get_vadjustment()
        position.set_value(position.get_upper())
        self.scroll_window.set_vadjustment(position)

    def do_OneMinTasks(self):

        try:
            self.dat.OneMinTick = False
            #log("OneMinTick")
            self.dat.pwr_min = np.roll(self.dat.pwr_min, 1)
            self.dat.pwr_min[0] = np.average(self.dat.pwr_sec)

            self.dat.rpm_min = np.roll(self.dat.rpm_min, 1)
            self.dat.rpm_min[0] = np.average(self.dat.rpm_sec)

            self.dat.spd_min = np.roll(self.dat.spd_min, 1)
            self.dat.spd_min[0] = np.average(self.dat.spd_sec)
            # log("pwr_min = {:04.2f}".format(float(self.dat.pwr_sec[self.dat.runTime_sec])) +
            #     ", rpm_min = {:04.0f}".format(float(self.dat.rpm_sec[self.dat.runTime_sec])) +
            #     ", spd_min = {:04.1f}".format(float(self.dat.spd_sec[self.dat.runTime_sec])))

        except Exception as e:
            log("ERROR: do_OneMinTasks: " + str(e))

    def do_OneHrTasks(self):

        try:
            self.dat.OneHrTick = False
            log("OneHrTick")
            self.dat.pwr_hrs = np.roll(self.dat.pwr_hrs, 1)
            self.dat.pwr_hrs[0] = np.average(self.dat.pwr_min)

            self.dat.rpm_hr = np.roll(self.dat.rpm_hr, 1)
            self.dat.rpm_hr[0] = np.average(self.dat.rpm_min)

            self.dat.spd_hr = np.roll(self.dat.spd_hr, 1)
            self.dat.spd_hr[0] = np.average(self.dat.spd_min)
            # log("pwr_min = {:04.2f}".format(float(self.dat.pwr_sec[self.dat.runTime_min])) +
            #     ", rpm_min = {:04.0f}".format(float(self.dat.rpm_sec[self.dat.runTime_min])) +
            #     ", spd_min = {:04.1f}".format(float(self.dat.spd_sec[self.dat.runTime_min])))

        except Exception as e:
            log("ERROR: do_OneHrTasks: " + str(e))

    # ---------------------------------------------------------------------------------------------------------------
    def update_runTimer(self):

        try:
            self.dat.runTime_100ms = self.dat.runTime_100ms + 1
            if self.dat.runTime_100ms % 10 == 0:
                self.dat.runTime_sec = self.dat.runTime_sec + 1
                self.dat.OneSecTick = True
                self.dat.runTime_100ms = 0
                if self.dat.runTime_sec % 60 == 0:
                    self.dat.runTime_min = self.dat.runTime_min + 1
                    self.dat.OneMinTick = True
                    self.dat.runTime_sec = 0
                    if self.dat.runTime_min % 60 == 0:
                        self.dat.runTime_hrs = self.dat.runTime_hrs + 1
                        self.dat.OneHrTick = True
                        self.dat.runTime_min = 0
        except Exception as e:
            log("update_runTime Error: " + str(e))

    # ------------------------------------ updateGUI --------------------------------------------------------------
    def updateGUI(self):

        try:
            #if self.dat.update_about_page == True:
                #self.dat.update_about_page = False
            GLib.idle_add(self.evms_sw_ver.set_label, self.sw_ver_evms)
            GLib.idle_add(self.data_sw_ver.set_label, self.dat.sw_ver_data)
            GLib.idle_add(self.can_sw_ver.set_label, self.evms_can.sw_ver_can)
            GLib.idle_add(self.map_sw_ver.set_label, self.mapPlots.sw_ver_maps)
            #GLib.idle_add(self.net_sw_ver.set_label, self.net.sw_ver_net)


            if self.dat.soc is not None and self.dat.soc != '':
                GLib.idle_add(self.lbl_Batt_val.set_label, "{:5.1f}".format(float(self.dat.soc)))
            if self.dat.mot_temp is not None and self.dat.mot_temp != '':
                GLib.idle_add(self.lbl_MotTemp_val.set_label, "{:3d}".format(self.dat.mot_temp))
            if self.dat.mot_ctrl_temp is not None and self.dat.mot_ctrl_temp != '':
                GLib.idle_add(self.lbl_CtlrTemp_val.set_label, "{:3d}".format(self.dat.mot_ctrl_temp))

            if self.dat.pack_amps is not None:
                GLib.idle_add(self.lbl_PackAmps_val.set_label, "{:d}".format(abs(self.dat.pack_amps)))
                GLib.idle_add(self.lbl_PackVolts_val.set_label, str(self.dat.pack_volts))
            if self.dat.ttd is not None:
                if self.dat.ttd < 0:
                    pass
                #don't update the value if the TTD is <0
                    # ttd_str = min(self.ttd_max, abs(self.dat.ttd))
                    # ttd_str = str(int(ttd_str)) + ':' + str(round((ttd_str % 1) * 60)).zfill(2)
                    # log("TTD: " + ttd_str)
                    #GLib.idle_add(self.lbl_TTD_val.set_label, ttd_str)
                    # GLib.idle_add(self.lbl_TTD.set_label, "TTD")
                else:
                    ttd_str = max(self.ttd_min, abs(self.dat.ttd))
                    ttd_str = str(int(ttd_str)) + ':' + str(round((ttd_str % 1) * 60)).zfill(2)
                    # log("TTD: " + ttd_str)
                    GLib.idle_add(self.lbl_TTD_val.set_label, ttd_str)
                    # GLib.idle_add(self.lbl_TTD.set_label, "TTC")
            else:
                # log("N/A")
                GLib.idle_add(self.lbl_TTD_val.set_label, " - ")

            if self.dat.date is not None and self.dat.date != '':
                GLib.idle_add(self.lbl_DATE_val.set_label, str(self.dat.date))
                GLib.idle_add(self.lbl_TIME_val.set_label, str(self.dat.time))

            if self.dat.latitude is not None and self.dat.latitude != '':
                GLib.idle_add(self.lbl_LAT_val.set_label, " {:11.7f}°".format(float(self.dat.latitude)))

            if self.dat.longitude is not None and self.dat.longitude != '':
                GLib.idle_add(self.lbl_LON_val.set_label, "{:11.7f}°".format(float(self.dat.longitude)))

            if self.dat.spd is not None and not self.dat.spd == '':
                GLib.idle_add(self.lbl_spd_val.set_label, "{:04.2f}".format(float(self.dat.spd)))

            if self.dat.rpm is not None:
                GLib.idle_add(self.lbl_rpm_val.set_label, "{:04.0f}".format(float(self.dat.rpm)))

            if self.dat.hdg is not None:
                GLib.idle_add(self.lbl_HDG_val.set_label, "{:04.1f}".format(float(self.dat.hdg)))
            else:
                GLib.idle_add(self.lbl_HDG_val.set_label, "---.-")

            pwr = self.dat.get_motor_pwr()[0]
            pwr = round(pwr, 1)
            if pwr is not None and pwr != '':
                GLib.idle_add(self.lbl_pwr_val.set_label, "{:04.2f}".format(abs(float(pwr))))

            ############## System On Time ###########
            if self.dat.get_runTime() is not None and self.dat.get_runTime() != '':
                GLib.idle_add(self.lbl_runTime_val.set_label, self.dat.get_runTime())

            ########### Set FORWARED or REVERSE label on Ring Gauge ######
            if self.dat.rpm is not None and self.dat.rpm != '':
                if self.dat.rpm > 2:
                    if (self.dat.rev_bit == True):
                        GLib.idle_add(self.lbl_fwd_rev_val.set_label, "REV")
                    else:
                        GLib.idle_add(self.lbl_fwd_rev_val.set_label, "FWD")
            else:
                GLib.idle_add(self.lbl_fwd_rev_val.set_label, " ")

            ############### CAN DATA TAB #################
            GLib.idle_add(self.lbl_eng_rpm.set_label, str(self.dat.mot_rpm))
            GLib.idle_add(self.lbl_eng_motTemp.set_label, str(self.dat.mot_temp))
            GLib.idle_add(self.lbl_eng_CtrlTemp.set_label, str(self.dat.mot_ctrl_temp))
            GLib.idle_add(self.lbl_eng_motAmps.set_label, str(self.dat.mot_amps))
            GLib.idle_add(self.lbl_eng_motVolts.set_label, str(self.dat.mot_volts))
            GLib.idle_add(self.lbl_eng_motStatFreq.set_label, str(self.dat.mot_stator_freq))
            GLib.idle_add(self.lbl_eng_ctrlFault1.set_label, str(self.dat.ctrl_fault_1))
            GLib.idle_add(self.lbl_eng_ctrlFault2.set_label, str(self.dat.ctrl_fault_2))
            GLib.idle_add(self.lbl_eng_throttleInput.set_label, str(self.dat.thrtl_inp))
            GLib.idle_add(self.lbl_eng_brakeInput.set_label, str(self.dat.brake_inp))
            GLib.idle_add(self.lbl_eng_econBit.set_label, str(self.dat.econ_bit))
            GLib.idle_add(self.lbl_eng_regenBit.set_label, str(self.dat.regen_bit))
            GLib.idle_add(self.lbl_eng_revBit.set_label, str(self.dat.rev_bit))
            GLib.idle_add(self.lbl_eng_brakeLightBit.set_label, str(self.dat.brake_light_bit))
            GLib.idle_add(self.lbl_eng_packLoCellV.set_label, str(self.dat.pack_lo_cell_v))
            GLib.idle_add(self.lbl_eng_packHiCellV.set_label, str(self.dat.pack_hi_cell_v))
            GLib.idle_add(self.lbl_eng_PackAvgCellV.set_label, str(self.dat.pack_avg_cell_v))
            GLib.idle_add(self.lbl_eng_packMaxCellNum.set_label, str(self.dat.pack_max_cell_num))
            GLib.idle_add(self.lbl_eng_packPopCells.set_label, str(self.dat.pack_pop_cells))
            GLib.idle_add(self.lbl_eng_dischRlyEnbl.set_label, str(self.dat.dsch_rly_enbl))
            GLib.idle_add(self.lbl_eng_chgRlyEnbl.set_label, str(self.dat.chg_rly_enbl))
            GLib.idle_add(self.lbl_eng_chgSftyEnbl.set_label, str(self.dat.chg_sfty_enbl))
            GLib.idle_add(self.lbl_eng_mlfctnIndActive.set_label, str(self.dat.mlfctn_ind_active))
            GLib.idle_add(self.lbl_eng_mltprpsInpSig.set_label, str(self.dat.multi_prps_inp_sig))
            GLib.idle_add(self.lbl_eng_alwaysOnSigStat.set_label, str(self.dat.alws_on_sig_stat))
            GLib.idle_add(self.lbl_eng_isRdySigStat.set_label, str(self.dat.is_rdy_sig_stat))
            GLib.idle_add(self.lbl_eng_charging.set_label, str(self.dat.charging))
            GLib.idle_add(self.lbl_eng_pack12v.set_label, str(self.dat.pack_12volt))
            GLib.idle_add(self.lbl_eng_packAmps.set_label, str(self.dat.pack_amps))
            GLib.idle_add(self.lbl_eng_packVolts.set_label, str(self.dat.pack_volts))
            GLib.idle_add(self.lbl_eng_packAh.set_label, str(self.dat.pack_amp_hrs))
            GLib.idle_add(self.lbl_eng_packHiTemp.set_label, str(self.dat.pack_hi_tmp))
            GLib.idle_add(self.lbl_eng_packLoTemp.set_label, str(self.dat.pack_lo_tmp))
            GLib.idle_add(self.lbl_eng_packSoc.set_label, str(self.dat.soc))
            GLib.idle_add(self.lbl_eng_packRes.set_label, str(self.dat.resistance))
            GLib.idle_add(self.lbl_eng_packHealth.set_label, str(self.dat.pack_hlth))
            GLib.idle_add(self.lbl_eng_packOpenV.set_label, str(self.dat.pack_open_v))
            GLib.idle_add(self.lbl_eng_packTotCyc.set_label, str(self.dat.pack_total_cyc))
            GLib.idle_add(self.lbl_eng_packCcl.set_label, str(self.dat.pack_ccl))
            GLib.idle_add(self.lbl_eng_packDcl.set_label, str(self.dat.pack_dcl))
            GLib.idle_add(self.lbl_eng_packMaxCellV.set_label, str(self.dat.pack_max_cell_v))
            GLib.idle_add(self.lbl_eng_packMinCellV.set_label, str(self.dat.pack_min_cell_v))
            GLib.idle_add(self.lbl_eng_pidRespMin.set_label, str(self.dat.pid_resp_min))
            GLib.idle_add(self.lbl_eng_pidRespMax.set_label, str(self.dat.pid_resp_max))
            GLib.idle_add(self.lbl_eng_pidFaultCnt.set_label, str(self.dat.pid_fault_cnt))
            GLib.idle_add(self.lbl_eng_pidErr1.set_label, str(self.dat.ctrl_fault_1))
            GLib.idle_add(self.lbl_eng_pidErr2.set_label, str(self.dat.ctrl_fault_2))
            GLib.idle_add(self.lbl_eng_gpsTime.set_label, str(self.dat.time))
            GLib.idle_add(self.lbl_eng_gpsDate.set_label, str(self.dat.date))

            if self.dat.latitude is not None and self.dat.latitude != '':
                GLib.idle_add(self.lbl_eng_latitude.set_label, str(" {:11.7f}°".format(float(self.dat.latitude))))
            if self.dat.longitude is not None and self.dat.longitude != '':
                GLib.idle_add(self.lbl_eng_longitude.set_label, str("{:11.7f}°".format(float(self.dat.longitude))))
            GLib.idle_add(self.lbl_eng_kts.set_label, str(self.dat.spd))
            GLib.idle_add(self.lbl_eng_hdg.set_label, str(self.dat.hdg))

            sys_datetime = datetime.utcnow()
            sys_datetime = sys_datetime - timedelta(microseconds=sys_datetime.microsecond)
            GLib.idle_add(self.lbl_eng_sysDatetime.set_label, str(sys_datetime))

            #GLib.idle_add(self.lbl_eng_timezone.set_label, tzname[0] + ' ' + tzname[1])
            GLib.idle_add(self.lbl_eng_offsetFromUtc.set_label, str(-timezone / 60 / 60))

        except Exception as e:
            log("updateGUI Error: " + str(e))

    # ----------------------------------------------- select_bar_history_type -----------------------------------

    def select_bar_history_type(self):
        self.bar_history_type = self.bar_history.get_active_text()

    # ----------------------------------------------- on_draw_sec_pwr_hist -----------------------------------

    def draw_bar_hist(self, da_pwr_hist, ctx_bar_hist, graph_var):

        max_y = self.dat.max_y_scale_bar_hist = 150

        if self.bar_history.get_active_text() == 'RPM':
            bar_max = self.max_rpm
            ctx_bar_hist.set_source_rgb(self.dat.rpm_R, self.dat.rpm_G, self.dat.rpm_B)
        elif self.bar_history.get_active_text() == 'Power':
            bar_max = self.max_pwr
            ctx_bar_hist.set_source_rgb(self.dat.pwr_R, self.dat.pwr_G, self.dat.pwr_B)
        elif self.bar_history.get_active_text() == 'Speed':
            bar_max = self.max_spd
            ctx_bar_hist.set_source_rgb(self.dat.spd_R, self.dat.spd_G, self.dat.spd_B)

        try:
            for idx, var_bin in enumerate(graph_var):
                x0 = self.dat.pwr_graph_x_ofst + self.dat.pwr_graph_width_pix - (idx * self.dat.pwr_bin_width)  - self.dat.pwr_bin_width
                y0 = max_y - self.dat.y_offset
                x1 = self.dat.pwr_bin_shade  # shaded part of bin
                y1 = -1 * abs(int(var_bin / bar_max * max_y))
                ctx_bar_hist.rectangle(x0, y0, x1, y1)
                ctx_bar_hist.fill()
        except Exception as e:
            print("update_power_history Error: " + str(e))


    def on_draw_pwr_hist_sec(self, da_pwr_hist, ctx_bar_hist):
        try:
            if self.bar_history.get_active_text() == 'RPM':
                graph_var = self.dat.rpm_sec
            elif self.bar_history.get_active_text() == 'Power':
                graph_var = self.dat.pwr_sec
            elif self.bar_history.get_active_text() == 'Speed':
                graph_var = self.dat.spd_sec

            self.draw_bar_hist(da_pwr_hist, ctx_bar_hist, graph_var)
        except Exception as e:
            log("on_draw_pwr_hist_sec ERROR: " + str(e))

    def on_draw_pwr_hist_min(self, da_pwr_hist, ctx_bar_hist):
        try:
            if self.bar_history.get_active_text() == 'RPM':
                graph_var = self.dat.rpm_min
            elif self.bar_history.get_active_text() == 'Power':
                graph_var = self.dat.pwr_min
            elif self.bar_history.get_active_text() == 'Speed':
                graph_var = self.dat.spd_min
            self.draw_bar_hist(da_pwr_hist, ctx_bar_hist, graph_var)
        except Exception as e:
            log("on_draw_pwr_hist_min ERROR: " + str(e))

    def on_draw_pwr_hist_hrs(self, da_pwr_hist, ctx_bar_hist):
        try:
            if self.bar_history.get_active_text() == 'RPM':
                graph_var = self.dat.rpm_hrs
            elif self.bar_history.get_active_text() == 'Power':
                graph_var = self.dat.pwr_hrs
            elif self.bar_history.get_active_text() == 'Speed':
                graph_var = self.dat.spd_hrs
            self.draw_bar_hist(da_pwr_hist, ctx_bar_hist, graph_var)
        except Exception as e:
            log("on_draw_pwr_hist_hrs ERROR: " + str(e))



        # --------------------------------------------------------- on_draw_gauge_key -------------------

    def on_draw_gauge_key(self, drawAreaGaugeKey, ctx_gauge_key):

        try:
            ctx_gauge_key.set_source_rgb(0.8, .8, .8)  # bar background color
            ctx_gauge_key.set_line_width(50)

            key_widget_height = 100

            ctx_gauge_key.rectangle(0, 0, 15, 15)
            ctx_gauge_key.set_source_rgb(self.dat.spd_R, self.dat.spd_G, self.dat.spd_B)
            ctx_gauge_key.fill()

            ctx_gauge_key.rectangle(0, 20, 15, 15)
            ctx_gauge_key.set_source_rgb(self.dat.rpm_R, self.dat.rpm_G, self.dat.rpm_B)
            ctx_gauge_key.fill()

            ctx_gauge_key.rectangle(0, 40, 15, 15)
            ctx_gauge_key.set_source_rgb(self.dat.pwr_R, self.dat.pwr_G, self.dat.pwr_B)
            ctx_gauge_key.fill()
        except Exception as e:
            log("Error - on_draw_gauge_key: " + str(e))

    # --------------------------------------------------------- draw ctrl temp bar -------------------
    def on_draw_mot_ctrl_temp(self, drawAreaCtrlTemp, ctx_ctrlTemp):

        try:
            ctx_ctrlTemp.set_source_rgb(0.8, .8, .8)  # bar background color
            ctx_ctrlTemp.set_line_width(50)
            
            gauge_width = 30
            top_right = 200  # mid-point startup condition until can data available.
            battery_widget_height = 400

            if self.dat.mot_ctrl_temp is not None:
                # log("SOC = " + str(self.data_holder.soc))
                top_right = battery_widget_height * int(self.dat.mot_ctrl_temp) / self.max_mot_ctrl_temp

                ctx_ctrlTemp.rectangle(0, 0, gauge_width, battery_widget_height)
                ctx_ctrlTemp.fill()

                ctx_ctrlTemp.set_source_rgb(self.dat.tmp_R, self.dat.tmp_B, self.dat.tmp_G)  # bar color
                if self.dat.mot_ctrl_temp >= int(self.ctrlr_temp_warn_threshold):
                    ctx_ctrlTemp.set_source_rgb(255, 140, 0)
                    if self.dat.mot_ctrl_temp >= int(self.ctrlr_temp_crit_threshold):
                        ctx_ctrlTemp.set_source_rgb(255, 0, 0)
                    ctx_ctrlTemp.set_line_width(6)  # bar color
                    ctx_ctrlTemp.move_to(0, 0)
                    ctx_ctrlTemp.line_to(gauge_width, 0)
                    ctx_ctrlTemp.stroke()
                    ctx_ctrlTemp.set_line_width(6)  # bar color
                    ctx_ctrlTemp.move_to(0, battery_widget_height)
                    ctx_ctrlTemp.line_to(gauge_width, battery_widget_height)
                    ctx_ctrlTemp.set_line_width(6)  # bar color
                    ctx_ctrlTemp.stroke()
                    ctx_ctrlTemp.move_to(0, 0)
                    ctx_ctrlTemp.line_to(0, battery_widget_height)
                    ctx_ctrlTemp.stroke()
                    ctx_ctrlTemp.set_line_width(6)  # bar color
                    ctx_ctrlTemp.move_to(gauge_width, 0)
                    ctx_ctrlTemp.line_to(gauge_width, battery_widget_height)
                    ctx_ctrlTemp.stroke()  # bar color
                    # ctx_batsoc.fill()

            ctx_ctrlTemp.rectangle(4, battery_widget_height - 4, gauge_width - 8, 4 - top_right)

            ctx_ctrlTemp.fill()
        except Exception as e:
            log("Exception - on_draw_mot_ctrl_tmp: " + str(e))

    # --------------------------------------------------------- draw motor temp bar -------------------
    def on_draw_mot_temp(self, drawAreaMotTemp, ctx_motTemp):

        try:
            ctx_motTemp.set_source_rgb(0.8, .8, .8)  # bar background color
            ctx_motTemp.set_line_width(50)

            gauge_width = 42
            top_right = 200  # mid-point startup condition until can data available.
            battery_widget_height = 400

            if self.dat.mot_temp is not None:
                # log("SOC = " + str(self.data_holder.soc))
                top_right = battery_widget_height * int(self.dat.mot_temp) / self.max_mot_temp
                ctx_motTemp.rectangle(0, 0, 55, battery_widget_height)
                ctx_motTemp.fill()

                ctx_motTemp.set_source_rgb(self.dat.tmp_R, self.dat.tmp_B, self.dat.tmp_G)  # bar color
                if self.dat.mot_temp >= int(self.mot_temp_warn_threshold):
                    ctx_motTemp.set_source_rgb(255, 140, 0)
                    if self.dat.mot_temp >= int(self.mot_temp_crit_threshold):
                        ctx_motTemp.set_source_rgb(255, 0, 0)
                    ctx_motTemp.set_line_width(6)  # bar color
                    ctx_motTemp.move_to(0, 0)
                    ctx_motTemp.line_to(gauge_width, 0)
                    ctx_motTemp.stroke()
                    ctx_motTemp.set_line_width(6)  # bar color
                    ctx_motTemp.move_to(0, battery_widget_height)
                    ctx_motTemp.line_to(gauge_width, battery_widget_height)
                    ctx_motTemp.set_line_width(6)  # bar color
                    ctx_motTemp.stroke()
                    ctx_motTemp.move_to(0, 0)
                    ctx_motTemp.line_to(0, battery_widget_height)
                    ctx_motTemp.stroke()
                    ctx_motTemp.set_line_width(6)  # bar color
                    ctx_motTemp.move_to(gauge_width, 0)
                    ctx_motTemp.line_to(gauge_width, battery_widget_height)
                    ctx_motTemp.stroke()  # bar color
                    # ctx_batsoc.fill()

            ctx_motTemp.rectangle(4, battery_widget_height - 4, 35, 4 - top_right)
            ctx_motTemp.fill()
        except Exception as e:
            log("Error - on_draw_mot_temp: " + str(e))

    # --------------------------------------------------------- draw battery SOC -------------------
    def on_draw_batt_soc(self, drawAreaBat, ctx_batsoc):

        try:

            ctx_batsoc.set_source_rgb(0.8, .8, .8)  # bar background color
            ctx_batsoc.set_line_width(50)

            battery_widget_height = 400
            top_right = 200  # mid-point startup condition until can data available.

            if self.dat.soc is not None:
                # log("SOC = " + str(self.data_holder.soc))
                top_right = (battery_widget_height - 4) * int(self.dat.soc) / 100
                ctx_batsoc.rectangle(0, 0, 112, battery_widget_height)
                ctx_batsoc.fill()
                ctx_batsoc.set_source_rgb(self.dat.bat_R, self.dat.bat_G, self.dat.bat_B)

                if self.dat.soc <= int(self.batt_warn_threshold):
                    ctx_batsoc.set_source_rgb(255, 140, 0)
                    if self.dat.soc <= int(self.batt_crit_threshold):
                        ctx_batsoc.set_source_rgb(255, 0, 0)
                    ctx_batsoc.set_line_width(6)# bar color
                    ctx_batsoc.move_to(0, 0)
                    ctx_batsoc.line_to(112, 0)
                    ctx_batsoc.stroke()
                    ctx_batsoc.set_line_width(6)  # bar color
                    ctx_batsoc.move_to(0, battery_widget_height)
                    ctx_batsoc.line_to(112, battery_widget_height)
                    ctx_batsoc.set_line_width(6)  # bar color
                    ctx_batsoc.stroke()
                    ctx_batsoc.move_to(0, 0)
                    ctx_batsoc.line_to(0, battery_widget_height)
                    ctx_batsoc.stroke()
                    ctx_batsoc.set_line_width(6)  # bar color
                    ctx_batsoc.move_to(112, 0)
                    ctx_batsoc.line_to(112, battery_widget_height)
                    ctx_batsoc.stroke()  # bar color
                    #ctx_batsoc.fill()

            ctx_batsoc.rectangle(4, battery_widget_height - 4, 104, 4 - top_right)
            ctx_batsoc.fill()
        except Exception as e:
            log("Error - on_draw_batt_soc: " + str(e))

    # -=======================================================-- draw ring gauge ---==============================----
    def on_draw_ring_gauge(self, da, ctx):

        radius = 275
        gaugeWidth = 1180 / 4
        line_width = radius / 6

        start_angle = pi * 0.7
        pwr_end_angle = start_angle
        spd_end_angle = start_angle
        rpm_end_angle = start_angle
        eff_end_angle = start_angle

        pegged = 0.8

        try:
            if self.dat.spd is not None:
                percent_spd = self.dat.spd / self.max_spd
                spd_end_angle = start_angle + min(0.99, percent_spd) * (2 * pi) * pegged  # max angle at 80% for speed

            if self.dat.rpm is not None:
                percent_rpm = self.dat.rpm / self.max_rpm
                if self.dat.rpm >= 0:
                    rpm_end_angle = start_angle + min(0.99, percent_rpm) * (2 * pi) * pegged
                else: # THE PROP IS SPINNING IN REVERSE
                    rpm_end_angle = start_angle - min(0.99, percent_rpm) * (2 * pi) * pegged

            if self.dat.pwr is not None:
                percent_pwr = self.dat.pwr / self.max_pwr
                if self.dat.pwr < 0:  # we're adding power to the battery
                    pwr_end_angle = start_angle - percent_pwr * (2 * pi) * pegged
                else:  # we're pulling power from the battery
                    pwr_end_angle = start_angle + percent_pwr * (2 * pi) * pegged
                if self.dat.spd is not None:
                    # NOTE: min(self.dat.pwr,.1) used for now, to limit eff angle
                    eff_end_angle = start_angle + self.dat.spd / max(self.dat.pwr * (2 * pi) * pegged, .1)

        except Exception as e:
            log("Error - on_draw_ring_gauge part 1: " + str(e))

        try:
            ########## gauge framework ##########
            ctx.set_source_rgb(0.1, 0.1, 0.1)
            ctx.set_line_width(1)

            ctx.arc(gaugeWidth,
                    radius,
                    radius * 0.4,
                    start_angle,
                    start_angle + 2 * pi * .8)
            ctx.stroke()

            ctx.set_source_rgb(0, 1, 0)  # green
            ctx.set_line_width(1)

            ctx.arc(gaugeWidth,
                    radius,
                    radius * 1,
                    start_angle,
                    eff_end_angle)

            ctx.stroke()

            # ctx.arc(self.x_cntr, self.y_cntr, radius=radius * 1.2, 0, 360, edgecolor='k', lw=2)

            ########## RING 1 : SPEED ##########
            ctx.set_source_rgb(self.dat.spd_R, self.dat.spd_G, self.dat.spd_B)
            ctx.set_line_width(line_width)
            ctx.set_tolerance(0.1)

            ctx.arc(gaugeWidth,
                    radius,
                    radius * 0.9,
                    start_angle,
                    spd_end_angle)
            ctx.stroke()

            # ctx.set_source_rgb(0.3, 0.4, 0.6)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()

            ########## RING 2 : RPM ##########

            if self.dat.rpm >= 0:
                ctx.set_source_rgb(self.dat.rpm_R, self.dat.rpm_G, self.dat.rpm_B)
            else:
                ctx.set_source_rgb(255, 0, 0)

            ctx.set_line_width(line_width)
            ctx.set_tolerance(0.1)

            ctx.arc(gaugeWidth,
                    radius,
                    radius * 0.7,
                    start_angle,
                    rpm_end_angle)
            ctx.stroke()

            # ctx.set_source_rgb(0.3, 0.4, 0.6)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()

            if self.dat.charging == 1:
                ctx.set_source_rgb(0, self.dat.pwr_G, 0)
                ctx.set_line_width(line_width)
                ctx.set_tolerance(0.1)

                ctx.arc(gaugeWidth,
                        radius,
                        radius * 0.5,
                        pwr_end_angle,
                        start_angle)
            ########## RING 3 : POWER ##########
            else:
                ctx.set_source_rgb(self.dat.pwr_R, self.dat.pwr_G, self.dat.pwr_B)
                ctx.set_line_width(line_width)
                ctx.set_tolerance(0.1)

                ctx.arc(gaugeWidth,
                        radius,
                        radius * 0.5,
                        start_angle,
                        pwr_end_angle)
            ctx.stroke()

            # ctx.set_source_rgb(0.3, 0.4, 0.6)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()
        except Exception as e:
            log("Error - on_draw_ring_gauge part 2: " + str(e))

    # def on_draw_instrument_frames (self, drawAreaInstrumentsFrame, ctx_instrements):
    #
    #     ctx_instrements.set_source_rgb(0.8, .8, .8)  # bar background color
    #     ctx_instrements.set_line_width(50)
    #
    #     key_widget_height = 100
    #
    #     ctx_instrements.rectangle(0, 0, 15, 15)
    #     ctx_instrements.set_source_rgb(self.dat.spd_R, self.dat.spd_G, self.dat.spd_B)
    #     ctx_instrements.fill()

    # ---------------------------------- Logging  ----------------------------------

    def print_can_column_headers(self):
        header_string = str('CAN bus columns are defined as:\n' +
                        'A_HEADER,date,time,lat,lon,spd,hdg,rpm,soc,ibat,vbat,motor_tmp,mot_ctrl_temp,' +
                        'pack_amp_hrs,thrtl_inp,brake_inp,mot_amps,rev,charging,econ_bit,regen_bit' + '\n'
                        'B_HEADER,pack_status,pack_hlth,pack_cycles,pack_open_v,pack_avg_cell_v,lo_cell_v,hi_cell_v,' +
                        'pack_lo_tmp,pack_hi_tmp,pack_max_cell_v,pack_min_cell_v,dsch_rly_enbl,chg_rly_enbl,chg_sfty_enbl,' +
                        'alws_on_sig_stat,is_rdy_sig_stat,pack_12volt,pack_limits,pack_ccl,pack_dcl,pack_max_cell_num,pack_pop_cells' + '\n'
                        'C_HEADER,pack_alert_status,mlfctn_ind_active,multi_ptps_inp_sig,pid_resp_min,' +
                        'pid_resp_max,pid_fault_cnt,pid_err_one,pid_err_two \n' )
        return header_string

    def init_AppLog(self):
        # setup time string with local time, to be used as base of logfile names
        log('\n\n*************** Newport Electric Boats, LLC ***************'
            + '\nEVMS App Logging Started: (rev ' + self.sw_ver_evms + ')\n\n')

        log('EVMS software version: ' + str(self.sw_ver_evms) +
              '\nMaps version: ' + self.mapPlots.sw_ver_maps +
              '\nDat version: '  + self.dat.sw_ver_data +
              '\nCan version: '  + self.evms_can.sw_ver_can + '\n\n')

        self.SysLogName = 'logs/' + self.appStartDateString + '_evms_system.log'
        self.CANLogName = 'logs/' + self.appStartDateString + '_evms_can.log'
        self.GPSLogName = 'logs/' + self.appStartDateString + '_evms_gps.log'
        log('SystemLog = ' + str(self.SysLogName))

        try:
            log(self.print_can_column_headers())

        except Exception as e:
            log("init_AppLog ERROR: " + str(e))

    def init_SysLog(self):
        # setup time string with local time, to be used as base of logfile names
        try:
            if os.path.exists(self.SysLogName):
                add_header = False
            else:
                add_header = True

            self.SysLog = open(self.SysLogName, 'a+')
            if add_header:
                self.SysLog.write(self.print_can_column_headers())

        except Exception as e:
            log("init_SysLog ERROR: " + str(e))

    # --------------------------------------------------------------------------------------------------------
    def init_gps_serial(self):

        for name in self.gps_ports:
            log("Checking for GPS on %s at %u baud" % (name, self.gps_baudrate))
            try:
                if len(self.gps_ports) == 1:
                    self.gpsPort = open(self.gps_ports[0], 'r+')
                else:
                    self.gpsPort = serial.Serial(name, self.gps_baudrate, timeout=self.SER_TIMEOUT)
                    # gpsPort = serial.Serial(name, baud)
                    # sleep(SER_TIMEOUT * 1.2)
                    self.gpsPort.flushInput()
                log("GPS found and connected on " + name)
                break
            except Exception as e:
                # self.status_msg.emit("Can't open port " + name)
                log("     not found at " + name)
                self.gpsPort = None
                pass
        if not self.gpsPort:
            self.dat.debugging = True
            log("GPS not found on EVMS...")

    def parse_gps_message(self, s):

        try:
            msg = pynmea2.parse(s)
            if msg.sentence_type == 'RMC':
                # An example RMC sentence is shown below:
                # $GPRMC, 210230, A, 3855.4487, N, 09446.0071, W, 0.0, 076.2, 130495, 003.8, E * 69
                # The sentence contains the following fields:
                # The sentence type
                # Current time( if available; UTC)
                # Position status(A for valid, V for invalid)
                # Latitude( in DDMM.MMM format)
                # Latitude compass direction
                # Longitude( in DDDMM.MMM format)
                # Longitude compass direction
                # Speed( in knots per hour)
                # Heading
                # Date(DDMMYY)
                # Magnetic variation
                # Magnetic variation direction
                # The checksum validation value( in hexadecimal)

                # log(msg)
                if msg.datestamp != None:
                    self.dat.date = msg.datestamp
                    from_zone = tz.tzutc()
                    to_zone = tz.tzlocal()
                    utc = datetime.strptime(str(msg.timestamp), '%H:%M:%S')
                    utc = utc.replace(tzinfo=from_zone)
                    local_time = utc.astimezone(to_zone)
                    local_time = local_time.time()
                    self.dat.time = local_time
                    self.dat.gps_datetime = str(msg.datestamp) + ',' + str(local_time)
                    self.dat.lat = msg.lat
                    self.dat.lon = msg.lon
                    self.dat.spd = msg.spd_over_grnd
                    self.dat.hdg = msg.true_course
                    self.dat.true_course = msg.true_course
                # self.dat.magnetic_variation = msg.s

                self.dat.latitude = msg.latitude
                self.dat.longitude = msg.longitude

                # log(self.dat.lat)
                # log(self.dat.lon)
                # log(self.dat.magnetic_variation)

                # log('self.dat.latitude = msg.latitude = ' + str(self.dat.latitude))
                # log('self.dat.longitude = msg.longitude = ' + str(self.dat.longitude))

        except Exception as e:  # pynmea2.nmea.ChecksumError:
            self.dat.gps_parse_error_count = self.dat.gps_parse_error_count + 1
            #log("parse_gps_message: " + str(e))


    def gps_readline(self):

        if self.gpsPort is not None:
            try:
                s = self.gpsPort.readline()
                if self.gps_logging_enabled == True:
                    self.GPSLog.write(s) #send raw gps sentence to gps logfile

                if self.gps_from_file == True:
                    first_chr = s[0]
                else:
                    first_chr = chr(s[0])
                if self.gps_from_file == True:
                    if s[3:6] != 'RMC':
                        return
                    else:
                        sleep(1)
                if self.gps_logging_enabled == True:
                    # log('gps_readline: ' + str(s))
                    if self.GPSLog != None:
                        if self.gps_from_file == False:
                            self.GPSLog.write(s.decode('utf-8'))
                        elif s != '' and s != '\n' and s[0] == '$':
                            self.GPSLog.write(s)
                if s != '' and s != '\n' and first_chr == '$':  # Get data from serial port
                    s = s.strip()
                    if self.gps_from_file == False:
                        s = s.decode('utf-8')
                    self.parse_gps_message(s)
                    #log('DEBUG ' + "gps_readline, parsed GPS: " + str(s))
                else:
                    if self.gps_from_file == False:
                        pass
                        #log("NMEA Parse ERROR : " + s.decode('utf-8'))
            except Exception as e:
                log("Exception gps_readline: " + str(e))
                gpsPort = None
        else:
            sleep(5)
            log('GPS connection failed. Rechecking.')
            self.init_gps_serial()

    def init_can_interface(self):

        log("Opening CAN interface: " + str(self.can_if_name))
        try:
            self.CANInterface = can.interface.Bus(channel=self.can_if_name, bustype='socketcan_ctypes', timeout=1)
            log("CAN interface opened.")
        except Exception as e:
            log("Exception init_can_interface: " + str(e))

    # -------------------------------thread functions -------------------------------------------------------
    def gps_reader_thread(self):

        try:
            log("starting GPS thread")
            while True:
               self.gps_readline()

        except Exception as e:
            log("Exception gps_reader_thread: " + str(e))

    def can_reader_thread(self, interface):

        try:
            log("starting CAN thread")
            while True:
                self.evms_can.can_read_data(interface, self.dat)
        except Exception as e:
            log("Exception can_reader_thread: " + str(e))


# ---------------------------------------- main ----------------------------------------------
if __name__ == "__main__":
    try:
        app = App()
    except Exception as e:
        print(e)
