import datetime
from threading import Thread

from Hardware_Drivers.Shi_Compressor import ShiCompressor
from Hardware_Drivers.ShiMcc import ShiMcc
from Hardware_Drivers.Tdk_lamda_Genesys import TdkLambdaGenesys
from Hardware_Drivers.Keysight34980ATcs import Keysight34980ATcs

from ThreadControls.updaters.helperFunctions.MccUpdateFunctions import *
from ThreadControls.updaters.helperFunctions.TcUpdateFunctions import *
from ThreadControls.updaters.helperFunctions.TdkUpdateFunctions import *
from ThreadControls.updaters.helperFunctions.CompUpdateFunctions import *

from ThreadControls.SafetyCheckHelperFunctions import enter_safe_mode, log_event

class HardwareUpdater(Thread):
    def __init__(self, parent=None):
        Thread.__init__(self, name="HardwareUpdater")

        try:
            self.compressor = ShiCompressor()
            self.comp_status_period = 3
            self.comp_uptime_period = 120  # 120s = 2 min read period

            self.mcc = ShiMcc()
            self.mcc_param_period = 30
            self.mcc_status_period = 0.5

            self.tdk_lambda = TdkLambdaGenesys()

            self.keysight = Keysight34980ATcs()
            self.tc_read_period = 5

        except Exception as e:
            # TODO: Make this "go up" to the client computer?
            print("ERROR: There has been en error initializing, the hardwareUpdater Thread ({})".format(e))
            raise e

    def run(self):
        pi = ProfileInstance.getInstance()
        # While true to restart the thread if it errors out
        while True:
            # Catch anything that goes wrong
            try:
                # Thread "Start up" stuff goes here
                Logging.logEvent("Debug", "Status Update",
                                {"message": "Starting Shi Compressor Updater",
                                "level": 2})

                comp_next_uptime_read, comp_next_status_read = initialize_shi_compressor(compressor=self.compressor)

                tc_read_time = initialize_thermocouples(self.keysight)

                next_mcc_param_read_time, mcc_status_read_time = initialize_shi_mcc(self.mcc)

                initialize_tdk_lambdas(self.tdk_lambda)

                while True:
                    # TODO: remove next line when done testing
                    start_time = time.time()

                    comp_next_uptime_read, comp_next_status_read = \
                        shi_compressor_update(compressor=self.compressor,
                                              comp_next_uptime_read = comp_next_uptime_read,
                                              comp_uptime_period = self.comp_uptime_period,
                                              comp_next_status_read = comp_next_status_read,
                                              comp_status_period = self.comp_status_period)

                    next_mcc_param_read_time, mcc_status_read_time = shi_mcc_update(mcc=self.mcc,
                                                                      next_param_read_time = next_mcc_param_read_time,
                                                                      mcc_param_period =     self.mcc_param_period,
                                                                      mcc_status_read_time = mcc_status_read_time,
                                                                      mcc_status_period=     self.mcc_status_period)

                    tc_read_time = thermocouple_update(self.keysight,
                                                       tc_read_time=tc_read_time,
                                                       tc_read_period=self.tc_read_period)


                    # This has no timer because it has no regular checks.
                    tdk_lambda_update(tdk_lambda=self.tdk_lambda)


                    print("Loop time: {}".format(round(time.time()-start_time,4)))
                    time.sleep(.05)

                #end of inner while true
            # end of try
            except Exception as e:
                # Safe the system here
                error_details = "Unknown Hardware Error: ({})".format(e)
                error_log = {
                    "time": str(datetime.datetime.now()),
                    "event": "Hardware Error",
                    "item": "Unknown",
                    "itemID": 0,
                    "details": error_details,
                    "actions": ["Log Event"]
                }
                enter_safe_mode(error_details)
                log_event(error_log, pi.error_list)
                pi.active_profile = False
            # Sleep for a second if it fails
            time.sleep(1)
        #end while True
    # End run()
