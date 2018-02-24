import os
import math
import time
from threading import Thread

from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance

from Hardware_Drivers.Shi_Compressor import ShiCompressor
from Hardware_Drivers.Keysight_34980A_TCs import Keysight_34980A_TCs
from Hardware_Drivers.Shi_Mcc import Shi_Mcc
from Hardware_Drivers.Tdk_lamda_Genesys import Tdk_lambda_Genesys

from Logging.Logging import Logging


def initialize_shi_compressor(compressor):
    hw = HardwareStatusInstance.getInstance()

    Logging.logEvent("Debug", "Status Update",
                     {"message": "Power on the Shi Compressor",
                      "level": 3})

    # This starts the helper thread for reading the fifo file
    compressor.open_port()

    print("initialize_shi_compressor: waiting for system to be ready")

    # Waiting until the system is reading the power of the Cryo Pump
    while hw.pc_104.digital_out.getVal('CryoP Pwr Relay 1') is None:
        print("initialize_shi_compressor: waiting for digital out")
        time.sleep(1)



    # Checks if the power is power is on or not
    currently_powered = hw.pc_104.digital_out.getVal('CryoP Pwr Relay 1')

    # If it's not powered, ask system to turn it on and wait 5 seconds
    # TODO: It might be better to have a loop here, checking until it's on.
    hw.pc_104.digital_out.update({'CryoP Pwr Relay 1': True})
    if not currently_powered:
        print("initialize_shi_compressor: Waiting on currently_powered")
        time.sleep(5)

    print("initialize_shi_compressor: done waiting")

    # Honestly, I have no idea why this line is here, I didn't write it but don't want to take it out
    compressor.flush_port()


    next_op_hours_read_time = time.time()
    # setup is done, this loop is the normal thread loop
    return next_op_hours_read_time


def log_live_temperature_data(data):
    '''
    data = {
        "time":		TCs['time'],
        "tcList":	TCs['tcList'],
        "ProfileUUID": ProfileUUID,
    }
    TCs is a list of dicitations ordered like this....
    {
    'Thermocouple': tc_num,
    'time': tc_time_offset,
    'temp': tc_tempK,
    'working': tc_working,
    'alarm': tc_alarm
    }
    '''

    time = data["time"]
    profile = data["profileUUID"]
    coloums = "( profile_I_ID, time, thermocouple, temperature )"
    values = ""

    for tc in data['tcList']:
        thermocouple = tc["Thermocouple"]
        temperature = tc["temp"]
        if math.isnan(tc["temp"]):
            continue
        values += "( \"{}\", \"{}\", {}, {} ),\n".format(profile, time.strftime('%Y-%m-%d %H:%M:%S'), thermocouple,
                                                         temperature)
    sql = "INSERT INTO tvac.Real_Temperature {} VALUES {};".format(coloums, values[:-2])

    sql.replace("nan", "NULL")

    HardwareStatusInstance.getInstance().sql_list.append(sql)


def initialize_thermocouples():
    Logging.logEvent("Debug", "Status Update",
                     {"message": "Starting ThermoCoupleUpdater",
                      "level": 2})

    tharsis = Keysight_34980A_TCs()
    tharsis.init_sys()

    return tharsis


def thermocouple_updater(tharsis):
    hw = HardwareStatusInstance.getInstance()

    Logging.logEvent("Debug", "Status Update",
                     {"message": "Pulling live data for TC",
                      "level": 4})
    # Get the values from the TC's
    tc_values = tharsis.getTC_Values()

    if ProfileInstance.getInstance().record_data:
        log_live_temperature_data({"time": tc_values['time'],
                                   "tcList": tc_values['tcList'],
                                   "profileUUID": ProfileInstance.getInstance().zoneProfiles.profileUUID})

    Logging.logEvent("Debug", "Data Dump",
                     {"message": "Current TC reading",
                      "level": 4,
                      "dict": tc_values['tcList']})
    hw.thermocouples.update(tc_values)


def run_set_mcc_cmd(fun, cmd):
    if len(cmd) <= 1:
        val = fun()
    elif len(cmd) == 2:
        val = fun(cmd[1])
    elif len(cmd) == 3:
        val = fun(cmd[1],cmd[2])
    else:
        raise Exception('run_cmd has to many arguments')
    if val['Error']:
        Logging.logEvent("Debug", "Status Update",
                         {"message": 'Shi MCC Set_"%s" Error Response: %s' % (cmd[0], val),
                          "level": 3})


