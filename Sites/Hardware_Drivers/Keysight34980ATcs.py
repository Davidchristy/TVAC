from telnetlib import Telnet
from datetime import datetime
import os
import time
# Host ipAddr_34980A = '192.168.99.3' on TVAC network
# Host ipAddr_34980A = '192.168.98.3' on direct connect.

#Ex: (@1002:1030,3010) Slot_1-Ch_2-30, & Slot_3-Ch_10
#Channel_List = "(@2036:2040,3001:3040)"

class Keysight34980ATcs(Telnet):

    def __init__(self, port=5024, timeout=10,
                channel_list = "(@1001:1040,2001:2040,3001:3040)"):
        Telnet.__init__(self)
        if os.name == "posix":
            user_name = os.environ['LOGNAME']
        else:
            user_name = "user"

        if 'root' in user_name:
            host = '192.168.99.3'
        else:
            host = '127.0.0.1'
        self.Ch_List = channel_list
        self.working_tc_lower_limit= 8
        self.working_tc_upper_limit = 2000
        self.telnet_prompt = "Tharsis> "
        if host is not None:
            self.open(host, port, timeout)
        
    def open(self, host, port=5024, timeout=10):
        print('Connecting to', host, "on port", str(port))
        Telnet.open(self, host, port, timeout)
        print(self.read(timeout,True)) ## Check "telnet_prompt" correctly configured
    
    def read(self, timeout=5, try_fix_prompt = False):
        response = ""
        for tries in range(1,2):
            try:
                response = self.read_until(self.telnet_prompt.encode(), timeout).decode()
            except EOFError as e:
                raise RuntimeError("Keysight: Connection has been closed")

            if response.endswith(self.telnet_prompt):
                response = response[:-len(self.telnet_prompt)]
                response = response.strip()
                break
            elif try_fix_prompt:
                    self.write('SYST:COMM:LAN:TELN:PROM "{0}"'.format(self.telnet_prompt).encode())
                    self.read(timeout = 1,try_fix_prompt = False)
            else:
                time.sleep(.1 * tries)
        else:
            raise TimeoutError(
                "Prompt Missing or not: '{0}'; Response: '{1}'".format(
                    self.telnet_prompt, response))
        return response
    
    def send_cmd(self, cmd: str, timeout=5):
        cmd += '\n'

        self.write(cmd.encode())
        response = self.read(timeout)

        return response

    def init_sys(self):
        dt_now = datetime.now()
        self.send_cmd("SYST:TIME {0:02d},{1:02d},{2:02d}.{3:03d}".format(dt_now.hour, dt_now.minute, dt_now.second, int(dt_now.microsecond / 1000)))
        self.send_cmd("SYST:DATE {0:04d},{1:02d},{2:02d}".format(dt_now.year, dt_now.month, dt_now.day))
        self.send_cmd("SYST:DATE?")
        self.send_cmd("SYST:TIME?")
        self.send_cmd("*IDN?")
        self.send_cmd("SYST:CTYP? 1")
        self.send_cmd("SYST:CTYP? 2")
        self.send_cmd("SYST:CTYP? 3")
        self.send_cmd("DISP ON")
        #self.send("DISP OFF") ## TODO: Uncomment line when done with most debuging
        self.send_cmd("SYST:BEEP:STAT OFF")
        self.send_cmd("CONF:TEMP TC,T")
        self.send_cmd("CONF:TEMP TC,T," + self.Ch_List)
        self.send_cmd("SENS:TEMP:ZERO:AUTO ON," + self.Ch_List)
        self.send_cmd("SENS:TEMP:TRAN:TYPE TC," + self.Ch_List)
        self.send_cmd("SENS:TEMP:TRAN:TC:TYPE T," + self.Ch_List)
        self.send_cmd("SENS:TEMP:TRAN:TC:RJUN:TYPE INT," + self.Ch_List)
        self.send_cmd("SENS:TEMP:TRAN:TC:IMP:AUTO OFF," + self.Ch_List)
        self.send_cmd("SENS:TEMP:TRAN:TC:CHECk ON," + self.Ch_List)
        self.send_cmd("UNIT:TEMP K")                                    #K=Kelven; C=°Celsius
        self.send_cmd("UNIT:TEMP K," + self.Ch_List)                    #K=Kelven; C=°Celsius
        self.send_cmd("ROUT:SCAN " + self.Ch_List)
        self.send_cmd("FORM:READ:CHAN ON")
        self.send_cmd("FORM:READ:ALAR ON")
        self.send_cmd("FORM:READ:TIME ON")
        self.send_cmd("FORM:READ:TIME:TYPE REL")
        self.send_cmd("FORM:READ:UNIT ON")
        self.send_cmd("SYST:BEEP") # Have unit beep when done with init

    def get_tc_values(self):
        ## tc_list formatting from "DataContracts.ThermocoupleCollection"
        tc_list = {'time':datetime.now(), 'tcList': []}

        # If it still errors out from time value, break these up more.
        # channels = ['(@1001:1020)','(@1021:1040)','(@2001:2020)',etc]
        # if the time it takes increases, decrease the sleep time in TC updater
        banks = ['(@1001:1040)',
                    '(@2001:2040)',
                    '(@3001:3040)']
        for bank in banks:
            # First get the values for the current bank of channels
            values = self.send_cmd("READ? {}".format(bank), 6).split(',')

            # Separate the large list of TC data into 4 sublists
            temperatures_raw = values[0:len(values):4]
            tc_time_offsets_raw = values[1:len(values):4]
            channels_raw = values[2:len(values):4]
            alarms = values[3:len(values):4]

            for i in range(len(temperatures_raw)):
                # Transform raw data to what we need
                tc_num = (int(channels_raw[i][0])-1)*40 + int(channels_raw[i][-3:])
                tc_unit = temperatures_raw[i][-1]
                temperature = float(temperatures_raw[i][:-1])
                if tc_unit == 'K':
                    tc_temp_k = temperature
                elif tc_unit == 'C':
                    tc_temp_k = temperature + 273.15
                elif tc_unit == 'F':
                    tc_temp_k = ((temperature - 32) * 5/9) + 273.15
                else:
                    raise RuntimeError("Unknown Units '" + temperatures_raw[i] + "' ch:" + str(tc_num))
                tc_time_offset = float(tc_time_offsets_raw[i])
                tc_alarm = int(alarms[i])

                # Calculate if the TC is currently working or not.
                if (tc_temp_k > self.working_tc_lower_limit) and \
                        (tc_temp_k < self.working_tc_upper_limit):
                    tc_working = True
                else:
                    tc_working = False
                    # If the TC is not working, put NaN as our value
                    tc_temp_k = float('NaN')

                # tc_list['tcList'] formatting from "DataContracts.ThermocoupleContract"
                tc_list['tcList'].append({'Thermocouple': tc_num,
                                          'time': tc_time_offset,
                                          'temp': tc_temp_k,
                                          'working': tc_working,
                                          'alarm': tc_alarm})
            #inner for loop for each tc
        # outer for loop for each call
        return tc_list
