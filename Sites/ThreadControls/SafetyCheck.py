from threading import Thread
import time
from datetime import datetime
from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance
from Logging.Logging import Logging
from ThreadControls.SafetyCheckHelperFunctions import power_failure, log_event, \
    log_removed_tcs, test_if_left_vacuum_while_vacuum_wanted, test_thermocouples_for_errors
from ThreadControls.helperFunctions.safe_mode import enter_safe_mode


class SafetyCheck(Thread):
    """
    SafetyCheck is the thread that runs the sainty and safety checks over the system.
    If it finds anything wrong with the the system it makes an error report and stores it in a queue
    to be seen by the client.
    """
    __instance = None

    def __init__(self, parent):
        if SafetyCheck.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            Logging.logEvent("Debug", "Status Update",
                             {"message": "Creating SafetyCheck",
                              "level": 2})
            self.errorDict = {
                "System Alarm: High Temperature": False,
                "Product Saver Alarm: High Temperature": False,
                "Product Saver Alarm: Low Temperature": False,
                "Human Touch Alarm: High Temperature": False,
                "Human Touch Alarm: Low Temperature": False,
                "Raised Pressure While Testing": False,
                "Thermocouple Disconnected": False,
                "Power Loss": False
            }

            self.SLEEP_TIME = 1  # in seconds

            SafetyCheck.__instance = self
            self.parent = parent
            super(SafetyCheck, self).__init__(name="SafetyChecker")

    def run(self):
        hw = HardwareStatusInstance.getInstance()
        pi = ProfileInstance.getInstance()
        # This should always stay on
        while True:
            # initialization of the safety Thread
            try:
                # Temps are in Kelvin
                MAX_OPERATING_TEMP = 437
                # safe at all lower bounds
                # MIN_OPERATING_TEMP

                MAX_TOUCH_TEMP = 318.15
                MIN_TOUCH_TEMP = 269.15


                Logging.logEvent("Debug", "Status Update",
                                 {"message": "Starting Safety Checker Thread",
                                  "level": 3})
                # stop when the program ends
                while True:
                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "Running Safety Checker Thread",
                                      "level": 4})

                    temp_error_dict = {
                        "System Alarm: High Temperature": False,
                        "Product Saver Alarm: High Temperature": False,
                        "Product Saver Alarm: Low Temperature": False,
                        "Human Touch Alarm: High Temperature": False,
                        "Human Touch Alarm: Low Temperature": False,
                        "Pressure Loss In Profile": False,
                        "Thermocouple Disconnected": False,
                        "Power Loss": False
                    }


                    # This is removed for now, because it's been added to all the sections that might have power failer
                    # and is duplicated code. Still want to have in case needed later
                    # if power_failure():
                    #     error_log = {
                    #         "time": str(datetime.now()),
                    #             "event": "Power Loss",
                    #             "item": "Unknown",
                    #             "itemID": 0,
                    #             "details": "There has been a connection or power failure, check status page for details.",
                    #             "actions": ["Log Event"]
                    #     }
                    #     log_event(error_log, pi.error_list)
                    #     if pi.active_profile:
                    #         enter_safe_mode("There has been a power failure during a profile.")

                    log_removed_tcs(hw)

                    test_thermocouples_for_errors(MAX_OPERATING_TEMP, MAX_TOUCH_TEMP, MIN_TOUCH_TEMP, temp_error_dict)

                    self.errorDict = temp_error_dict

                    test_if_left_vacuum_while_vacuum_wanted(hw, pi, temp_error_dict)

                    time.sleep(self.SLEEP_TIME)
            # end of inner while true loop
            except Exception as e:
                Logging.debug_print(1, "Error in Safety Checker: {}".format(str(e)))
                time.sleep(self.SLEEP_TIME)
        # end of try/except