def run_get_cmd(fun, key):
    hw = HardwareStatusInstance.getInstance()
    val = fun()
    if val['Error']:
        Logging.logEvent("Debug", "Status Update",
                         {"message": 'Shi MCC Get_"%s" Error Response: %s' % (key, val),
                          "level": 3})
    else:
        if 'Data' in val:
            hw.shi_cryopump.update({'MCC Params': {key: val['Data']}})
        else:
            hw.shi_cryopump.update({'MCC Params': {key: val['Response']}})


def process_mcc_cmd(cmd, mcc):
    '''
    Notes references section and page number of the "Marathon Cryopump Controller Programmer's Reference Guide"
    Found in the documentation

    :param cmd:
    :param mcc:
    :return:
    '''
    hw = HardwareStatusInstance.getInstance()
    mcc_cmds = {
        "Turn_CryoPumpOn":        mcc.Turn_CryoPumpOn,        # 2.14 • Pump On/Off/Query pg:13
        "Turn_CryoPumpOff":       mcc.Turn_CryoPumpOff,       # 2.14 • Pump On/Off/Query pg:13
        "Close_PurgeValve":       mcc.Close_PurgeValve,       # 2.15 • Purge On/Off/Query pg:14
        # Open_PurgeValve never used
        "Open_PurgeValve":        mcc.Open_PurgeValve,        # 2.15 • Purge On/Off/Query pg:14
        "Start_Regen":            mcc.Start_Regen,            # 2.16 • Regeneration pg:14
        "Open_RoughingValve":     mcc.Open_RoughingValve,     # 2.24 • Rough On/Off/Query pg:19
        "Close_RoughingValve":    mcc.Close_RoughingValve,    # 2.24 • Rough On/Off/Query pg:19
        "Clear_RoughingInterlock":mcc.Clear_RoughingInterlock,# 2.25 • Rough Valve Interlock pg:20
        # TODO: GUI shi cryopump interface has a button for this, try tracking it down.
        # Turn_TcPressureOn never used
        "Turn_TcPressureOn":      mcc.Turn_TcPressureOn,      # 2.29 • TC On/Off/Query pg:22
        # Turn_TcPressureOff never used
        "Turn_TcPressureOff":     mcc.Turn_TcPressureOff      # 2.29 • TC On/Off/Query pg:22
    }
    temp_func = mcc_cmds.get(cmd[0],None)
    if temp_func:
        run_set_mcc_cmd(temp_func, cmd)

    if 'FirstStageTempCTL' == cmd[0]:  # 2.9 • First Stage Temperature Control pg:10
        run_set_mcc_cmd(mcc.Set_FirstStageTempCTL, cmd)
        run_get_cmd(mcc.Get_FirstStageTempCTL,
                         "First Stage Temp CTL")
    elif 'PowerFailureRecovery' == cmd[0]:  # 2.12 • Power Failure Recovery pg:11
        run_set_mcc_cmd(mcc.Set_PowerFailureRecovery, cmd)
        run_get_cmd(mcc.Get_PowerFailureRecovery,
                         "Power Failure Recovery")
    elif 'Set_RegenParam' == cmd[0]:  # 2.19 • Regeneration Parameters pg:16
        run_set_mcc_cmd(mcc.Set_RegenParam, cmd)
        val = mcc.Get_RegenParam(cmd[1])
        hw.shi_cryopump.update({'MCC Params': {"Regen Param_%s" % cmd[1]: val['Data']}})
    elif 'RegenStartDelay' == cmd[0]:  # 2.21 • Regeneration Start Delay pg.18
        run_set_mcc_cmd(mcc.Set_RegenStartDelay, cmd)
        run_get_cmd(mcc.Get_RegenStartDelay,
                    "Regen Start Delay")
    elif 'SecondStageTempCTL' == cmd[0]:  # 2.27 • Second Stage Temperature Control pg:21
        run_set_mcc_cmd(mcc.Set_SecondStageTempCTL, cmd)
        run_get_cmd(mcc.Get_SecondStageTempCTL,
                         "Second Stage Temp CTL")
    else:
        Logging.logEvent("Error", 'Unknown Shi_MCC_Cmd: "%s"' % cmd[0],
                         {"type": 'Unknown Shi_MCC_Cmd',
                          "filename": 'ThreadControls/ShiMccUpdater.py',
                          "line": 0,
                          "thread": "ShiMccUpdater"
                          })


