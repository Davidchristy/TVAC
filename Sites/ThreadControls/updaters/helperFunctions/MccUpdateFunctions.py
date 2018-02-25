import time
from Collections.HardwareStatusInstance import HardwareStatusInstance
from Logging.Logging import Logging

def run_get_cmd(fun, key):
    hw = HardwareStatusInstance.getInstance()
    val = fun()
    if val['Error']:
        Logging.logEvent("Debug", "Status Update",
                         {"message": 'Shi MCC Get_"%s" Error Response: %s' % (key, val),
                          "level": 3})
    else:
        if 'Data' in val:
            hw.shi_cryopump.update_shi_cryopump({'MCC Params': {key: val['Data']}})
        else:
            hw.shi_cryopump.update_shi_cryopump({'MCC Params': {key: val['Response']}})

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
        "Turn_CryoPumpOn":        mcc.turn_cryopump_on,        # 2.14 • Pump On/Off/Query pg:13
        "Turn_CryoPumpOff":       mcc.turn_cryopump_off,       # 2.14 • Pump On/Off/Query pg:13
        "Close_PurgeValve":       mcc.close_purge_valve,       # 2.15 • Purge On/Off/Query pg:14
        # Open_PurgeValve never used
        "Open_PurgeValve":        mcc.open_purge_valve,        # 2.15 • Purge On/Off/Query pg:14
        "Start_Regen":            mcc.start_regen,            # 2.16 • Regeneration pg:14
        "Open_RoughingValve":     mcc.open_roughing_valve,     # 2.24 • Rough On/Off/Query pg:19
        "Close_RoughingValve":    mcc.close_roughing_valve,    # 2.24 • Rough On/Off/Query pg:19
        "Clear_RoughingInterlock":mcc.clear_roughing_interlock,# 2.25 • Rough Valve Interlock pg:20
        # Turn_TcPressureOn never used
        "Turn_TcPressureOn":      mcc.turn_tc_pressure_on,      # 2.29 • TC On/Off/Query pg:22
        # Turn_TcPressureOff never used
        "Turn_TcPressureOff":     mcc.turn_tc_pressure_off      # 2.29 • TC On/Off/Query pg:22
    }
    temp_func = mcc_cmds.get(cmd[0],None)
    if temp_func:
        run_set_mcc_cmd(temp_func, cmd)

    if 'FirstStageTempCTL' == cmd[0]:  # 2.9 • First Stage Temperature Control pg:10
        run_set_mcc_cmd(mcc.set_first_stage_temp_ctl, cmd)
        run_get_cmd(mcc.get_first_stage_temp_ctl,
                         "First Stage Temp CTL")
    elif 'PowerFailureRecovery' == cmd[0]:  # 2.12 • Power Failure Recovery pg:11
        run_set_mcc_cmd(mcc.set_power_failure_recovery, cmd)
        run_get_cmd(mcc.get_power_failure_recovery,
                         "Power Failure Recovery")
    elif 'Set_RegenParam' == cmd[0]:  # 2.19 • Regeneration Parameters pg:16
        run_set_mcc_cmd(mcc.set_regen_param, cmd)
        val = mcc.get_regen_param(cmd[1])
        hw.shi_cryopump.update_shi_cryopump({'MCC Params': {"Regen Param_%s" % cmd[1]: val['Data']}})
    # Never used?
    elif 'RegenStartDelay' == cmd[0]:  # 2.21 • Regeneration Start Delay pg.18
        run_set_mcc_cmd(mcc.set_regen_start_delay, cmd)
        run_get_cmd(mcc.get_regen_start_delay,
                    "Regen Start Delay")
    elif 'SecondStageTempCTL' == cmd[0]:  # 2.27 • Second Stage Temperature Control pg:21
        run_set_mcc_cmd(mcc.set_second_stage_temp_ctl, cmd)
        run_get_cmd(mcc.get_second_stage_temp_ctl,
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
    try:


        # I don't know what this is talking about
        # TODO: Log better events
        Logging.logEvent("Debug", "Status Update",
                         {"message": "Power on the Shi Mcc",
                          "level": 3})

        # starting the helper thread to read the fifo file
        mcc.open_port()

        # Checks to see if the MCC is currently powered,
        currently_powered = hw.pc_104.digital_out.getVal('MCC2 Power')

        # If it isn't it turns on.
        # TODO: Turn this into loop
        print("about to wait for MCC to turn on")
        hw.pc_104.digital_out.update({'MCC2 Power': True})
        if not currently_powered:
            time.sleep(1)
        print("MCC should be on by now")

        # This is here to clear any old data that might be in the port, waiting for .2 seconds to allow for HW to reply
        mcc.flush_port(.2)

        # Now send some initialization commands:

        # 1: The maximum second stage temperature the cryopump may start to restart after a power failure, should be 65
        restart_temperature = mcc.get_regen_param_6()
        if restart_temperature['Data'] != 65:
            run_set_mcc_cmd(mcc.set_regen_param, [' ', '6', 65])

        # 2: Power failure recovery enabled only when T2 is less than the limit set point.
        power_failure_recovery_status = mcc.get_power_failure_recovery()
        if power_failure_recovery_status['Data'] != 2:
            run_set_mcc_cmd(mcc.set_regen_param, [' ', 2])

    except RuntimeError as e:
        print("ERROR: MCC: There has been an error with the Shi MCC ({})".format(e))
    except TimeoutError as e:
        print("ERROR: MCC: There has been a Timeout error with the MCC ({})".format(e))
        HardwareStatusInstance.getInstance().tdk_lambda_power = False
    else:
        HardwareStatusInstance.getInstance().tdk_lambda_power = True
    # This is next time the code should read mcc parameters...
    # It gets initialized to current time so they are read ASAP
    next_param_read_time = time.time()
    mcc_status_read_time = time.time()

    return next_param_read_time, mcc_status_read_time

def shi_mcc_update(mcc, next_param_read_time, mcc_param_period, mcc_status_read_time, mcc_status_period):
    hw = HardwareStatusInstance.getInstance()
    Logging.logEvent("Debug", "Status Update",
                     {"message": "Reading and writing with ShiMccUpdater.",
                      "level": 4})
    try:

        if time.time() > mcc_status_read_time:
            # update the time you need
            mcc_status_read_time = time.time() + mcc_status_period

            # collect the general status of the mcc
            val = mcc.get_shi_mcc_status()
            hw.shi_cryopump.update_shi_cryopump({'MCC Status': val['Response']})


        # if there has been enough time since the last param read, read them again.
        if time.time() > next_param_read_time:
            # update the time you need
            next_param_read_time = time.time() + mcc_param_period

            val = mcc.get_param_values()
            hw.shi_cryopump.update_shi_cryopump({'MCC Params': val['Response']})


        while len(hw.shi_mcc_cmds):
            cmd = hw.shi_mcc_cmds.pop()
            process_mcc_cmd(cmd, mcc)

    except RuntimeError as e:
        # TODO: This needs to log to something...anything really
        print("ERROR: MCC: There has been an error with the Shi MCC ({})".format(e))
    except TimeoutError as e:
        print("ERROR: MCC: There has been a Timeout error with the MCC ({})".format(e))
        HardwareStatusInstance.getInstance().tdk_lambda_power = False
    else:
        HardwareStatusInstance.getInstance().tdk_lambda_power = True

    return next_param_read_time, mcc_status_read_time