from Collections.HardwareStatusInstance import HardwareStatusInstance
from Logging.Logging import Logging
from Collections.ProfileInstance import ProfileInstance
from ThreadControls.SafetyCheckHelperFunctions import log_hw_error

def initialize_tdk_lambdas(tdk_lambda):
    hw = HardwareStatusInstance.getInstance()
    pi = ProfileInstance.getInstance()
    # Thread "Start up" stuff goes here
    Logging.logEvent("Debug", "Status Update",
                     {"message": "TDK Lambda Genesys Control Stub Thread",
                      "level": 2})
    update_power_supplies = [{'addr': hw.tdk_lambda_ps.get_platen_left_addr()},
                             {'addr': hw.tdk_lambda_ps.get_platen_right_addr()},
                             {'addr': hw.tdk_lambda_ps.get_shroud_left_addr()},
                             {'addr': hw.tdk_lambda_ps.get_shroud_right_addr()}]
    try:
        tdk_lambda.open_port()
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
            ps.update(tdk_lambda.get_mode())
    except RuntimeError as e:
        item = "TDK Lambda"
        error_details = "ERROR: {}: There has been an error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
    except TimeoutError as e:
        HardwareStatusInstance.getInstance().tdk_lambda_power  = False
        item = "TDK Lambda"
        error_details = "ERROR: {}: There has been a Timeout error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
    else:
        HardwareStatusInstance.getInstance().tdk_lambda_power = True
    hw.tdk_lambda_ps.update_tdk_lambda(update_power_supplies)



def tdk_lambda_update(tdk_lambda):
    hw = HardwareStatusInstance.getInstance()
    pi = ProfileInstance.getInstance()
    if hw.operational_vacuum:
        try:
            # This is here to clear any old data that might be in the port, waiting for .2 seconds to allow for HW to reply
            tdk_lambda.flush_port(.2)

            # Loop through all the potential commands to do.
            while hw.tdk_lambda_cmds:
                cmd = hw.tdk_lambda_cmds.pop(0)
                process_tkd_lambda_command(cmd, tdk_lambda=tdk_lambda)

        except RuntimeError as e:
            item = "TDK Lambda"
            error_details = "ERROR: {}: There has been an error with the {} ({})".format(item, item, e)
            log_hw_error(pi=pi, item=item, error_details=error_details)
        except TimeoutError as e:
            hw.tdk_lambda_power = False
            item = "TDK Lambda"
            error_details = "ERROR: {}: There has been a Timeout error with the {} ({})".format(item, item, e)
            log_hw_error(pi=pi, item=item, error_details=error_details)
        else:
            hw.tdk_lambda_power = True


def process_tkd_lambda_command(cmd, tdk_lambda):
    """
    A small helper function for processing TDK Commands
    :param cmd:
    :param tdk_lambda:
    :return:
    """
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
        # If these are used, you can skip the rest of the code
        return

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
        raise RuntimeError("TDK: The given command: ({}) is not in the list of known tdk commands".format(cmd[0]))

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
        duty_cycle_max_capped = min(1.0, duty_cycle_raw)
        duty_cycle = max(0.0, duty_cycle_max_capped)

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

