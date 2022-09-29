######################################################################################################################
#
#   Copyright (c) 2022 Newport Electric Boats, LLC. All rights reserved.
#   Electric Vessel Management System (EVMS)
#   Filename: evms_can.py
#
######################################################################################################################

import serial, can
from can import Message
#from evms_data_holder import DataHolder
import logging
import sys

# --- GLOBAL Variables -----
#sw_ver_can = "0.9.4"

class evms_can:
    def __init__(self, applog, buffer):
        self.sw_ver_can = "1.0.0"
        self.applog = applog
        self.buffer = buffer
        logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, handlers=[
            logging.FileHandler(applog),
            logging.StreamHandler(sys.stdout)])


    def log(self, message):
        global log_window_buffer
        self.buffer += message + '\n'
        logging.info(message)

    # def can_write_data(self, canInterface: can.interface.Bus, message):
    #     canInterface.send(1)

    def can_send_select_LFP(self, canInterface: can.interface.Bus,on_off):

        enable_LFP1 = Message(arbitration_id=0x701, is_extended_id=True, data=[on_off]) #, 0x1, 0x2, 0x3])
        #print(enable_LFP1)
        #self.log("sending CAN message: " + str(enable_LFP1))
        canInterface.send(enable_LFP1)


    def can_read_data(self, canInterface: can.interface.Bus, v_dat):

        message = canInterface.recv(1)
        #print(str(message.arbitration_id) + " " + str(message.data))
        if message is None:
            # print('No CAN message was received')
            pass
        elif message.arbitration_id == 1537:  ## AC1239 STATUS 1
            tmp_str = ''
            for i in message.data:
                tmp_str += hex(i) + ' '
            if tmp_str != v_dat.ac1239_status_1:
                v_dat.ac1239_status_1 = tmp_str
                # Get motor_rpm from bits 7 through 22 (16 bits)
                motor_rpm = message.data[0]
                motor_rpm = motor_rpm << 8
                motor_rpm = motor_rpm | message.data[1]
                v_dat.mot_rpm = motor_rpm
                prop_rpm = motor_rpm / 2
                v_dat.rpm = prop_rpm
                ##### Get motor_temp from bits 23 through 30 (8 bits) #####
                motor_temp = message.data[2]
                v_dat.mot_temp = motor_temp
                ##### Get motor_controller_temp bits from bits 31 through 38 (8 bits) #####
                motor_controller_temp = message.data[3]
                motor_controller_temp = self.uint8_to_int8(motor_controller_temp)
                v_dat.mot_ctrl_temp = motor_controller_temp
                ##### Get motor_amps bits #####
                motor_amps = message.data[4]
                motor_amps = motor_amps << 8
                motor_amps = motor_amps | message.data[5]
                motor_amps = motor_amps * 0.1
                v_dat.mot_amps = round(motor_amps, 1)
                ##### Get motor_volt #####
                motor_volt = message.data[6]
                motor_volt = motor_volt << 8
                motor_volt = motor_volt | message.data[7]
                motor_volt = motor_volt * 0.1
                v_dat.mot_volts = round(motor_volt, 2)
        elif message.arbitration_id == 1538:  ## AC1239 STATUS 2
            tmp_str = ''
            for i in message.data:
                tmp_str += bin(i) + ' '
            if tmp_str != v_dat.ac1239_status_2:
                v_dat.ac1239_status_2 = tmp_str
                ### Get motor_stator_frequency bytes #####
                motor_stator_frequency = (message.data[0] << 8) | message.data[1]
                motor_stator_frequency = self.uint16_to_int16(motor_stator_frequency)
                v_dat.mot_stator_freq = motor_stator_frequency
                ### Get controller_fault_primary byte #####
                controller_fault_primary = message.data[2]
                v_dat.ctrl_fault_1 = controller_fault_primary
                #### Get controller_fault_secondary byte #####
                controller_fault_secondary = message.data[3]
                v_dat.ctrl_fault_2 = controller_fault_secondary
                #### Get throttle_input byte #####
                throttle_input = message.data[4]
                v_dat.thrtl_inp = throttle_input
                #### Get brake_input byte #####
                brake_input = message.data[5]
                v_dat.brake_inp = brake_input
                #### Get economy_bit (48) #####
                economy_bit = (message.data[6] & 0b00010000) >> 4
                v_dat.econ_bit = economy_bit
                ### Get regen_bit (49) #####
                regen_bit = (message.data[6] & 0b00001000) >> 3
                v_dat.regen_bit = regen_bit
                ### Get reverse_bit (50) #####
                reverse_bit = (message.data[6] & 0b00000100) >> 2
                v_dat.rev_bit = reverse_bit
                ### Get brake_light_bit (51) #####
                brake_light_bit = (message.data[6] & 0b00000010) >> 1
                v_dat.brake_light_bit = brake_light_bit
        elif message.arbitration_id == 1617:  ## PACK CELL STATUS
            tmp_str = ''
            for i in message.data:
                tmp_str += hex(i) + ' '
            if tmp_str != v_dat.pack_cell_status:
                v_dat.pack_cell_status = tmp_str
                #### get pack_low_cell_volt bytes #####
                pack_low_cell_volt = (message.data[1] << 8) | message.data[0]
                pack_low_cell_volt = self.uint16_to_int16(pack_low_cell_volt)
                pack_low_cell_volt = pack_low_cell_volt * 0.001
                v_dat.pack_lo_cell_v = round(pack_low_cell_volt, 2)
                ### get pack_high_cell_volt bytes #####
                pack_high_cell_volt = (message.data[3] << 8) | message.data[2]
                pack_high_cell_volt = self.uint16_to_int16(pack_high_cell_volt)
                pack_high_cell_volt = pack_high_cell_volt * 0.001
                v_dat.pack_hi_cell_v = round(pack_high_cell_volt, 2)
                #### get pack_avg_volt bytes #####
                pack_avg_cell_volt = (message.data[5] << 8) | message.data[4]
                pack_avg_cell_volt = self.uint16_to_int16(pack_avg_cell_volt)
                pack_avg_cell_volt = pack_avg_cell_volt * 0.001
                v_dat.pack_avg_cell_v = pack_avg_cell_volt
                ### get pack_max_cell_number byte #####
                pack_max_cell_number = message.data[6]
                v_dat.pack_max_cell_num = pack_max_cell_number
                ### get pack_populated_cells byte #####
                pack_populated_cells = message.data[7]
                v_dat.pack_pop_cells = pack_populated_cells
        elif message.arbitration_id == 1619:  ## PACK ALERT STATUS
            tmp_str = ''
            for i in message.data:
                tmp_str += hex(i) + ' '
            if tmp_str != v_dat.pack_alert_status:
                v_dat.pack_alert_status = tmp_str
                # Get discharge_relay_enabled alert bit
                discharge_relay_enabled = message.data[0]
                discharge_relay_enabled = (discharge_relay_enabled & 0b00000001)
                v_dat.dsch_rly_enbl = discharge_relay_enabled
                # Get charge_relay_enabled alert bit
                charge_relay_enabled = message.data[0]
                charge_relay_enabled = (charge_relay_enabled & 0b00000010) >> 1
                v_dat.chg_rly_enbl = charge_relay_enabled
                # Get charge_safety_enabled alert bit
                charge_safety_enabled = message.data[0]
                charge_safety_enabled = (charge_safety_enabled & 0b00000100) >> 2
                v_dat.chg_sfty_enbl = charge_safety_enabled
                # Get malfunction_indicator_active alert bit
                malfunction_indicator_active = message.data[0]
                malfunction_indicator_active = (malfunction_indicator_active & 0b00001000) >> 3
                v_dat.mlfctn_ind_active = malfunction_indicator_active
                # Get multi_purpose_input_signal alert bit
                multi_purpose_input_signal = message.data[0]
                multi_purpose_input_signal = (multi_purpose_input_signal & 0b00010000) >> 4
                v_dat.multi_prps_inp_sig = multi_purpose_input_signal
                # Get always_on_signal_status alert bit
                always_on_signal_status = message.data[0]
                always_on_signal_status = (always_on_signal_status & 0b00100000) >> 5
                v_dat.alws_on_sig_stat = always_on_signal_status
                # Get is_ready_signal_status alert bit
                is_ready_signal_status = message.data[0]
                is_ready_signal_status = (is_ready_signal_status & 0b01000000) >> 6
                v_dat.is_rdy_sig_stat = is_ready_signal_status
                # Get is_charging_signal_status alert bit
                is_charging_signal_status = message.data[0]
                is_charging_signal_status = (is_charging_signal_status & 0b10000000) >> 7
                v_dat.charging = is_charging_signal_status
                # Get pack_12_v bits
                pack_12v = (message.data[2] << 8) | message.data[1]
                pack_12v = self.uint16_to_int16(pack_12v)
                pack_12v = pack_12v * 0.1
                v_dat.pack_12volt = pack_12v
        elif message.arbitration_id == 336:  ## PACK CRITICAL DATA
            tmp_str = ''
            for i in message.data:
                tmp_str += hex(i) + ' '
            if tmp_str != v_dat.pack_critical_data:
                v_dat.pack_critical_data = tmp_str
                # get ibat from first two data bytes
                pack_ibat = message.data[1]
                pack_ibat = pack_ibat << 8
                pack_ibat = pack_ibat | message.data[0]
                pack_ibat = self.uint16_to_int16(pack_ibat) * -1
                v_dat.pack_amps = pack_ibat
                # dataline.ibat = str(pack_ibat)
                # get vbat from 3rd & 4th data bytes
                pack_vbat = message.data[3]
                pack_vbat = pack_vbat << 8
                pack_vbat = pack_vbat | message.data[2]
                pack_vbat = self.uint16_to_int16(pack_vbat) / 10
                v_dat.pack_volts = pack_vbat
                # get ah from 5th and 6th data bytes
                pack_ah = message.data[5]
                pack_ah = pack_ah << 8
                pack_ah = pack_ah | message.data[4]
                v_dat.pack_amp_hrs = pack_ah
                # get high_temp from 7th data byte
                pack_high_temp = message.data[6]
                v_dat.pack_hi_tmp = pack_high_temp
                # get low_temp from 8th data byte
                pack_low_temp = message.data[7]
                v_dat.pack_lo_tmp = pack_low_temp
        elif message.arbitration_id == 1616:  ## PACK STATUS
            tmp_str = ''
            for i in message.data:
                tmp_str += hex(i) + ' '
            if tmp_str != v_dat.pack_status:
                v_dat.pack_status = tmp_str
                # get pack_soc from 1st data byte
                pack_soc = message.data[0] / 2
                v_dat.soc = pack_soc
                # get resistance from 2nd and 3rd byte
                pack_resistance = message.data[2]
                pack_resistance = pack_resistance << 8
                pack_resistance = pack_resistance | message.data[1]
                v_dat.resistance = pack_resistance
                # get health from 4th byte
                pack_health = message.data[3]
                v_dat.pack_hlth = pack_health
                # get open_vbat from 5th and 6th byte
                pack_open_vbat = message.data[5]
                pack_open_vbat = pack_open_vbat << 8
                pack_open_vbat = pack_open_vbat | message.data[4]
                v_dat.pack_open_v = pack_open_vbat
                # get total_cycles from 7th and 8th byte
                pack_total_cycles = message.data[7]
                pack_total_cycles = pack_total_cycles << 8
                pack_total_cycles = pack_total_cycles | message.data[6]
                v_dat.pack_total_cyc = pack_total_cycles
        elif message.arbitration_id == 1618:  ## PACK LIMITS
            tmp_str = ''
            for i in message.data:
                tmp_str += hex(i) + ' '
            if tmp_str != v_dat.pack_limits:
                v_dat.pack_limits = tmp_str
                # get pack_ccl byte
                pack_ccl = (message.data[1] << 8) | message.data[0]
                pack_ccl = self.uint16_to_int16(pack_ccl)
                v_dat.pack_ccl = pack_ccl
                # get pack_dcl byte
                pack_dcl = (message.data[3] << 8) | message.data[2]
                pack_dcl = self.uint16_to_int16(pack_dcl)
                v_dat.pack_dcl = pack_dcl
                # get pack_max_cell_volt bytes
                pack_max_cell_volt = (message.data[5] << 8) | message.data[4]
                pack_max_cell_volt = self.uint16_to_int16(pack_max_cell_volt)
                pack_max_cell_volt = pack_max_cell_volt * 0.001
                pack_max_cell_volt = round(pack_max_cell_volt, 3)
                v_dat.pack_max_cell_v = pack_max_cell_volt
                # get pack_min_cell_volt bytes
                pack_min_cell_volt = (message.data[7] << 8) | message.data[6]
                pack_min_cell_volt = self.uint16_to_int16(pack_min_cell_volt)
                pack_min_cell_volt = pack_min_cell_volt * 0.001
                pack_min_cell_volt = round(pack_min_cell_volt, 3)
                v_dat.pack_min_cell_v = pack_min_cell_volt
        elif message.arbitration_id == 2027:  ## PACK ERROR RESPONSES
            tmp_str = ''
            for i in message.data:
                tmp_str += hex(i) + ' '
            if tmp_str != v_dat.pack_error_responses:
                v_dat.pack_error_responses = tmp_str
                self.log("PACK ERROR RESPONSE: " + v_dat.pack_error_responses)
                # parse CAN message
                pid_response_min = message.data[1]
                v_dat.pid_resp_min = pid_response_min
                pid_response_max = message.data[2]
                v_dat.pid_resp_max = pid_response_max
                pid_fault_count = message.data[3]
                v_dat.pid_fault_cnt = pid_fault_count
                pid_error_one = (message.data[5] << 8) | message.data[4]
                v_dat.pid_err_one = pid_error_one
                pid_error_two = (message.data[7] << 8) | message.data[6]
                v_dat.pid_err_two = pid_error_two
                return "PACK ERROR RESPONSE: " + v_dat.pack_error_responses
        elif message.arbitration_id == 54: #51:  ## PACK CELL BROADCAST
            tmp_str = ''
            for i in message.data:
                tmp_str += hex(i) + ' '               #https://andromedaint.atlassian.net/wiki/spaces/DOC/pages/28737773/CAN+Messaging+Maps
            if tmp_str != v_dat.pack_cell_broadcast:  #http://socialledge.com/sjsu/index.php/DBC_Format
                v_dat.pack_cell_broadcast = tmp_str
                self.cell_id = message.data[0]   #: 0 | 8 @ 1 + (1, 0)[0 | 0]
                self.cell_checksum = message.data[1]  #: 56 | 8 @ 1 - (1, 0)[0 | 0]
                self.cell_open_volt = message.data[1]  #: 47 | 16 @ 0 - (0.0001, 0)[-6 | 6]
                self.cell_internal_resist = message.data[1]  #: 31 | 16 @ 0 - (1E-005, 0)[0 | 0]
                self.cell_inst_volt = message.data[1]
                #print(tmp_str)

        #         cell_ID = message.data[0]
        #         packCellBroadcastLst.append(cell_ID)
        #         ###### Send message to main display thread #####i
        #         writePackCellBroadcast.emit(packCellBroadcastLst)

            # print(tmp_str)
            # for i in range(7):
            #     print(message.data[i])


    def uint16_to_int16(self, x):
        if x > 0x7FFF:
            return x - (0xFFFF + 1)
        else:
            return x

    def uint8_to_int8(self, x):
        if x > 0x7F:
            return x - (0xFF + 1)
        else:
            return x