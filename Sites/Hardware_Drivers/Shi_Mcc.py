import time
import os

from Logging.Logging import Logging
from Hardware_Drivers.tty_reader import TTY_Reader
from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance


def get_checksum(cmd):  # append the sum of the string's bytes mod 256 + '\r'
    """
    This is a small helper function to get the checksum of the given string.
    :param cmd:
    :return:
    """
    d = sum(cmd.encode())
    #       0x30 + ( (d2 to d6) or (d0 xor d6) or ((d1 xor d7) shift to d2)
    return 0x30 + ((d & 0x3c) |
                   ((d & 0x01) ^ ((d & 0x40) >> 6)) |  # (d0 xor d6)
                   ((d & 0x02) ^ ((d & 0x80) >> 6)))  # (d1 xor d7)


def gen_cmd(cmd):  # Cmd syntax see section 2.3 MCC Programing Guide
    return "${0}{1:c}\r".format(cmd, get_checksum(cmd))


def format_response(d, error=False, pwrFail=False):  # , d_int = 0, d_float = 0.0);
    return {"Error": error, "PowerFailure": pwrFail, "Response": d}  # , "int"=d_int, "float"=d_float}


class Shi_Mcc:

    def __init__(self):
        self.port = None
        self.port_listener = TTY_Reader(None,name="Shi_Mcc_Reader")
        self.port_listener.daemon = True


    def open_port(self):
        self.port = open('/dev/ttyxuart0', 'r+b', buffering=0)
        self.port_listener.get_fd(self.port)
        try:
            self.port_listener.start()
        except Exception as e:
            pass
        self.port_listener.flush_buffer(1.0)


    def flush_port(self):
        self.port_listener.flush_buffer(1.0)


    def close_port(self):
        if not self.port.closed:
            self.port.close()


    def send_mcc_cmd(self, command):
        for tries in range(3):
            # Writes the command to the FIFO file connected to the MCC
            self.port.write(gen_cmd(command).encode())

            # Waits until it gets a reply, waits for 2 seconds before calling it timeout
            # I don't know what happens at timeout...
            # TODO: Confirm this works, and clean up read_line()
            resp = self.port_listener.read_line(2.0)

            # Checks to see if the reply received is valid
            if self.valid_response(resp):
                if resp[1] == 'A':  # Response Good!
                    data = format_response(resp[2:-2])
                elif resp[1] == 'B':
                    data = format_response(resp[2:-2], pwrFail=True)
                elif resp[1] == 'E':
                    data = format_response(resp[2:-2], error=True)
                elif resp[1] == 'F':
                    data = format_response(resp[2:-2], error=True, pwrFail=True)
                else:
                    data = format_response("R--" + resp + "-- unknown", error=True)
                break
                # TODO: Change to error event print("Try number: " + str(tries))
        else:
            # TODO: Change to error event print("No more tries! Something is wrong!")
            raise RuntimeError("Timeout Error: MCC not replying, last command: {}".format(command))
        return data

    def valid_response(self, response):
        '''
        This is a helper function that checks to see if the reply received from the MCC is valid

        Look at the "Marathon Cryopump Controller Programmer's Reference Guide" Section 2.3 for more detail.
        :param response:
        :return:
        '''

        if len(response) < 4:
            self.port_listener.flush_buffer(2.0)
            print("MCC: Reply from MCC is less than 4 in length: '{}'".format(response.replace('\r', r'\r')))
            return False
        if response[-1] != '\r':
            print("MCC: Missing Carriage Return at the end: '{}'".format(response.replace('\r', r'\r')))
            return False
        if response[-2] != chr(get_checksum(response[1:-2])):
            print("MCC: Checksum was incorrect: Expected: '{}' Received: '{}'".format(get_checksum(response[1:-2]), response[-2]))
            return False
        if response[0] != '$':
            print("MCC: '$' is not the first byte: '{}'".format(response.replace('\r', r'\r')))
            return False
        return True  # Yea!! response seems ok

    def get_status(self):
        # Create Dict of Functions
        functions = {"DutyCycle": self.Get_DutyCycle,  # 2.4 ------------------ Ex: "$XOI??_\r"
                "Stage1Temp": self.Get_FirstStageTemp,  # 2.8 ------------ Ex: "$J;\r"
                "CryoPumpReadyState": self.Get_CryoPumpRdyState,  # 2.14 - Ex: "$A?2\r"
                "PurgeValveState": self.Get_PurgeValveState,  # 2.15 ----- Ex: "$E?6\r"
                "RegenError": self.Get_RegenError,  # 2.18 --------------- Ex: "$eT\r"
                "RegenStep": self.Get_RegenStep,  # 2.20 ----------------- Ex: "$O>\r"
                "RoughingValveState": self.Get_RoughingValveState,  # 2.24 Ex: "$D?3\r"
                "RoughingInterlock": self.Get_RoughingInterlock,  # 2.25 - Ex: "$Q?B\r"
                "Stage2Temp": self.Get_SecondStageTemp,  # 2.26 ---------- Ex: "$K:\r"
                "Status": self.Get_Status_Cmd,  # 2.28 ----------------------- Ex: "$S16\r"
                "TcPressure": self.Get_TcPressure}  # 2.30 --------------- Ex: "$L=\r"
        return self.run_GetFunctions(functions)

    def get_ParamValues(self):
        # Create Dict of Functions
        FunS = {"Elapsed Time": self.Get_ElapsedTime,  # 2.5 -------------------------- Ex: "$Y?J\r"
                "Failed Rate Of Rise Cycles": self.Get_Failed_RateOfRise_Cycles,  # 2.6 Ex: "$m\\r"
                "Failed Repurge Cycles": self.Get_FailedRepurgeCycles,  # 2.7 --------- Ex: "$l]\r"
                "First Stage Temp CTL": self.Get_FirstStageTempCTL,  # 2.9 ------------ Ex: "$H?5\r"
                "Last Rate Of Rise Value": self.Get_LastRateOfRiseValue,  # 2.10 ------ Ex: "$n_\r"
                "MCC Version": self.Get_ModuleVersion,  # 2.11 ------------------------ Ex: "$@1\r"
                "Power Failure Recovery": self.Get_PowerFailureRecovery,  # 2.12 ------ Ex: "$i?H\r"
                "Power Failure Recovery Status": self.Get_PowerFailureRecoveryStatus,  # 2.13 Ex: "$t?a\r"
                "Regen Cycles": self.Get_RegenCycles,  # 2.17 - Ex: "$Z?K\r"
                "Regen Param_0": self.Get_RegenParam_0,  # 2.19 Ex: "P0?"
                "Regen Param_1": self.Get_RegenParam_1,  # 2.19 Ex: "P1?"
                "Regen Param_2": self.Get_RegenParam_2,  # 2.19 Ex: "P2?"
                "Regen Param_3": self.Get_RegenParam_3,  # 2.19 Ex: "P3?"
                "Regen Param_4": self.Get_RegenParam_4,  # 2.19 Ex: "P4?"
                "Regen Param_5": self.Get_RegenParam_5,  # 2.19 Ex: "P5?"
                "Regen Param_6": self.Get_RegenParam_6,  # 2.19 Ex: "P6?"
                "Regen Param_A": self.Get_RegenParam_A,  # 2.19 Ex: "PA?"
                "Regen Param_C": self.Get_RegenParam_C,  # 2.19 Ex: "PC?"
                "Regen Param_G": self.Get_RegenParam_G,  # 2.19 Ex: "PG?"
                "Regen Param_z": self.Get_RegenParam_z,  # 2.19 Ex: "Pz?"
                "Regen Start Delay": self.Get_RegenStartDelay,  # 2.21 ------ Ex: "$j?[\r"
                "Regen Step Timer": self.Get_RegenStepTimer,  # 2.22 -------- Ex: "$kZ\r"
                "Regen Time": self.Get_RegenTime,  # 2.23 ------------------- Ex: "$aP\r"
                "Second Stage Temp CTL": self.Get_SecondStageTempCTL,  # 2.27 Ex: "$I?:\r"
                "Tc Pressure State": self.Get_TcPressureState}  # 2.29 ------ Ex: "$B?3\r"
        return self.run_GetFunctions(FunS)

    def run_GetFunctions(self, Functions):
        er = False
        pf = False
        vals = {}
        for key in Functions.keys():
            val = Functions[key]()
            er |= val['Error']
            if er:
                print("run_GetFunctions Error==True")
                break
            pf |= val['PowerFailure']
            if 'Data' in val:
                vals[key] = val['Data']
            else:
                vals[key] = val['Response']
        return format_response(vals, er, pf)

    # MCC Programmers References Guide Rev C

    # 2.4 • Duty Cycle pg:8
    def Get_DutyCycle(self):  # Command Ex: "$XOI??_\r"
        # return self.send_cmd("XOI??")
        val = self.send_mcc_cmd("XOI??")
        if not val['Error']:
            val['Data'] = round((int(val['Response'])/35.0) * 100.0, 2)
        return val

    # 2.5 • Elapsed Time pg:8
    def Get_ElapsedTime(self):  # Command Ex: "$Y?J\r"
        # return self.send_cmd("Y?")
        val = self.send_mcc_cmd("Y?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.6 • Failed Rate Of Rise Cycles pg:8
    def Get_Failed_RateOfRise_Cycles(self):  # Command Ex: "$m\\r"
        # return self.send_cmd("m")
        val = self.send_mcc_cmd("m")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.7 • Failed Repurge Cycles pg:9
    def Get_FailedRepurgeCycles(self):  # Command Ex: "$l]\r"
        # return self.send_cmd("l")
        val = self.send_mcc_cmd("l")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.8 • First Stage Temperature pg:9
    def Get_FirstStageTemp(self):  # Command Ex: "$J;\r"
        # return self.send_cmd("J")
        val = self.send_mcc_cmd("J")
        if not val['Error']:
            val['Data'] = float(val['Response'])
        return val

    # 2.9 • First Stage Temperature Control pg:10
    def Get_FirstStageTempCTL(self):  # Command Ex: "$H?5\r"
        val = self.send_mcc_cmd("H?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Set_FirstStageTempCTL(self, temp=0, method=0):
        if (temp < 0) | (temp > 320):
            # TODO: Change to error event print('First stage Temperature out is of range (0-320): {:d}'.format(temp))
            return format_response("Temp out of range: " + str(temp), error=True)
        if (method < 0) | (method > 3):
            # TODO: Change to error event print('First stage control method is out of range (0-3): {:d}'.format(method))
            return format_response("Temp out of range: " + str(method), error=True)
        # add convert to real Data
        return self.send_mcc_cmd("H{0:d},{1:d}".format(temp, method))

    # 2.10 • Last Rate Of Rise Value pg:11
    def Get_LastRateOfRiseValue(self):  # Command Ex: "$n_\r"
        # return self.send_cmd("n")
        val = self.send_mcc_cmd("n")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.11 • Module Version pg:11
    def Get_ModuleVersion(self):  # Command Ex: "$@1\r"
        return self.send_mcc_cmd("@")

    # 2.12 • Power Failure Recovery pg:11
    def Get_PowerFailureRecovery(self):  # Command Ex: "$i?H\r"
        val = self.send_mcc_cmd("i?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Set_PowerFailureRecovery(self, method=2):  # Command Ex: "$i2H\r"
        # 0: Power failure recovery disabled.
        # 1: Power failure recovery enabled.
        # 2: Power failure recovery enabled only when T2 is less than the limit set point.
        if (method < 0) | (method > 2):
            print('Not a Valid Power recovery mode (0-2): {:d}'.format(method))
            return format_response("Not a Valid Power recovery mode (0-2): " + str(method), error=True)
        # add convert to real Data
        return self.send_mcc_cmd("i{0:d}".format(method))

    # 2.13 • Power Failure Recovery Status pg:12
    def Get_PowerFailureRecoveryStatus(self):  # Command Ex: "$t?a\r"
        val = self.send_mcc_cmd("t?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.14 • Pump On/Off/Query pg:13
    def Get_CryoPumpOnState(self):  # Command Ex: "$A?2\r"
        return self.send_mcc_cmd("A?")

    def Get_CryoPumpRdyState(self):  # Command Ex: "$A??m\r"
        return self.send_mcc_cmd("A??")  # Use this one for the Contract

    def Turn_CryoPumpOn(self):  # Command Ex: "$A1c\r"
        return self.send_mcc_cmd("A1")

    def Turn_CryoPumpOff(self):
        return self.send_mcc_cmd("A0")

    # 2.15 • Purge On/Off/Query pg:14
    def Get_PurgeValveState(self):  # Command Ex: "$E?6\r"
        # return self.send_cmd("E?")
        val = self.send_mcc_cmd("E?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Open_PurgeValve(self):
        hw = HardwareStatusInstance.getInstance()
        if hw.pc_104.digital_in.getVal('CryoP_GV_Closed'):
            return self.send_mcc_cmd("E1")
        else:
            return format_response("Cryopump Gate Valve not closed. Purge valve not opened.")



    def Close_PurgeValve(self):  # Command Ex: "$E0d\r"
        return self.send_mcc_cmd("E0")

    # 2.16 • Regeneration pg:14
    def Start_Regen(self, num):
        if (num < 0) | (num > 4):
            # TODO: Change to error event print('First stage control method is out of range (0-4): {:d}'.format(num))
            return format_response("Start Regen Number of range: " + str(num), error=True)

        Logging.logEvent("Event", "Cryopump Regeneration",
                         {"message": "Cryopump regeneration starting",
                          "ProfileInstance": ProfileInstance.getInstance()})
        return self.send_mcc_cmd("N{0:d}".format(num))

    # 2.17 • Regeneration Cycles pg:15
    def Get_RegenCycles(self):  # Command Ex: "$Z?K\r"
        # return self.send_cmd("Z?")
        val = self.send_mcc_cmd("Z?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.18 • Regeneration Error pg:15
    def Get_RegenError(self):  # Command Ex: "$eT\r"
        return self.send_mcc_cmd("e")

    # 2.19 • Regeneration Parameters pg:16
    def Get_RegenParam(self, Param=''):  # expected call: Get_RegenParam(chr(int))
        if (Param not in ['0', '1', '2', '3', '4', '5', '6', 'A', 'C', 'G', 'z']):
            return format_response("Parameter unknown: " + str(Param), error=True)
        val = self.send_mcc_cmd("P" + str(Param) + "?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_0(self):
        # return self.send_cmd("P0?")
        val = self.send_mcc_cmd("P0?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_1(self):
        # return self.send_cmd("P1?")
        val = self.send_mcc_cmd("P1?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_2(self):
        # return self.send_cmd("P2?")
        val = self.send_mcc_cmd("P2?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_3(self):
        # return self.send_cmd("P3?")
        val = self.send_mcc_cmd("P3?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_4(self):
        # return self.send_cmd("P4?")
        val = self.send_mcc_cmd("P4?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_5(self):
        # return self.send_cmd("P5?")
        val = self.send_mcc_cmd("P5?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_6(self):
        val = self.send_mcc_cmd("P6?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_A(self):
        # return self.send_cmd("PA?")
        val = self.send_mcc_cmd("PA?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_C(self):
        # return self.send_cmd("PC?")
        val = self.send_mcc_cmd("PC?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_G(self):
        # return self.send_cmd("PG?")
        val = self.send_mcc_cmd("PG?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Get_RegenParam_z(self):
        val = self.send_mcc_cmd("Pz?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Set_RegenParam(self, Param='', Value=0):  # expected call: Set_RegenParam(chr(int), int)
        if (Param not in ['0', '1', '2', '3', '4', '5', '6', 'A', 'C', 'G', 'z']):
            return format_response("Parameter unknown: " + str(Param), error=True)
        elif (Param == '0') & ((Value < 0) | (Value > 59994)):
            return format_response("RegenParam: Pump Restart Delay out of range: " + str(Value), error=True)
        elif (Param == '1') & ((Value < 0) | (Value > 9990)):
            return format_response("RegenParam: Extend Purge time out of range: " + str(Value), error=True)
        elif (Param == '2') & ((Value < 0) | (Value > 200)):
            return format_response("RegenParam: Repurge Cycles out of range: " + str(Value), error=True)
        elif (Param == '3') & ((Value < 25) | (Value > 200)):
            return format_response("RegenParam: Rough to Pressure out of range: " + str(Value), error=True)
        elif (Param == '4') & ((Value < 1) | (Value > 100)):
            return format_response("RegenParam: Rate of Rise out of range: " + str(Value), error=True)
        elif (Param == '5') & ((Value < 0) | (Value > 200)):
            return format_response("RegenParam: Rate of Rise Cycles out of range: " + str(Value), error=True)
        elif (Param == '6') & ((Value < 0) | (Value > 80)):
            return format_response("RegenParam: Restart Temperature out of range: " + str(Value), error=True)
        elif (Param == 'A') & ((Value < 0) | (Value > 1)):
            return format_response("RegenParam: Roughing Interlock not 0 or 1: " + str(Value), error=True)
        elif (Param == 'C') & ((Value < 1) | (Value > 3)):
            return format_response("RegenParam: Pumps per Compressor: " + str(Value), error=True)
        elif (Param == 'G') & ((Value < 0) | (Value > 9999)):
            return format_response("RegenParam: Repurge time out of range: " + str(Value), error=True)
        elif (Param == 'z') & ((Value < 0) | (Value > 1)):
            return format_response("RegenParam: Stand by mode not 0 or 1: " + str(Value), error=True)
        else:
            return self.send_mcc_cmd("P" + str(Param) + str(Value))

    # 2.20 • Regeneration Sequence pg:17
    def Get_RegenStep(self):  # Command Ex: "$O>\r"
        return self.send_mcc_cmd("O")

    # 2.21 • Regeneration Start Delay pg.18
    def Get_RegenStartDelay(self):  # Command Ex: "$j?[\r"
        val = self.send_mcc_cmd("j?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Set_RegenStartDelay(self, delay):
        if (delay < 0) or (delay > 59994):
            # TODO: Change to error event print('Regeneration Start Delay out is of range (0-59994): {:d}'.format(delay))
            return format_response("Regeneration Start Delay out of range: " + str(delay), error=True)
        return self.send_mcc_cmd("j{0:d}".format(delay))

    # 2.22 • Regeneration Step Timer pg:18
    def Get_RegenStepTimer(self):  # Command Ex: "$kZ\r"
        # return self.send_cmd("k")
        val = self.send_mcc_cmd("k")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.23 • Regeneration Time pg:19
    def Get_RegenTime(self):  # Command Ex: "$aP\r"
        # return self.send_cmd("a")
        val = self.send_mcc_cmd("a")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.24 • Rough On/Off/Query pg:19
    def Get_RoughingValveState(self):  # Command Ex: "$D?3\r"
        # return self.send_cmd("D?")
        val = self.send_mcc_cmd("D?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Open_RoughingValve(self):  # Command Ex: "$D1d\r"
        return self.send_mcc_cmd("D1")

    def Close_RoughingValve(self):
        return self.send_mcc_cmd("D0")

    # 2.25 • Rough Valve Interlock pg:20
    def Get_RoughingInterlock(self):  # Command Ex: "$Q?B\r"
        # return self.send_cmd("Q?")
        val = self.send_mcc_cmd("Q?")
        if not val['Error']:
            val['Data'] = int(val['Response']) - 0x30
        return val

    def Clear_RoughingInterlock(self):  # Command Ex: "$Q?B\r"
        return self.send_mcc_cmd("Q")

    # 2.26 • Second Stage Temperature pg:20
    def Get_SecondStageTemp(self):  # Command Ex: "$K:\r"
        # return self.send_cmd("K")
        if os.name == "posix":
            userName = os.environ['LOGNAME']
        else:
            userName = "User"
        if "root" in userName:
            val = self.send_mcc_cmd("K")
        else:
            val = {'Error':False,'Response':14.0}
        if not val['Error']:
            val['Data'] = float(val['Response'])
        return val

    # 2.27 • Second Stage Temperature Control pg:21
    def Get_SecondStageTempCTL(self):  # Command Ex: "$I?:\r"
        val = self.send_mcc_cmd("I?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Set_SecondStageTempCTL(self, temp):  # Command Ex: "$I?:\r"
        if (temp < 0) | (temp > 320):
            # TODO: Change to error event print('Second stage Temperature out is of range (0-320): {:d}'.format(temp))
            return format_response("Temp out of range: " + str(temp), error=True)
        return self.send_mcc_cmd("I{0:d}".format(temp))

    # 2.28 • Status pg:22
    def Get_Status_Cmd(self):  # Command Ex: "$S16\r"
        # return self.send_cmd("S1")
        val = self.send_mcc_cmd("S1")
        if (not val['Error']) & (len(val['Response']) == 1):
            val['Data'] = ord(val['Response']) - 0x20
        return val

    # 2.29 • TC On/Off/Query pg:22
    def Get_TcPressureState(self):  # Command Ex: "$B?3\r"
        # return self.send_cmd("B?")
        val = self.send_mcc_cmd("B?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def Turn_TcPressureOn(self):  # Command Ex: "$B1b\r"
        return self.send_mcc_cmd("B1")

    def Turn_TcPressureOff(self):  # Command Ex: "$B?3\r"
        return self.send_mcc_cmd("B0")

    # 2.30 • Thermocouple Pressure pg:22
    def Get_TcPressure(self):  # Command Ex: "$L=\r"
        # return self.send_cmd("L")
        val = self.send_mcc_cmd("L")
        if not val['Error']:
            val['Data'] = float(val['Response']) / 1000  # Change to Torr
        return val