def initialize_shi_mcc(mcc):
    """
    Initializes the Shi MCC to be used for our program. For more information about the commands used
    refer to "Marathon Cryopump Controller Programmer's Reference Guide" in the Documentation.
    :return:
    """
    hw = HardwareStatusInstance.getInstance()

    # I don't know what this is talking about
    Logging.logEvent("Debug", "Status Update",
                     {"message": "Power on the Shi Mcc",
                      "level": 3})

    # starting the helper thread to read the fifo file
    mcc.open_port()
    # waiting until the system can detect the...cryopump?
    # TODO: By this point, this shouldn't be needed.
    # Make assert instead?
    while hw.pc_104.digital_out.getVal('CryoP Pwr Relay 1') is None:
        time.sleep(1)

    # Checks to see if the MCC is currently powered,
    currently_powered = hw.pc_104.digital_out.getVal('MCC2 Power')

    # If it isn't it turns on.
    hw.pc_104.digital_out.update({'MCC2 Power': True})
    if not currently_powered:
        time.sleep(5)

    # No idea why this is here
    mcc.flush_port()

    # Now send some initialization commands:

    # 1: The maximum second stage temperature the cryopump may start to restart after a power failure, should be 65
    restart_temperature = mcc.Get_RegenParam_6()
    if restart_temperature['Data'] != 65:
        run_set_mcc_cmd(mcc.Set_RegenParam, [' ', '6', 65])

    # 2: Power failure recovery enabled only when T2 is less than the limit set point.
    power_failure_recovery_status = mcc.Get_PowerFailureRecovery()
    if power_failure_recovery_status['Data'] != 2:
        run_set_mcc_cmd(mcc.Set_RegenParam, [' ', 2])

    # This is next time the code should read mcc parameters...
    # It gets initialized to current time so they are read ASAP
    next_param_read_time = time.time()

    return next_param_read_time


def shi_mcc_update(mcc, next_param_read_time, mcc_param_period):
    hw = HardwareStatusInstance.getInstance()

    Logging.logEvent("Debug", "Status Update",
                     {"message": "Reading and writing with ShiMccUpdater.",
                      "level": 4})

    # TODO: This should have a timer attached as well
    # First collect the general status of the mcc
    val = mcc.get_status()
    hw.shi_cryopump.update({'MCC Status': val['Response']})

    # if there has been enough time since the last param read, read them again.
    if time.time() > next_param_read_time:
        val = mcc.get_ParamValues()
        hw.shi_cryopump.update({'MCC Params': val['Response']})

        # update the time you need
        next_param_read_time = time.time() + mcc_param_period

    while len(hw.shi_mcc_cmds):
        cmd = hw.shi_mcc_cmds.pop()
        process_mcc_cmd(cmd, mcc)

    return next_param_read_time


def initialize_tdk_lambdas(tdk_lambda):
    hw = HardwareStatusInstance.getInstance()
    # Thread "Start up" stuff goes here
    Logging.logEvent("Debug", "Status Update",
                     {"message": "TDK Lambda Genesys Control Stub Thread",
                      "level": 2})

    tdk_lambda.open_port()
    update_power_supplies = [{'addr': hw.tdk_lambda_ps.get_platen_left_addr()},
                             {'addr': hw.tdk_lambda_ps.get_platen_right_addr()},
                             {'addr': hw.tdk_lambda_ps.get_shroud_left_addr()},
                             {'addr': hw.tdk_lambda_ps.get_shroud_right_addr()}]
    for ps in update_power_supplies:
        tdk_lambda.set_addr(ps['addr'])
        ps.update(tdk_lambda.get_out())
        if not hw.operational_vacuum:
            tdk_lambda.set_out_off()
        ps.update(tdk_lambda.get_idn())
        ps.update(tdk_lambda.get_rev())
        ps.update(tdk_lambda.get_sn())
        ps.update(tdk_lambda.get_date())
        ps.update(tdk_lambda.get_ast())
        ps.update(tdk_lambda.get_out())
        ps.update(tdk_lambda.get_mode())
    hw.tdk_lambda_ps.update(update_power_supplies)
    next_status_read_time = time.time()
    return next_status_read_time


