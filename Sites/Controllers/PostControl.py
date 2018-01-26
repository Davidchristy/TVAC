from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance
from ThreadControls.ThreadCollectionInstance import ThreadCollectionInstance

from Logging.Logging import Logging


def load_profile(data):
    profile_instance = ProfileInstance.getInstance()
    return profile_instance.zoneProfiles.load_profile(data["profile_name"])


def save_profile(data):
    profile_instance = ProfileInstance.getInstance()
    return profile_instance.zoneProfiles.save_profile(data)


def pause_single_thread(data):
    threadInstance = ThreadCollectionInstance.getInstance()
    threadInstance.threadCollection.pause(data)
    return "{'result':'success'}"


def remove_pause_single_thread(data):
    thread_instance = ThreadCollectionInstance.getInstance()
    thread_instance.threadCollection.removePause(data)
    return "{'result':'success'}"


def hold_single_thread(data):
    thread_instance = ThreadCollectionInstance.getInstance()
    thread_instance.threadCollection.holdThread(data)
    return "{'result':'success'}"


def release_hold_single_thread(data):
    thread_instance = ThreadCollectionInstance.getInstance()
    thread_instance.threadCollection.releaseHoldThread(data)
    return "{'result':'success'}"


def send_hw_cmd(data):
    if type(data) is not list:
        return '{"result":"Needs a json dictionary of a cmds."}'
    hw = HardwareStatusInstance.getInstance()
    Logging.debugPrint(3,"POST: SendHwCmd '%s'" % data)
    if data[0] == "Shi_MCC_Cmds":  # ['cmd', arg, arg,... arg]
        hw.Shi_MCC_Cmds.append(data[1:])
    elif data[0] == "Shi_Compressor_Cmds":  # 'cmd'
        hw.Shi_Compressor_Cmds.append(data[1])
    elif data[0] == "TdkLambda_Cmds":  # ['cmd', arg, arg,... arg]
        hw.TdkLambda_Cmds.append(data[1:])
    else:
        return '{"result":"Unknown Hardware Target."}'
    return '{"result":"success"}'


def set_pc_104_digital(data):
    pins = HardwareStatusInstance.getInstance().pc_104
    Logging.debugPrint(3,"POST: setPC104_Digital '%s'" % data)
    pins.digital_out.update(data)
    Logging.debugPrint(4,"Digital out data: '%s'" % pins.digital_out.getJson())
    return "{'result':'success'}"


def set_pc_104_analog(data):
    pins = HardwareStatusInstance.getInstance().pc_104
    pins.analog_out.update(data)
    return "{'result':'success'}"


def heat_up_shroud(data):
    duty_cycle = float(data['dutyCycle'])
    tdk_lambda = HardwareStatusInstance.getInstance().tdk_lambda_ps
    if not ProfileInstance.getInstance().activeProfile:
        if duty_cycle == 0:
            if tdk_lambda.get_shroud_left().output_enable or tdk_lambda.get_shroud_right().output_enable:
                HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Disable Shroud Output'])
                return "{'result':'Disabled Shroud'}"
            else:
                return "{'result':'Shroud Off'}"
        else:
            if not (tdk_lambda.get_shroud_left().output_enable and tdk_lambda.get_shroud_right().output_enable):
                HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Setup Shroud'])
                print("Turning on Shroud")
            HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Shroud Duty Cycle', duty_cycle])
            return "{'result':'Shroud duty cycle set'}"
    else:
        return "{'result':'Not used in Profile'}"


def heat_up_platen(data):
    duty_cycle = float(data['dutyCycle'])
    tdk_lambda = HardwareStatusInstance.getInstance().tdk_lambda_ps
    if not ProfileInstance.getInstance().activeProfile:
        if duty_cycle == 0:
            if tdk_lambda.get_platen_left().output_enable or tdk_lambda.get_platen_right().output_enable:
                HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Disable Platen Output'])
                return "{'result':'Disabled Platen'}"
            else:
                return "{'result':'Platen Off'}"
        else:
            if not (tdk_lambda.get_platen_left().output_enable and tdk_lambda.get_platen_right().output_enable):
                HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Setup Platen'])
            HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Platen Duty Cycle', duty_cycle])
            return "{'result':'Platen duty cycle set'}"
    else:
        return "{'result':'Not used in Profile'}"



