from threading import Thread
import threading
import time
from datetime import datetime
import os
import subprocess

from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance
from Logging.MySql import MySQlConnect
from Logging.Logging import Logging

def release_hold_thread():
    ProfileInstance.getInstance().inHold = False
    sql = "UPDATE System_Status SET in_hold=0;"
    mysql = MySQlConnect()
    try:
        mysql.cur.execute(sql)
        mysql.conn.commit()
    except Exception as e:
        Logging.debugPrint(3, "sql: {}".format(sql))
        Logging.debugPrint(1, "Error in ThreadCollection, holdThread: {}".format(str(e)))
        if Logging.debug:
            raise e


def power_failure():
    results = True
    results = results and HardwareStatusInstance.getInstance().pfeiffer_gauge_power
    results = results and HardwareStatusInstance.getInstance().shi_compressor_power
    results = results and HardwareStatusInstance.getInstance().shi_mcc_power
    results = results and HardwareStatusInstance.getInstance().tdk_lambda_power
    results = results and HardwareStatusInstance.getInstance().thermocouple_power
    results = results and HardwareStatusInstance.getInstance().pc_104_power
    return not results


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
            self.errorList = []
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

            self.MAX_UUT_TEMP = {}
            self.MIN_UUT_TEMP = {}
            self.SLEEP_TIME = 1  # in seconds

            SafetyCheck.__instance = self
            self.parent = parent
            super(SafetyCheck, self).__init__(name="SafetyChecker")

    def run(self):
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

                # TODO, make this user defined
                # These are test values, they will change when the code is written to change them
                self.MAX_UUT_TEMP = {}
                self.MIN_UUT_TEMP = {}

                # Used to keep track of the first time through a loop
                vacuum = False

                hardwareStatusInstance = HardwareStatusInstance.getInstance()

                Logging.logEvent("Debug", "Status Update",
                                 {"message": "Starting Safety Checker Thread",
                                  "level": 3})
                # stop when the program ends
                while True:
                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "Running Safety Checker Thread",
                                      "level": 4})

                    # print("Number of Threads: {}".format(threading.active_count()))
                    # for t in threading.enumerate():
                    #     print("Thread: {}".format(t.name))

                    tempErrorDict = {
                        "System Alarm: High Temperature": False,
                        "Product Saver Alarm: High Temperature": False,
                        "Product Saver Alarm: Low Temperature": False,
                        "Human Touch Alarm: High Temperature": False,
                        "Human Touch Alarm: Low Temperature": False,
                        "Pressure Loss In Profile": False,
                        "Thermocouple Disconnected": False,
                        "Power Loss": False
                    }
                    TCs = hardwareStatusInstance.thermocouples.ValidTCs

                    if power_failure():
                        error_log = {
                            "time": str(datetime.now()),
                                "event": "Power Loss",
                                "item": "Unknown",
                                "itemID": 0,
                                "details": "There has been a connection or power failure, check status page for details.",
                                "actions": ["Log Event"]
                        }
                        self.logEvent(error_log)
                        if ProfileInstance.getInstance().activeProfile:
                            ProfileInstance.getInstance().activeProfile = False
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

                    for tc in hardwareStatusInstance.thermocouples.recently_disconnected:
                        error_log = {
                            "time": str(datetime.now()),
                                "event": "Thermocouple {} Disconnected".format(tc.Thermocouple),
                                "item": "Thermocouple",
                                "itemID": tc.Thermocouple,
                                "details": "Thermocouple(s) lost: {}".format(list(tc.Thermocouple for tc in hardwareStatusInstance.thermocouples.recently_disconnected)),
                                "actions": ["Log Event"]
                        }
                        print("TC {} has been removed".format(tc.Thermocouple))
                        print("the list length: {}".format(len(hardwareStatusInstance.thermocouples.recently_disconnected)))
                        self.logEvent(error_log)
                        print("After Event log")
                        hardwareStatusInstance.thermocouples.recently_disconnected.remove(tc)

                    overheated_tc = False
                    for tc in TCs:
                        # if there are any TC's higher than max temp
                        if tc.temp > MAX_OPERATING_TEMP:
                            overheated_tc = True
                            errorDetail = "TC # {} is above MAX_OPERATING_TEMP ({}). Currently {}c".format(
                                tc.Thermocouple, MAX_OPERATING_TEMP, tc.temp)
                            error = {
                                "time": str(datetime.now()),
                                "event": "System Alarm: High Temperature",
                                "item": "Thermocouple",
                                "itemID": tc.Thermocouple,
                                "details": errorDetail,
                                "actions": ["Turned off heater", "Log Event"]
                            }
                            self.logEvent(error)
                            tempErrorDict[error['event']] = True

                            d_out = HardwareStatusInstance.getInstance().pc_104.digital_out
                            ProfileInstance.getInstance().activeProfile = False
                            Logging.debugPrint(1, "ERROR Heat was above max operating temperature ({})".format(tc.temp))
                            vacuum = False
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

                            release_hold_thread()
                        # end of max operational test

                        if tc.userDefined:
                            # print("tc: {} zone: {}".format(tc.Thermocouple,tc.zone))
                            if tc.zone != 0:
                                if tc.temp > ProfileInstance.getInstance().zoneProfiles.getZone(tc.zone).maxHeatError:
                                    errorDetail = "TC # {} is above MAX_UUT_TEMP ({}). Currently {}c".format(
                                        tc.Thermocouple,
                                        ProfileInstance.getInstance().zoneProfiles.getZone(tc.zone).maxHeatError,
                                        tc.temp)
                                    error = {
                                        "time": str(datetime.now()),
                                        "event": "Product Saver Alarm: High Temperature",
                                        "item": "Thermocouple",
                                        "itemID": tc.Thermocouple,
                                        "details": errorDetail,
                                        "actions": ["Turned off heater", "Log Event"]
                                    }
                                    self.logEvent(error)
                                    tempErrorDict[error['event']] = True
                                # end of max user test

                                if tc.temp < ProfileInstance.getInstance().zoneProfiles.getZone(tc.zone).minHeatError:
                                    errorDetail = "TC # {} is below MIN_UUT_TEMP ({}). Currently {}c".format(
                                        tc.Thermocouple,
                                        ProfileInstance.getInstance().zoneProfiles.getZone(tc.zone).minHeatError,
                                        tc.temp)
                                    error = {
                                        "time": str(datetime.now()),
                                        "event": "Product Saver Alarm: Low Temperature",
                                        "item": "Thermocouple",
                                        "itemID": tc.Thermocouple,
                                        "details": errorDetail,
                                        "actions": ["Turned off LN flow", "Log Event"]
                                    }
                                    self.logEvent(error)
                                    tempErrorDict[error['event']] = True
                        # end of min user test
                        # end of user test

                        # Get the full list
                        OutsideThermoCouples = []
                        if tc.Thermocouple in OutsideThermoCouples:
                            if tc.temp > MAX_TOUCH_TEMP:
                                errorDetail = "TC # {} is above MAX_TOUCH_TEMP ({}). Currently {}c".format(
                                    tc.Thermocouple, MAX_TOUCH_TEMP, tc.temp)
                                error = {
                                    "time": str(datetime.now()),
                                    "event": "Human Touch Alarm: High Temperature",
                                    "item": "Thermocouple",
                                    "itemID": tc.Thermocouple,
                                    "details": errorDetail,
                                    "actions": ["Log Event"]
                                }
                                self.logEvent(error)
                                tempErrorDict[error['event']] = True
                            # end of max touch test

                            if tc.temp < MIN_TOUCH_TEMP:
                                errorDetail = "TC # {} is below MIN_TOUCH_TEMP ({}). Currently {}c".format(
                                    tc.Thermocouple, MIN_TOUCH_TEMP, tc.temp)
                                error = {
                                    "time": str(datetime.now()),
                                    "event": "Human Touch Alarm: Low Temperature",
                                    "item": "Thermocouple",
                                    "itemID": tc.Thermocouple,
                                    "details": errorDetail,
                                    "actions": ["Log Event"]
                                }
                                self.logEvent(error)
                                tempErrorDict[error['event']] = True
                            # end of min touch test
                        # if of outside thermaltest
                    # End of TC for loop
                    HardwareStatusInstance.getInstance().overheated_tc = overheated_tc

                    for errorType in self.errorDict:
                        # for every type of error
                        if self.errorDict[errorType] and not tempErrorDict[errorType]:
                            # It was true and now is not, log it.

                            # make a event log
                            errorLog = {
                                "time": str(datetime.now()),
                                "event": errorType,
                                "item": "Thermocouple",
                                "itemID": tc.Thermocouple,
                                "details": "The current event has ended",
                                "actions": ["Log Event"]
                            }
                            self.logEvent(errorLog)

                    self.errorDict = tempErrorDict

                    # Logging if you've entered operational vacuum, and then left it
                    # TODO: operational_vacuum can't be updated if there isn't an active profile...this needs to change
                    if HardwareStatusInstance.getInstance().operational_vacuum:
                        vacuum = True

                    if os.name == "posix":
                        userName = os.environ['LOGNAME']
                    else:
                        userName = "user"
                    if "root" in userName:
                        if vacuum and HardwareStatusInstance.getInstance().pfeiffer_gauges.get_chamber_pressure() > 1e-4:
                            d_out = HardwareStatusInstance.getInstance().pc_104.digital_out
                            ProfileInstance.getInstance().activeProfile = False
                            Logging.debugPrint(1, "ERROR Pressure is above 10^-4. ({})".format(
                                HardwareStatusInstance.getInstance().pfeiffer_gauges.get_chamber_pressure()))
                            vacuum = False
                            # TODO: Send Error
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

                            release_hold_thread()

                        # end if vacuum in bad condintion
                    # end if root
                    time.sleep(self.SLEEP_TIME)
            # end of inner while true loop
            except Exception as e:
                Logging.debugPrint(1, "Error in Safety Checker: {}".format(str(e)))
                raise e
                if Logging.debug:
                    raise e
                time.sleep(self.SLEEP_TIME)
        # end of try/except

    # end of outer while true
    # end of run()

    def logEvent(self, error):
        errorInList = False
        if self.errorList:
            for tempError in self.errorList:
                if error["event"] == tempError["event"]:
                    if error["item"] == tempError["item"]:
                        if error['itemID'] == tempError['itemID']:
                            errorInList = True
        if not errorInList:
            # debugPrint(1, error["details"])
            self.errorList.append(error)
        # print(self.errorList)

        Logging.debugPrint(4, "Running Safety Checker Thread")
        # Not sure what to do with this
        if not self.errorDict.get(error["event"],False):
            # The error has not been on, and is now on
            # Log SQL stuff
            pass
