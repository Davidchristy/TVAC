from Collections.HardwareStatusInstance import HardwareStatusInstance
from Logging.Logging import Logging


def enter_safe_mode(pi, error_mesg):
    pi.active_profile = False
    hw = HardwareStatusInstance.getInstance()
    Logging.debug_print(1, error_mesg)
    print(error_mesg)
    d_out = HardwareStatusInstance.getInstance().pc_104.digital_out
    d_out.update({"IR Lamp 1 PWM DC": 0})
    d_out.update({"IR Lamp 2 PWM DC": 0})
    d_out.update({"IR Lamp 3 PWM DC": 0})
    d_out.update({"IR Lamp 4 PWM DC": 0})
    d_out.update({"IR Lamp 5 PWM DC": 0})
    d_out.update({"IR Lamp 6 PWM DC": 0})
    d_out.update({"IR Lamp 7 PWM DC": 0})
    d_out.update({"IR Lamp 8 PWM DC": 0})
    d_out.update({"IR Lamp 9 PWM DC": 0})
    d_out.update({"IR Lamp 10 PWM DC": 0})
    d_out.update({"IR Lamp 11 PWM DC": 0})
    d_out.update({"IR Lamp 12 PWM DC": 0})
    d_out.update({"IR Lamp 13 PWM DC": 0})
    d_out.update({"IR Lamp 14 PWM DC": 0})
    d_out.update({"IR Lamp 15 PWM DC": 0})
    d_out.update({"IR Lamp 16 PWM DC": 0})
    HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Shroud Duty Cycle', 0])
    HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Platen Duty Cycle', 0])
    hw.pc_104.digital_out.update({'LN2-S Sol': False})
    hw.pc_104.analog_out.update({'LN2 Shroud': 0})
    hw.pc_104.digital_out.update({'LN2-P Sol': False})
    hw.pc_104.analog_out.update({'LN2 Platen': 0})