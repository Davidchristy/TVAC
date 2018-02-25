import time

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


def format_response(d, error=False, pwr_fail=False):  # , d_int = 0, d_float = 0.0);
    return {"Error": error, "PowerFailure": pwr_fail, "Response": d}  # , "int"=d_int, "float"=d_float}


def run_get_functions(functions):

    er = False
    pf = False
    vals = {}
    for key in functions.keys():
        val = functions[key]()
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


class ShiMcc:

    def __init__(self):
        self.port = None
        self.port_listener = TTY_Reader(None,name="Shi_Mcc_Reader")
        self.port_listener.daemon = True


    def open_port(self):
        self.port = open('/dev/ttyxuart0', 'r+b', buffering=0)
        self.port_listener.get_fd(self.port)
        try:
            self.port_listener.start()
        except RuntimeError:
            pass
        self.port_listener.flush_buffer(1.0)

    def flush_port(self, wait_time = 0):
        self.port_listener.flush_buffer(wait_time)

    def close_port(self):
        if not self.port.closed:
            self.port.close()

    def send_mcc_cmd(self, command):
        # Tries and sends the command three times before error-ing out
        for tries in range(1,4):
            # Writes the command to the FIFO file connected to the MCC
            self.port.write(gen_cmd(command).encode())

            # Waits until it gets a reply, waits for .5 seconds before calling it timeout
            # Marathon Cryopump Controller Programmer's Reference Guide Section 2.2
            # Recommends 500 milliseconds
            resp = self.port_listener.read_line(.5)

            # TODO: Check to see whar happens if B, E, or F happens
            # Checks to see if the reply received is valid
            if self.valid_response(resp):
                if resp[1] == 'A':  # Response Good!
                    data = format_response(resp[2:-2])
                elif resp[1] == 'B':
                    data = format_response(resp[2:-2], pwr_fail=True)
                elif resp[1] == 'E':
                    data = format_response(resp[2:-2], error=True)
                elif resp[1] == 'F':
                    data = format_response(resp[2:-2], error=True, pwr_fail=True)
                else:
                    data = format_response("R--" + resp + "-- unknown", error=True)
                break
            time.sleep(.1 * tries)
        else:
            raise TimeoutError("Timeout Error: MCC not replying, last command: {}".format(command))
        return data

    def valid_response(self, response):
        """
        This is a helper function that checks to see if the reply received from the MCC is valid

        Look at the "Marathon Cryopump Controller Programmer's Reference Guide" Section 2.3 for more detail.
        :param response:
        :return:
        """

        if len(response) < 4:
            self.port_listener.flush_buffer(2.0)
            print("MCC: Reply from MCC is less than 4 in length: '{}'".format(response.replace('\r', r'\r')))
            return False
        if response[-1] != '\r':
            print("MCC: Missing Carriage Return at the end: '{}'".format(response.replace('\r', r'\r')))
            return False
        if response[-2] != chr(get_checksum(response[1:-2])):
            raise RuntimeError("MCC: Checksum was incorrect: Expected: '{}' Received: '{}'".format(get_checksum(response[1:-2]), response[-2]))
        if response[0] != '$':
            raise RuntimeError("MCC: '$' is not the first byte: '{}'".format(response.replace('\r', r'\r')))
        return True  # Yea!! response seems ok

    def get_shi_mcc_status(self):
        # Create Dict of Functions
        functions = {"DutyCycle": self.get_duty_cycle,  # 2.4 ------------------ Ex: "$XOI??_\r"
                     "Stage1Temp": self.get_first_stage_temp,  # 2.8 ------------ Ex: "$J;\r"
                     "CryoPumpReadyState": self.get_cryopump_ready_state,  # 2.14 - Ex: "$A?2\r"
                     "PurgeValveState": self.get_purge_valve_state,  # 2.15 ----- Ex: "$E?6\r"
                     "RegenError": self.get_regen_error,  # 2.18 --------------- Ex: "$eT\r"
                     "RegenStep": self.get_regen_step,  # 2.20 ----------------- Ex: "$O>\r"
                     "RoughingValveState": self.get_roughing_valve_state,  # 2.24 Ex: "$D?3\r"
                     "RoughingInterlock": self.get_roughing_interlock,  # 2.25 - Ex: "$Q?B\r"
                     "Stage2Temp": self.get_second_stage_temp,  # 2.26 ---------- Ex: "$K:\r"
                     "Status": self.get_status_cmd,  # 2.28 ----------------------- Ex: "$S16\r"
                     "TcPressure": self.get_tc_pressure}  # 2.30 --------------- Ex: "$L=\r"
        return run_get_functions(functions)

    def get_param_values(self):
        # Create Dict of Functions
        functions = {"Elapsed Time": self.get_elapsed_time,  # 2.5 -------------------------- Ex: "$Y?J\r"
                     "Failed Rate Of Rise Cycles": self.get_failed_rate_of_rise_cycles,  # 2.6 Ex: "$m\\r"
                "Failed Repurge Cycles": self.get_failed_repurge_cycles,  # 2.7 --------- Ex: "$l]\r"
                "First Stage Temp CTL": self.get_first_stage_temp_ctl,  # 2.9 ------------ Ex: "$H?5\r"
                "Last Rate Of Rise Value": self.get_last_rate_of_rise_value,  # 2.10 ------ Ex: "$n_\r"
                "MCC Version": self.get_module_version,  # 2.11 ------------------------ Ex: "$@1\r"
                "Power Failure Recovery": self.get_power_failure_recovery,  # 2.12 ------ Ex: "$i?H\r"
                "Power Failure Recovery Status": self.get_power_failure_recovery_status,  # 2.13 Ex: "$t?a\r"
                "Regen Cycles": self.get_regen_cycles,  # 2.17 - Ex: "$Z?K\r"
                     "Regen Param_0": self.get_regen_param_0,  # 2.19 Ex: "P0?"
                     "Regen Param_1": self.get_regen_param_1,  # 2.19 Ex: "P1?"
                     "Regen Param_2": self.get_regen_param_2,  # 2.19 Ex: "P2?"
                     "Regen Param_3": self.get_regen_param_3,  # 2.19 Ex: "P3?"
                     "Regen Param_4": self.get_regen_param_4,  # 2.19 Ex: "P4?"
                     "Regen Param_5": self.get_regen_param_5,  # 2.19 Ex: "P5?"
                     "Regen Param_6": self.get_regen_param_6,  # 2.19 Ex: "P6?"
                     "Regen Param_A": self.get_regen_param_a,  # 2.19 Ex: "PA?"
                     "Regen Param_C": self.get_regen_param_c,  # 2.19 Ex: "PC?"
                     "Regen Param_G": self.get_regen_param_g,  # 2.19 Ex: "PG?"
                     "Regen Param_z": self.get_regen_param_z,  # 2.19 Ex: "Pz?"
                     "Regen Start Delay": self.get_regen_start_delay,  # 2.21 ------ Ex: "$j?[\r"
                     "Regen Step Timer": self.get_regen_step_timer,  # 2.22 -------- Ex: "$kZ\r"
                     "Regen Time": self.get_regen_time,  # 2.23 ------------------- Ex: "$aP\r"
                     "Second Stage Temp CTL": self.get_second_stage_temp_ctl,  # 2.27 Ex: "$I?:\r"
                     "Tc Pressure State": self.get_tc_pressure_state}  # 2.29 ------ Ex: "$B?3\r"
        return run_get_functions(functions)

    # MCC Programmers References Guide Rev C

    # 2.4 • Duty Cycle pg:8
    def get_duty_cycle(self):  # Command Ex: "$XOI??_\r"
        val = self.send_mcc_cmd("XOI??")
        if not val['Error']:
            # TODO: In the manual it gives 23 as the max, yet this has 35. Which one is right?
            val['Data'] = round((int(val['Response'])/35.0) * 100.0, 2)
        return val

    # 2.5 • Elapsed Time pg:8
    def get_elapsed_time(self):  # Command Ex: "$Y?J\r"
        val = self.send_mcc_cmd("Y?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.6 • Failed Rate Of Rise Cycles pg:8
    def get_failed_rate_of_rise_cycles(self):  # Command Ex: "$m\\r"
        val = self.send_mcc_cmd("m")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.7 • Failed Repurge Cycles pg:9
    def get_failed_repurge_cycles(self):  # Command Ex: "$l]\r"
        val = self.send_mcc_cmd("l")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.8 • First Stage Temperature pg:9
    def get_first_stage_temp(self):  # Command Ex: "$J;\r"
        val = self.send_mcc_cmd("J")
        if not val['Error']:
            val['Data'] = float(val['Response'])
        return val

    # 2.9 • First Stage Temperature Control pg:10
    def get_first_stage_temp_ctl(self):  # Command Ex: "$H?5\r"
        val = self.send_mcc_cmd("H?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def set_first_stage_temp_ctl(self, temp=0, method=0):
        if (temp < 0) | (temp > 320):
            raise RuntimeError("MCC: Temp out of range: {}".format(temp))
        if (method < 0) | (method > 3):
            raise RuntimeError("MCC: method out of range: (0-3) '{:d}'".format(temp))
        # add convert to real Data
        return self.send_mcc_cmd("H{0:d},{1:d}".format(temp, method))

    # 2.10 • Last Rate Of Rise Value pg:11
    def get_last_rate_of_rise_value(self):  # Command Ex: "$n_\r"
        val = self.send_mcc_cmd("n")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.11 • Module Version pg:11
    def get_module_version(self):  # Command Ex: "$@1\r"
        return self.send_mcc_cmd("@")

    # 2.12 • Power Failure Recovery pg:11
    def get_power_failure_recovery(self):  # Command Ex: "$i?H\r"
        val = self.send_mcc_cmd("i?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def set_power_failure_recovery(self, method=2):  # Command Ex: "$i2H\r"
        # 0: Power failure recovery disabled.
        # 1: Power failure recovery enabled.
        # 2: Power failure recovery enabled only when T2 is less than the limit set point.
        if (method < 0) | (method > 2):
            raise RuntimeError('MCC: Not a Valid Power recovery mode (0-2): {:d}'.format(method))
        # add convert to real Data
        return self.send_mcc_cmd("i{0:d}".format(method))

    # 2.13 • Power Failure Recovery Status pg:12
    def get_power_failure_recovery_status(self):  # Command Ex: "$t?a\r"
        val = self.send_mcc_cmd("t?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.14 • Pump On/Off/Query pg:13
    # Never used
    def get_cryo_pump_on_state(self):  # Command Ex: "$A?2\r"
        return self.send_mcc_cmd("A?")

    def get_cryopump_ready_state(self):  # Command Ex: "$A??m\r"
        return self.send_mcc_cmd("A??")  # Use this one for the Contract

    def turn_cryopump_on(self):  # Command Ex: "$A1c\r"
        return self.send_mcc_cmd("A1")

    def turn_cryopump_off(self):
        return self.send_mcc_cmd("A0")

    # 2.15 • Purge On/Off/Query pg:14
    def get_purge_valve_state(self):  # Command Ex: "$E?6\r"
        val = self.send_mcc_cmd("E?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def open_purge_valve(self):
        hw = HardwareStatusInstance.getInstance()
        if hw.pc_104.digital_in.getVal('CryoP_GV_Closed'):
            return self.send_mcc_cmd("E1")
        else:
            return format_response("Cryopump Gate Valve not closed. Purge valve not opened.")

    def close_purge_valve(self):  # Command Ex: "$E0d\r"
        return self.send_mcc_cmd("E0")

    # 2.16 • Regeneration pg:14
    def start_regen(self, num):
        if (num < 0) | (num > 4):
            raise RuntimeError('MCC: First stage control method is out of range (0-4): {:d}'.format(num))

        Logging.logEvent("Event", "Cryopump Regeneration",
                         {"message": "Cryopump regeneration starting",
                          "ProfileInstance": ProfileInstance.getInstance()})
        return self.send_mcc_cmd("N{0:d}".format(num))

    # 2.17 • Regeneration Cycles pg:15
    def get_regen_cycles(self):  # Command Ex: "$Z?K\r"
        val = self.send_mcc_cmd("Z?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.18 • Regeneration Error pg:15
    def get_regen_error(self):  # Command Ex: "$eT\r"
        return self.send_mcc_cmd("e")

    # 2.19 • Regeneration Parameters pg:16
    def get_regen_param(self, param=''):  # expected call: Get_RegenParam(chr(int))
        if param not in ['0', '1', '2', '3', '4', '5', '6', 'A', 'C', 'G', 'z']:
            raise RuntimeError("MCC: Regen Parameter unknown: {}".format(param))
        val = self.send_mcc_cmd("P" + str(param) + "?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_0(self):
        val = self.send_mcc_cmd("P0?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_1(self):
        val = self.send_mcc_cmd("P1?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_2(self):
        val = self.send_mcc_cmd("P2?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_3(self):
        val = self.send_mcc_cmd("P3?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_4(self):
        val = self.send_mcc_cmd("P4?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_5(self):
        val = self.send_mcc_cmd("P5?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_6(self):
        val = self.send_mcc_cmd("P6?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_a(self):
        val = self.send_mcc_cmd("PA?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_c(self):
        val = self.send_mcc_cmd("PC?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_g(self):
        val = self.send_mcc_cmd("PG?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def get_regen_param_z(self):
        val = self.send_mcc_cmd("Pz?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def set_regen_param(self, param = '', value = 0):  # expected call: Set_RegenParam(chr(int), int)
        if param not in ['0', '1', '2', '3', '4', '5', '6', 'A', 'C', 'G', 'z']:
            raise RuntimeError("MCC: Parameter unknown: " + str(param))
        elif (param == '0') & ((value < 0) | (value > 59994)):
            raise RuntimeError("MCC: RegenParam: Pump Restart Delay out of range: " + str(value))
        elif (param == '1') & ((value < 0) | (value > 9990)):
            raise RuntimeError("MCC: RegenParam: Extend Purge time out of range: " + str(value))
        elif (param == '2') & ((value < 0) | (value > 200)):
            raise RuntimeError("MCC: RegenParam: Repurge Cycles out of range: " + str(value))
        elif (param == '3') & ((value < 25) | (value > 200)):
            raise RuntimeError("MCC: RegenParam: Rough to Pressure out of range: " + str(value))
        elif (param == '4') & ((value < 1) | (value > 100)):
            raise RuntimeError("MCC: RegenParam: Rate of Rise out of range: " + str(value))
        elif (param == '5') & ((value < 0) | (value > 200)):
            raise RuntimeError("MCC: RegenParam: Rate of Rise Cycles out of range: " + str(value))
        elif (param == '6') & ((value < 0) | (value > 80)):
            raise RuntimeError("MCC: RegenParam: Restart Temperature out of range: " + str(value))
        elif (param == 'A') & ((value < 0) | (value > 1)):
            raise RuntimeError("MCC: RegenParam: Roughing Interlock not 0 or 1: " + str(value))
        elif (param == 'C') & ((value < 1) | (value > 3)):
            raise RuntimeError("MCC: RegenParam: Pumps per Compressor: " + str(value))
        elif (param == 'G') & ((value < 0) | (value > 9999)):
            raise RuntimeError("MCC: RegenParam: Repurge time out of range: " + str(value))
        elif (param == 'z') & ((value < 0) | (value > 1)):
            raise RuntimeError("MCC: RegenParam: Stand by mode not 0 or 1: " + str(value))
        else:
            return self.send_mcc_cmd("P" + str(param) + str(value))

    # 2.20 • Regeneration Sequence pg:17
    def get_regen_step(self):  # Command Ex: "$O>\r"
        return self.send_mcc_cmd("O")

    # 2.21 • Regeneration Start Delay pg.18
    def get_regen_start_delay(self):  # Command Ex: "$j?[\r"
        val = self.send_mcc_cmd("j?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def set_regen_start_delay(self, delay):
        if (delay < 0) or (delay > 59994):
            raise RuntimeError('Regeneration Start Delay out is of range (0-59994): {:d}'.format(delay))
        return self.send_mcc_cmd("j{0:d}".format(delay))

    # 2.22 • Regeneration Step Timer pg:18
    def get_regen_step_timer(self):  # Command Ex: "$kZ\r"
        val = self.send_mcc_cmd("k")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.23 • Regeneration Time pg:19
    def get_regen_time(self):  # Command Ex: "$aP\r"
        val = self.send_mcc_cmd("a")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    # 2.24 • Rough On/Off/Query pg:19
    def get_roughing_valve_state(self):  # Command Ex: "$D?3\r"
        val = self.send_mcc_cmd("D?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def open_roughing_valve(self):  # Command Ex: "$D1d\r"
        return self.send_mcc_cmd("D1")

    def close_roughing_valve(self):
        return self.send_mcc_cmd("D0")

    # 2.25 • Rough Valve Interlock pg:20
    def get_roughing_interlock(self):  # Command Ex: "$Q?B\r"
        val = self.send_mcc_cmd("Q?")
        if not val['Error']:
            val['Data'] = int(val['Response']) - 0x30
        return val

    def clear_roughing_interlock(self):  # Command Ex: "$Q?B\r"
        return self.send_mcc_cmd("Q")

    # 2.26 • Second Stage Temperature pg:20
    def get_second_stage_temp(self):  # Command Ex: "$K:\r"
        val = self.send_mcc_cmd("K")
        if not val['Error']:
            val['Data'] = float(val['Response'])
        return val

    # 2.27 • Second Stage Temperature Control pg:21
    def get_second_stage_temp_ctl(self):  # Command Ex: "$I?:\r"
        val = self.send_mcc_cmd("I?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def set_second_stage_temp_ctl(self, temp):  # Command Ex: "$I?:\r"
        if (temp < 0) | (temp > 320):
            raise RuntimeError('MCC: Second stage Temperature out is of range (0-320): {:d}'.format(temp))
        return self.send_mcc_cmd("I{0:d}".format(temp))

    # 2.28 • Status pg:22
    def get_status_cmd(self):  # Command Ex: "$S16\r"
        val = self.send_mcc_cmd("S1")
        if (not val['Error']) & (len(val['Response']) == 1):
            val['Data'] = ord(val['Response']) - 0x20
        return val

    # 2.29 • TC On/Off/Query pg:22
    def get_tc_pressure_state(self):  # Command Ex: "$B?3\r"
        val = self.send_mcc_cmd("B?")
        if not val['Error']:
            val['Data'] = int(val['Response'])
        return val

    def turn_tc_pressure_on(self):  # Command Ex: "$B1b\r"
        return self.send_mcc_cmd("B1")

    def turn_tc_pressure_off(self):  # Command Ex: "$B?3\r"
        return self.send_mcc_cmd("B0")

    # 2.30 • Thermocouple Pressure pg:22
    def get_tc_pressure(self):  # Command Ex: "$L=\r"
        val = self.send_mcc_cmd("L")
        if not val['Error']:
            val['Data'] = float(val['Response']) / 1000  # Change to Torr
        return val