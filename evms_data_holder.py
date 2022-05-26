######################################################################################################################
#
#   Copyright (c) 2022 Newport Electric Boats, LLC. All rights reserved.
#   Electric Vessel Management System (EVMS)
#   Filename: evms_data_holder.py
#
######################################################################################################################

import numpy as np

class DataHolder:
    def __init__(self):
        self.sw_ver_data = "0.3.2"
        self.ac1239_status_1 = ""
        self.rpm = None
        self.mot_rpm = None
        self.mot_temp = None
        self.mot_ctrl_temp = None
        self.mot_amps = None
        self.mot_volts = None

        self.ac1239_status_2 = ""
        self.mot_stator_freq = None
        self.ctrl_fault_1 = None
        self.ctrl_fault_2 = None
        self.thrtl_inp = None
        self.brake_inp = None
        self.econ_bit = None
        self.regen_bit = None
        self.rev_bit = None
        self.brake_light_bit = None

        self.pack_cell_status = ""
        self.pack_lo_cell_v = None
        self.pack_hi_cell_v = None
        self.pack_avg_cell_v = None
        self.pack_max_cell_num = None
        self.pack_pop_cells = None
        self.pack_cycles = None

        self.pack_alert_status = ""
        self.dsch_rly_enbl = None
        self.chg_rly_enbl = None
        self.chg_sfty_enbl = None
        self.mlfctn_ind_active = None
        self.multi_prps_inp_sig = None
        self.alws_on_sig_stat = None
        self.is_rdy_sig_stat = None
        self.charging = None
        self.pack_12volt = None

        self.pack_critical_data = ""
        self.pack_amps = None
        self.pack_volts = None
        self.pack_amp_hrs = None
        self.pack_hi_tmp = None
        self.pack_lo_tmp = None

        self.pack_status = ""
        self.soc = None
        self.resistance = None
        self.pack_hlth = None
        self.pack_open_v = None
        self.pack_total_cyc = None

        self.pack_limits = ""
        self.pack_ccl = None
        self.pack_dcl = None
        self.pack_max_cell_v = None
        self.pack_min_cell_v = None

        self.pack_error_responses = ""
        self.pid_resp_min = None
        self.pid_resp_max = None
        self.pid_fault_cnt = None
        self.pid_err_one = None
        self.pid_err_two = None

        self.pack_cell_broadcast = ""

        self.time = None
        self.date = None
        self.gps_datetime = None
        self.lat = None
        self.lon = None
        self.spd = None
        self.hdg = None
        self.latitude = None
        self.longitude = None

        #self.update_about_page = True

        ########## RUNTIME VARIABLES ##########
        self.runTime = None
        self.runTime_100ms = 0
        self.runTime_sec = 0
        self.runTime_min = 0
        self.runTime_hrs = 0

        ########## TTD VARIABLES ##########
        self.ttd = None
        self.rpm_threshold = 100
        self.avging_time_s = 60
        self.datapoints_needed = 15
        self.valid_datapoints = 0
        self.amps_running_avg = None
        self.a = 0.9
        self.b = 0.1

        ########## Colors for gauges, battery, motor temp ###############
        self.spd_R = 0.2
        self.spd_G = 0.8
        self.spd_B = 0.99

        self.rpm_R = 0.1
        self.rpm_G = 0.5
        self.rpm_B = 0.99

        self.pwr_R = 0.2
        self.pwr_G = 0.3
        self.pwr_B = 0.99

        self.bat_R = 0.2
        self.bat_G = 0.3
        self.bat_B = 0.99

        self.tmp_R = 0.1
        self.tmp_G = 0.1
        self.tmp_B = 0.1

        # ------------------ Bar History Calculations -------------------
        self.UpdateBarHistPlot = False
        self.OneSecTick = False
        self.OneMinTick = False
        self.OneHrTick = False

        self.pwr = 0
        self.rpm = 0
        self.spd = 0
        self.max_y_scale_bar_hist = 150

        self.pwr_10hz = np.zeros(10)
        self.pwr_sec = np.zeros(60)
        self.pwr_min = np.zeros(60)
        self.pwr_hrs = np.zeros(60)
        self.rpm_10hz = np.zeros(10)
        self.rpm_sec = np.zeros(60)
        self.rpm_min = np.zeros(60)
        self.rpm_hr = np.zeros(60)
        self.spd_10hz = np.zeros(10) #
        self.spd_sec = np.zeros(60)
        self.spd_min = np.zeros(60)
        self.spd_hr = np.zeros(60)


        # ---------------- GUI logging checkboxes ------------------------
        self.chk_can_logging = False
        self.chk_gps_logging = False

        self.active_notification = False
        self.dataholder_log = ''

    def get_dataholder_log(self):
        return self.dataholder_log

    def clear_dataholder_log(self):
        self.dataholder_log = ''

    def log_dataholder(self, logstring):
        self.dataholder_log = self.dataholder_log + "DH: " + logstring + "\n"

    def get_SysLog_str(self, type):

        try:
            if type == 'a':
                #tmp_str = str(self.gps_datetime)
                tmp_str = type
                tmp_str += ',' + str(self.date)
                tmp_str += ',' + str(self.time)
                tmp_str += ',' + str(self.latitude) #keep these this way (DD.dddddd)
                tmp_str += ',' + str(self.longitude)#keep these this way (DD.dddddd)
                tmp_str += ',' + str(self.spd)
                tmp_str += ',' + str(self.hdg)
                tmp_str += ',' + str(self.rpm)
                tmp_str += ',' + str(self.soc)
                tmp_str += ',' + str(self.pack_amps)
                tmp_str += ',' + str(self.pack_volts)
                tmp_str += ',' + str(self.mot_temp)
                tmp_str += ',' + str(self.mot_ctrl_temp)
                tmp_str += ',' + str(self.pack_amp_hrs)
                tmp_str += ',' + str(self.thrtl_inp)
                tmp_str += ',' + str(self.brake_inp)
                tmp_str += ',' + str(self.mot_amps)
                tmp_str += ',' + str(self.rev_bit)
                tmp_str += ',' + str(self.charging)
                tmp_str += ',' + str(self.econ_bit)
                tmp_str += ',' + str(self.regen_bit)
            elif type == 'b':
                tmp_str = type
                tmp_str += ',' + str(self.pack_status)
                tmp_str += ',' + str(self.pack_hlth)
                tmp_str += ',' + str(self.pack_cycles)
                tmp_str += ',' + str(self.pack_open_v)
                tmp_str += ',' + str(self.pack_avg_cell_v)
                tmp_str += ',' + str(self.pack_lo_cell_v)
                tmp_str += ',' + str(self.pack_hi_cell_v)
                tmp_str += ',' + str(self.pack_lo_tmp)
                tmp_str += ',' + str(self.pack_hi_tmp)
                tmp_str += ',' + str(self.pack_max_cell_v)
                tmp_str += ',' + str(self.pack_min_cell_v)
                tmp_str += ',' + str(self.dsch_rly_enbl)
                tmp_str += ',' + str(self.chg_rly_enbl)
                tmp_str += ',' + str(self.chg_sfty_enbl)
                tmp_str += ',' + str(self.alws_on_sig_stat)
                tmp_str += ',' + str(self.is_rdy_sig_stat)
                tmp_str += ',' + str(self.pack_12volt)
                tmp_str += ',' + str(self.pack_limits)
                tmp_str += ',' + str(self.pack_ccl)
                tmp_str += ',' + str(self.pack_dcl)
                tmp_str += ',' + str(self.pack_max_cell_num)
                tmp_str += ',' + str(self.pack_pop_cells)
            elif type == 'c':
                tmp_str = type
                tmp_str += ',' + str(self.pack_alert_status)
                tmp_str += ',' + str(self.mlfctn_ind_active)
                tmp_str += ',' + str(self.multi_prps_inp_sig)
                tmp_str += ',' + str(self.pid_resp_min)
                tmp_str += ',' + str(self.pid_resp_max)
                tmp_str += ',' + str(self.pid_fault_cnt)
                tmp_str += ',' + str(self.pid_err_one)
                tmp_str += ',' + str(self.pid_err_two)
        except Exception as e:
            self.log_dataholder("DataHolderError get_data_str: " + str(e))
        return tmp_str

    def get_motor_pwr(self):
        try:
            if (not self.pack_amps == None) and (not self.pack_volts == None):
                kw = self.pack_amps * self.pack_volts / -1000.0
                hp = self.pack_amps * self.pack_volts / -746.0
                #log_dataholder("kw: {:.2f}  hp: {:.2f}".format(kw, hp))
                return kw, hp
            else:
                return 0, 0
        except Exception as e:
            self.log_dataholder("DataHolderError get_motor_pwr: at line 109" + str(e))

    def calc_ttd(self, rpm, amps, ah):
        try:
            if  (rpm  is not None and rpm  != "") and \
                (amps is not None and amps != "") and \
                (ah   is not None and ah   != ""):

                # datapoint is only valid if RPM is over 100
                if rpm > self.rpm_threshold:
                    self.valid_datapoints += 1
                    if self.amps_running_avg == None:
                        self.amps_running_avg = amps
                    else:
                        self.amps_running_avg = self.amps_running_avg * self.a + amps * self.b
                    if self.valid_datapoints >= self.datapoints_needed:
                        self.ttd = round(ah / max(.05,self.amps_running_avg, 1)) #preventing div by zero...
                else:
                    self.valid_datapoints = 0
                    self.amps_running_avg = None
        except Exception as e:
            log_dataholder("calc_ttd ERROR: " + str(e))

    def get_runTime(self):
        try:
            self.runTime = "{:02d}".format(self.runTime_hrs) + \
                           ":{:02d}".format(self.runTime_min) + \
                           ":{:02d}".format(self.runTime_sec)
            return self.runTime

        except Exception as e:
            log_dataholder("dataHolderError: get_runTime():" + str(e))




