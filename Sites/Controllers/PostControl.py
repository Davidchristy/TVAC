from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance
from ThreadControls.ThreadCollectionInstance import ThreadCollectionInstance
import ThreadControls.ThreadHelperFunctions as ThreadHelperFunctions
import Collections.ProfileHelperFunctions as ProfileHelperFunctions
from Logging.Logging import Logging


def load_profile(data):
    if not HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed:
        return "{'Error door is open':'Error: Door is open'}"
    pi = ProfileInstance.getInstance()
    return pi.load_profile(data["profile_name"])


def save_profile(data):
    pi = ProfileInstance.getInstance()
    return ProfileHelperFunctions.save_profile(data, pi=pi)


def hold_single_thread(data):
    thread_instance = ThreadCollectionInstance.getInstance()
    thread_instance.threadCollection.holdThread(data)
    return "{'result':'success'}"


# TODO: What if this doesn't work?
def release_hold_single_thread(data):
    ThreadHelperFunctions.release_hold()
    return "{'result':'success'}"


def send_hw_cmd(data):
    if type(data) is not list:
        return '{"result":"Needs a json dictionary of a cmds."}'
    hw = HardwareStatusInstance.getInstance()
    Logging.debug_print(3, "POST: SendHwCmd '%s'" % data)
    if data[0] == "Shi_MCC_Cmds":  # ['cmd', arg, arg,... arg]
        hw.shi_mcc_cmds.append(data[1:])
    elif data[0] == "Shi_Compressor_Cmds":  # 'cmd'
        hw.shi_compressor_cmds.append(data[1])
    elif data[0] == "TdkLambda_Cmds":  # ['cmd', arg, arg,... arg]
        hw.tdk_lambda_cmds.append(data[1:])
    else:
        return '{"result":"Unknown Hardware Target."}'
    return '{"result":"success"}'


def set_pc_104_digital(data):
    if HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed:
        pins = HardwareStatusInstance.getInstance().pc_104
        Logging.debug_print(3, "POST: setPC104_Digital '%s'" % data)
        pins.digital_out.update(data)
        Logging.debug_print(4, "Digital out data: '%s'" % pins.digital_out.getJson())
        return "{'result':'success'}"
    else:
        return "{'result':'error'}"


def set_pc_104_analog(data):
    if HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed:
        pins = HardwareStatusInstance.getInstance().pc_104
        pins.analog_out.update(data)
        return "{'result':'success'}"
    else:
        return "{'result':'error'}"

def heat_up_shroud(data):
    duty_cycle = float(data['dutyCycle'])
    tdk_lambda = HardwareStatusInstance.getInstance().tdk_lambda_ps
    if not ProfileInstance.getInstance().active_profile:
        if duty_cycle == 0:
            if tdk_lambda.get_shroud_left().output_enable or tdk_lambda.get_shroud_right().output_enable:
                HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Disable Shroud Output'])
                return "{'result':'Disabled Shroud'}"
            else:
                return "{'result':'Shroud Off'}"
        else:
            if not (tdk_lambda.get_shroud_left().output_enable and tdk_lambda.get_shroud_right().output_enable):
                HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Setup Shroud'])
                print("Turning on Shroud")
            HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Shroud Duty Cycle', duty_cycle])
            return "{'result':'Shroud duty cycle set'}"
    else:
        return "{'result':'Not used in Profile'}"


def heat_up_platen(data):
    duty_cycle = float(data['dutyCycle'])
    tdk_lambda = HardwareStatusInstance.getInstance().tdk_lambda_ps
    if not ProfileInstance.getInstance().active_profile:
        if duty_cycle == 0:
            if tdk_lambda.get_platen_left().output_enable or tdk_lambda.get_platen_right().output_enable:
                HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Disable Platen Output'])
                return "{'result':'Disabled Platen'}"
            else:
                return "{'result':'Platen Off'}"
        else:
            if not (tdk_lambda.get_platen_left().output_enable and tdk_lambda.get_platen_right().output_enable):
                HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Setup Platen'])
            HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Platen Duty Cycle', duty_cycle])
            return "{'result':'Platen duty cycle set'}"
    else:
        return "{'result':'Not used in Profile'}"



