#!/usr/bin/env python
import bmstools.jbd
import serial
import sys
import time
from pprint import pprint
import json


class Test:

    def __init__(self):
        s = serial.Serial('/dev/ttyUSB0')
        self.j = bmstools.jbd.JBD(s)
        self.j.debug=True

    def test(self):
        self.j.debug=True
        self.j.password = 'abcdef'

        self.j.open()
        for _ in range(3):
            try:
                j._sendPassword()
                print('send password success')
            except Exception as e:
                print(f'attempt {_} error {repr(e)}')

    def clearErrors(self):
        self.j.clearErrors()

    def main(self):

        if 0:
            self.j.clearPasswordNoFactory()
            return

        if 0:
            self.j.clearPassword()
            return

        if 0:
            self.j.setPassword('abcdef')
            return


        if 0:
            self.j.password = 'xxxxxx'
            #self.j.password = bytes(6)
            self.clearErrors()
            return

        if 0:
            print(repr(serial_num_reg))
            print(serial_num_reg.get('serial_num'))
            print(f"serial number: {serial_num_reg.get(serial_num_reg.regName)}")

            reg = j.eeprom_reg_by_regname['error_cnts']
            reg = j.readReg(reg)
            for k,v in reg.items():
                print(k,v)

        while 1:
            time.sleep(1)
            basic = self.j.readBasicInfo()
            cell = self.j.readCellInfo()
            print(json.dumps(basic, indent = 2))
            print(json.dumps(cell, indent = 2))
            break
            pprint(basic)
            pprint(cell)


def main():
    test = Test()
    test.main()
main()
