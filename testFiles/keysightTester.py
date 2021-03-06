#!/usr/bin/env python3.5
from datetime import datetime
import time
import sys
from telnetlib import Telnet
from datetime import datetime


## TODO!! Change all print errors to ERROR logger.

# Host ipAddr_34980A = '192.168.99.3' on TVAC network
# Host ipAddr_34980A = '192.168.98.3' on direct connect.

# Ex: (@1002:1030,3010) Slot_1-Ch_2-30, & Slot_3-Ch_10
# Channel_List = "(@2036:2040,3001:3040)"

class Keysight_34980A_TCs(Telnet):

    def __init__(self, host='localhost', port=5024, timeout=10,
                 ChannelList="(@1001:1040,2001:2040,3001:3040)"):
        Telnet.__init__(self)
        self.Ch_List = ChannelList
        self.working_tc_lower_limit = 8
        self.working_tc_upper_limit = 2000
        self.telnet_prompt = "Tharsis> "
        if host is not None:
            print("host: {}".format(host))
            print("port: {}".format(port))
            print("timeout: {}".format(timeout))
            self.open(host, port, timeout)

    def open(self, host, port=5024, timeout=10):
        print('Connecting to', host, "on port", str(port))
        Telnet.open(self, host, port, timeout)
        print("opened connection")
        print(self.read(timeout, True))  ## Check "telnet_prompt" correctly configured

    def read(self, timeout=5, try_fix_prompt=False):
        response = ''
        try:
            print("Trying to read keysight")
            response = self.read_until(self.telnet_prompt.encode(), 5).decode()
            print("Raw value: {}".format(response))
        except Exception as e:
            raise e

        if response.endswith(self.telnet_prompt):
            print("Remove prompt")
            response = response[:-len(self.telnet_prompt)]
        else:
            if try_fix_prompt:
                self.write('SYST:COMM:LAN:TELN:PROM "{0}"'.format(self.telnet_prompt).encode())
                self.read(1, False)
            else:
                raise RuntimeError(
                    "Prompt Missing or not: '{0}'; Responce: '{1}'".format(
                        self.telnet_prompt, response))
        return response.strip()

    def send(self, cmd: str, timeout=5, appendLF=True, printR=False):
        if appendLF:
            cmd += '\n'
        print("Sending commend: {}".format(cmd))
        self.write(cmd.encode())
        response = self.read(timeout)
        if printR:
            print(cmd + response)  ## TODO: Change to log
        return response

    def init_sys(self):
        dt_now = datetime.now()
        self.send("SYST:TIME {0:02d},{1:02d},{2:02d}.{3:03d}".format(dt_now.hour, dt_now.minute, dt_now.second,
                                                                     int(dt_now.microsecond / 1000)))
        self.send("SYST:DATE {0:04d},{1:02d},{2:02d}".format(dt_now.year, dt_now.month, dt_now.day))
        self.send("SYST:DATE?", printR=True)
        self.send("SYST:TIME?", printR=True)
        self.send("*IDN?", printR=True)
        self.send("SYST:CTYP? 1", printR=True)
        self.send("SYST:CTYP? 2", printR=True)
        self.send("SYST:CTYP? 3", printR=True)
        self.send("DISP ON")
        # self.send("DISP OFF") ## TODO: Uncomment line when done with most debuging
        self.send("SYST:BEEP:STAT OFF")
        self.send("CONF:TEMP TC,T")
        self.send("CONF:TEMP TC,T," + self.Ch_List)
        self.send("SENS:TEMP:ZERO:AUTO ON," + self.Ch_List)
        self.send("SENS:TEMP:TRAN:TYPE TC," + self.Ch_List)
        self.send("SENS:TEMP:TRAN:TC:TYPE T," + self.Ch_List)
        self.send("SENS:TEMP:TRAN:TC:RJUN:TYPE INT," + self.Ch_List)
        self.send("SENS:TEMP:TRAN:TC:IMP:AUTO OFF," + self.Ch_List)
        self.send("SENS:TEMP:TRAN:TC:CHECk ON," + self.Ch_List)
        self.send("UNIT:TEMP K")  # K=Kelven; C=°Celsius
        self.send("UNIT:TEMP K," + self.Ch_List)  # K=Kelven; C=°Celsius
        self.send("ROUT:SCAN " + self.Ch_List)
        self.send("FORM:READ:CHAN ON")
        self.send("FORM:READ:ALAR ON")  # TODO: Set Alarms
        self.send("FORM:READ:TIME ON")
        self.send("FORM:READ:TIME:TYPE REL")
        self.send("FORM:READ:UNIT ON")
        self.send("SYST:BEEP")  # Have unit beep when done with init

    def getTC_Values(self, print_raw_values=False):
        ## tc_list formating from "DataContracts.ThermocoupleCollection"
        tc_list = {'time': datetime.now(), 'tcList': []}
        channels = ['(@1001:1040)',
                    '(@2001:2040)',
                    '(@3001:3040)']
        for channel in channels:

            values = self.send("READ? {}".format(channel), 6).split(',')
            v1 = values[0:len(values):4]
            v2 = values[1:len(values):4]
            v3 = values[2:len(values):4]
            v4 = values[3:len(values):4]

            if len(v1)==1: print("Final values: {}".format(values))
            print("v1: {}".format(len(v1)))
            print("v2: {}".format(len(v2)))
            print("v3: {}".format(len(v3)))
            print("v4: {}".format(len(v4)))
            for i in range(len(v1)):
                tc_num = (int(v3[i][0]) - 1) * 40 + int(v3[i][-3:])
                tc_unit = v1[i][-1]
                temperature = float(v1[i][:-1])
                if tc_unit == 'K':
                    tc_tempK = temperature
                elif tc_unit == 'C':
                    tc_tempK = temperature + 273.15
                elif tc_unit == 'F':
                    tc_tempK = ((temperature - 32) * 5 / 9) + 273.15
                else:
                    # TODO!! make this a recoverable reinitializing error.
                    raise RuntimeError("Unknown Units '" + v1[i] + "' ch:" + str(tc_num))
                tc_time_offset = float(v2[i])
                tc_alarm = int(v4[i])
                if (tc_tempK > self.working_tc_lower_limit) and \
                        (tc_tempK < self.working_tc_upper_limit):
                    tc_working = True
                else:
                    tc_working = False
                    tc_tempK = float('NaN')
                if print_raw_values:
                    print([v1[i], v2[i], v3[i], v4[i]])
                # tc_list['tcList'] formating from "DataContracts.ThermocoupleContract"
                tc_list['tcList'].append({'Thermocouple': tc_num,
                                          'time': tc_time_offset,
                                          'temp': tc_tempK,
                                          'working': tc_working,
                                          'alarm': tc_alarm})
        return tc_list

if __name__ == '__main__':
    ks = Keysight_34980A_TCs()

    for i in range(100):
        # tcs = ks.getTC_Values()
        ks.write("lol".encode())
        # print(tcs)