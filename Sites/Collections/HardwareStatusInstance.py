import os

from Collections.ThermocoupleCollection import ThermocoupleCollection
from Collections.PfeifferGaugeCollection import PfeifferGaugeCollection
from Collections.ShiCryopumpCollection import ShiCryopumpCollection
from Collections.TdkLambdaCollection import TdkLambdaCollection
from Collections.PC_104_Instance import PC_104_Instance

from Logging.Logging import Logging


class HardwareStatusInstance:
    # Here will be the instance stored.
    __instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if not HardwareStatusInstance.__instance:
            HardwareStatusInstance()
        return HardwareStatusInstance.__instance

    def __init__(self):
        if HardwareStatusInstance.__instance:
            raise Exception("This class is a singleton!")
        else:
            Logging.logEvent("Debug","Status Update", 
                {"message": "Creating HardwareStatusInstance",
                 "level":2})
            self.thermocouples = ThermocoupleCollection()
            self.pfeiffer_gauges = PfeifferGaugeCollection()
            self.shi_cryopump = ShiCryopumpCollection()
            self.shi_mcc_cmds = []  # ['cmd', arg, arg,... arg]
            self.shi_compressor_cmds = []  # 'cmd'
            self.tdk_lambda_ps = TdkLambdaCollection()
            self.tdk_lambda_cmds = []  # ['cmd', arg, arg,... arg]
            self.pc_104 = PC_104_Instance.getInstance()

            # System Wide Stats
            if os.name == "posix":
                user_name = os.environ['LOGNAME']
            else:
                user_name = "user"
            if "root" in user_name:
                self.operational_vacuum = False
                
            else:
                self.operational_vacuum = True
            self.vacuum_state = None

            self.pfeiffer_gauge_power = True
            self.shi_compressor_power = True
            self.shi_mcc_power = True
            self.tdk_lambda_power = True
            self.thermocouple_power = True
            self.pc_104_power = True

            self.overheated_tc = False




            HardwareStatusInstance.__instance = self