def process_tkd_lambda_command(cmd, tdk_lambda):
    hw = HardwareStatusInstance.getInstance()

    # None of these are used
    set_heater_cmds = {
        "Set Platen Left":  hw.tdk_lambda_ps.get_platen_left_addr(),
        "Set Platen Right": hw.tdk_lambda_ps.get_platen_right_addr(),
        "Set Shroud Left":  hw.tdk_lambda_ps.get_shroud_left_addr(),
        "Set Shroud Right": hw.tdk_lambda_ps.get_shroud_right_addr()
    }
    if cmd[0] in set_heater_cmds:
        power_type = {
            "V":tdk_lambda.set_pv,
            "C":tdk_lambda.set_pc,
        }
        tdk_lambda.set_addr(set_heater_cmds[cmd[0]])
        power_type[cmd[2]](cmd[1])

    tdk_lambda_cmds = [
        # Not used
        'Enable All Output',
        # Not used
        'Enable Platen Output',
        # not used
        'Enable Shroud Output'
        'Setup Platen',
        'Setup Shroud',
        'Disable All Output'
        'Disable Platen Output',
        'Disable Shroud Output',
        'Platen Duty Cycle',
        'Shroud Duty Cycle'
    ]

    # Check to see if it's in the list of commands
    if cmd[0] not in tdk_lambda_cmds:
        # TODO: Make this more offical
        print("Command not known")
        return

    tmp_list = []
    current_scale = 0
    # only list platen addresses
    if "Platen" in cmd[0]:
        current_scale = 5.5
        tmp_list = [hw.tdk_lambda_ps.get_platen_left_addr(),
                    hw.tdk_lambda_ps.get_platen_right_addr()]
    # only list shroud addresses
    if "Shroud" in cmd[0]:
        current_scale = 3
        tmp_list = [hw.tdk_lambda_ps.get_shroud_left_addr(),
                    hw.tdk_lambda_ps.get_shroud_right_addr()]
    # list all addresses
    if "All" in cmd[0]:
        tmp_list = [hw.tdk_lambda_ps.get_platen_left_addr(),
                    hw.tdk_lambda_ps.get_platen_right_addr(),
                    hw.tdk_lambda_ps.get_shroud_left_addr(),
                    hw.tdk_lambda_ps.get_shroud_right_addr()]

    # Setup might be needed, done here
    enable = None
    current = 0
    voltage = 0
    if "Enable" in cmd[0]:
        enable = True
    if "Disable" in cmd[0]:
        enable = False
    if "Duty Cycle" in cmd[0]:
        duty_cycle_raw = float(cmd[1])
        duty_cycle_max_capped = min(1, duty_cycle_raw)
        duty_cycle = max(0, duty_cycle_max_capped)

        current = duty_cycle * current_scale
        voltage = current * 80.0

    # Loop through the listed tdk's
    for tdk_addr in tmp_list:
        tdk_lambda.set_addr(tdk_addr)
        if "Output" in cmd[0]:
            tdk_lambda.set_out(enable)
        if "Setup" in cmd[0]:
            tdk_lambda.set_pc(0.0)
            tdk_lambda.set_pv(0.0)
            tdk_lambda.set_out_on()
        if "Duty Cycle" in cmd[0]:
            tdk_lambda.set_pc(current)
            tdk_lambda.set_pv(voltage)


def tdk_lambda_update(tdk_lambda, next_tdk_lambda_read_time, tdk_lambdas_read_peroid):
    hw = HardwareStatusInstance.getInstance()
    if hw.operational_vacuum:


        # TODO: Not sure on the location of flush port
        tdk_lambda.flush_port()

        # First we create a list of dictionaries, each representing a tdk lambda unit
        update_tdk_lambdas = [{'addr': hw.tdk_lambda_ps.get_platen_left_addr()},
                                 {'addr': hw.tdk_lambda_ps.get_platen_right_addr()},
                                 {'addr': hw.tdk_lambda_ps.get_shroud_left_addr()},
                                 {'addr': hw.tdk_lambda_ps.get_shroud_right_addr()}]

        # Cycle through them, if there is not an operational vacuum, and one of them is on, turn it off.
        for tdk in update_tdk_lambdas:
            tdk_lambda.set_addr(tdk['addr'])
            if not hw.operational_vacuum and hw.tdk_lambda_ps.get_val(tdk['addr'],'output enable'):
                Logging.debugPrint(2, "TDK, either not in vacuum, or turned off")
                tdk_lambda.set_out_off()
            # Updating the temp dictionary
            tdk.update(tdk_lambda.get_out())

        # Update the "real" version of them, with the info you just found
        hw.tdk_lambda_ps.update(update_tdk_lambdas)

        # If there not an operation vacuum, leave the function
        # TODO: I don't believe this section is needed, as we can put this check "lower"
        if not hw.operational_vacuum:
            for tdk in update_tdk_lambdas:
                tdk_lambda.set_addr(tdk['addr'])
                tdk_lambda.set_out_off()
            return

        # Loop through all the potential commands to do.
        while hw.tdk_lambda_cmds:
            cmd = hw.tdk_lambda_cmds.pop(0)
            process_tkd_lambda_command(cmd, tdk_lambda=tdk_lambda)


