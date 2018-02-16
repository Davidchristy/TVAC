import os
import sys
import time
from datetime import datetime
import math
from threading import Thread

from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance
from Hardware_Drivers.Keysight_34980A_TCs import Keysight_34980A_TCs
from Logging.Logging import Logging




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

class ThermoCoupleUpdater(Thread):
    """
    This is a simply thread class that connects the hardware (Keysight_34980A_TCs)
    With our software interface (hwStatus.Thermocouples).

    This is one way communication, it doesn't write anything to the Keysight_34980A_TCs, only reads.

    If there are errors in the thread, they will be caught, processed, and the thread restarted
    """
    __instance = None



    def __init__(self, parent):
        if ThermoCoupleUpdater.__instance:
            raise Exception("This class is a singleton!")
        else:
            Logging.logEvent("Debug","Status Update",
            {"message": "Creating ThermoCoupleUpdater",
             "level":2})
            ThermoCoupleUpdater.__instance = self
            self.parent = parent
            self.hardwareStatusInstance = HardwareStatusInstance
            self.SLEEP_TIME = 5
            super(ThermoCoupleUpdater, self).__init__(name="ThermoCoupleUpdater")
            self.number_continuous_errors = 0
            self.MAX_NUMBER_OF_ERRORS = 2

    def run(self):
        """
        :rtype: None

        This is an infinite loop that runs at all times while the program runs.
        If it errors out for whatever reason it will catch the error and restart the thread.

        It's job to to read the hardware Thermocouple and update the hw status object with updated data.

        # TODO: Make sure the program halts if it can't read the data.
        """

        # This makes the loop constant, even after failing, it will just restart the thread info
        while True:
            # This try is there to catch any errors that might show up
            try:
                # Thread "Start up" stuff goes here
                hw_status, tharsis, user_name = self.start_procedure()

                while True:
                    # TODO: I don't think "record data" would work here.
                    if "root" in user_name:
                        Logging.logEvent("Debug","Status Update",
                        {"message": "Pulling live data for TC",
                         "level":4})
                        tc_values = tharsis.getTC_Values()
                    else:
                        # We are in a test environment, so give it fake data
                        Logging.logEvent("Debug","Status Update",
                        {"message": "Generating test data for TC",
                         "level":4})

                        f_tcs = open("../virtualized/hw-files/thermocouples.txt", "r")
                        tcs = []
                        for line in f_tcs:
                            try:
                                tcs.append(float(line.strip()))
                            except ValueError as e:
                                pass
                        f_tcs.close()

                        tc_values = {
                            'time': datetime.now(),
                            'tcList': [
                                # {'Thermocouple': 11,'working':True, 'temp': hw_status.thermocouples.getTC(11).getTemp() + current_pid + 0},
                            ]
                        }
                        for i, tc_temp in enumerate(tcs):
                            if (tc_temp > 8) and (tc_temp < 2000):
                                tc_working = True
                            else:
                                tc_working = False
                                tc_temp = float('NaN')
                            tc_values['tcList'].append(
                                {'Thermocouple':i+1,
                                 'working':tc_working,
                                 'temp':tc_temp}
                            )

                    '''
                    TCs is a list of dictionaries ordered like this....
                    {
                    'Thermocouple': tc_num,
                    'time': tc_time_offset,
                    'temp': tc_tempK,
                    'working': tc_working,
                    'alarm': tc_alarm
                    }
                    '''
                    if ProfileInstance.getInstance().record_data:
                        log_live_temperature_data({"message": "Current TC reading",
                             "time":    tc_values['time'],
                             "tcList":  tc_values['tcList'],
                             "profileUUID": ProfileInstance.getInstance().zoneProfiles.profileUUID,
                             "ProfileInstance": ProfileInstance.getInstance()})

                    Logging.logEvent("Debug","Data Dump",
                                     {"message": "Current TC reading",
                         "level":4,
                         "dict":tc_values['tcList']})

                    hw_status.thermocouples.update(tc_values)


                    hw_status.thermocouple_power = True
                    self.number_continuous_errors = 0

                    time.sleep(self.SLEEP_TIME)

            except Exception as e:

                # Instead of False here, check to see how much time has passed since the first failer
                # if more than x time (3*SLEEP_TIME)? has has passed with constasnt failer
                # Acutally through error.
                self.number_continuous_errors += 1
                if self.number_continuous_errors >= self.MAX_NUMBER_OF_ERRORS:
                    HardwareStatusInstance.getInstance().thermocouple_power = False

                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                Logging.logEvent("Error","Hardware Interface Thread",
                                 {"type": exc_type,
                                  "filename": fname,
                                  "line": exc_tb.tb_lineno,
                                  "thread": "ThermoCoupleUpdater",
                                  "ProfileInstance": ProfileInstance.getInstance()
                                  })
                Logging.logEvent("Debug","Status Update",
                                 {"message": "There was a {} error in ThermoCoupleUpdater. File: {}:{}".format(exc_type,fname,exc_tb.tb_lineno),
                                  "level":1})
                if Logging.debug:
                    raise e
                # If you want to cleanly close things, do it here
                time.sleep(self.SLEEP_TIME)
                # end of try/except
            # end of running check
        # end of while True

    def start_procedure(self):
        Logging.logEvent("Debug", "Status Update",
                         {"message": "Starting ThermoCoupleUpdater",
                          "level": 2})
        ip_addr_34980a = '192.168.99.3'
        # channel__list = "(@1001:1020,2036:2040,3001:3040)"
        channel_list = "(@1001:1040,2001:2040,3001:3040)"

        hw_status = self.hardwareStatusInstance.getInstance()
        if os.name == "posix":
            user_name = os.environ['LOGNAME']
        else:
            user_name = "User"
        if "root" in user_name:
            tharsis = Keysight_34980A_TCs(ip_addr_34980a, ChannelList=channel_list)
            tharsis.init_sys()
        else:
            tharsis = None
        return hw_status, tharsis, user_name
    # end of run()