class HardwareUpdater(Thread):
    def __init__(self, parent=None):
        Thread.__init__(self, name="HardwareUpdater")
        self.parent = parent



        self.hw = HardwareStatusInstance.getInstance()

        self.compressor = ShiCompressor()
        self.op_hours_read_period = 120  # 120s = 2 min read period

        self.number_continuous_errors = 0
        self.MAX_NUMBER_OF_ERRORS = 3

        self.sleep_time = 3

        self.mcc = Shi_Mcc()
        self.mcc_param_period = 30  # 10 second period

        self.tdk_lambda = Tdk_lambda_Genesys()
        self.tdk_lambdas_read_peroid = 4.0  # 0.5s loop period

    def run(self):
        if os.name == "posix":
            user_name = os.environ['LOGNAME']
        else:
            user_name = "user"
        # While true to restart the thread if it errors out
        while True:
            # Catch anything that goes wrong
            try:
                # Thread "Start up" stuff goes here
                Logging.logEvent("Debug", "Status Update",
                                {"message": "Starting Shi Compressor Updater",
                                "level": 2})

                next_op_hours_read_time = initialize_shi_compressor(compressor=self.compressor)

                tharsis = initialize_thermocouples()

                next_mcc_param_read_time = initialize_shi_mcc(self.mcc)

                next_tdk_lambda_read_time = initialize_tdk_lambdas(self.tdk_lambda)

                while True:
                    next_op_hours_read_time = self.shi_compressor_update(next_op_hours_read_time)
                    HardwareStatusInstance.getInstance().shi_compressor_power = True

                    thermocouple_updater(tharsis)
                    HardwareStatusInstance.getInstance().thermocouple_power = True

                    next_mcc_param_read_time = shi_mcc_update(mcc=self.mcc,
                                                                   next_param_read_time = next_mcc_param_read_time,
                                                                   mcc_param_period = self.mcc_param_period)
                    HardwareStatusInstance.getInstance().shi_mcc_power = True

                    tdk_lambda_update(tdk_lambda=self.tdk_lambda,
                                           next_tdk_lambda_read_time=next_tdk_lambda_read_time,
                                           tdk_lambdas_read_peroid=self.tdk_lambdas_read_peroid)
                    HardwareStatusInstance.getInstance().tdk_lambda_power = True


                #end of inner while true
            # end of try
            except Exception as e:
                # TODO: REmove this!
                self.compressor.close_port()
                raise e


    def shi_compressor_update(self, next_op_hours_read_time):
        Logging.logEvent("Debug", "Status Update",
                         {"message": "Reading and writing with ShiCompressorUpdater.",
                          "level": 4})

        val = {}
        val.update(self.compressor.get_temperatures())
        val.update(self.compressor.get_pressure())
        val.update(self.compressor.get_status_bits())
        if time.time() > next_op_hours_read_time:
            val.update(self.compressor.get_id())
            next_op_hours_read_time += self.op_hours_read_period
        self.hw.shi_cryopump.update({'Compressor': val})
        while len(self.hw.shi_compressor_cmds):
            cmd = self.hw.shi_compressor_cmds.pop()
            if 'on' == cmd:
                self.compressor.set_compressor_on()
            elif 'off' == cmd:
                self.compressor.set_compressor_off()
            elif 'reset' == cmd:
                self.compressor.set_reset()
            else:
                Logging.logEvent("Error", 'Unknown Shi_Compressor_Cmds: "%s"' % cmd,
                                 {"type": 'Unknown Shi_Compressor_Cmds',
                                  "filename": 'ThreadControls/ShiCompressorUpdater.py',
                                  "line": 0,
                                  "thread": "ShiCompressorUpdater"
                                  })
            # end if/else
        # end while
        return next_op_hours_read_time
