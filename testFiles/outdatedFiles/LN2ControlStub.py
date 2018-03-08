from threading import Thread
import os
import time


from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance

from Logging.Logging import Logging
# used for testing
import random

class LN2ControlStub(Thread):
    """
    docstring for LN2ControlStub
    """
    __instance = None

    def __init__(self, ThreadCollection):
        if LN2ControlStub.__instance != None: # correct to carry over from TCU.py?
            raise Exception("This class is a singleton!")
        else:
            Logging.logEvent("Debug","Status Update", 
            {"message": "LN2: Creating LN2ControlStub",
             "level":2})
            LN2ControlStub.__instance = self
            self.ThreadCollection = ThreadCollection
            self.hardwareStatus = HardwareStatusInstance
            self.SLEEP_TIME = 5  # will be 30 seconds
            super(LN2ControlStub, self).__init__(name="LN2ControlStub")

            self.time_since_last_sleep = time.time()

    def run(self):
        if os.name == "posix":
            user_name = os.environ['LOGNAME']
        else:
            user_name = "user"

            # While true to restart the thread if it errors out
        while True:
            # Check to make sure there is an active profile
            # and that we are sitting in an operational vacuum
            # and that all drivers and updaters are running
            a_out = self.hardwareStatus.getInstance().pc_104.analog_out
            d_out = self.hardwareStatus.getInstance().pc_104.digital_out
            a_out.update({'LN2 Shroud': 0,'LN2 Platen': 0})
            d_out.update({'LN2-S Sol': False, 'LN2-P Sol': False, })

            if "root" not in user_name:
                HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed = True

            if ProfileInstance.getInstance().active_profile and \
                    HardwareStatusInstance.getInstance().operational_vacuum and \
                    HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed:
                # try and catch anything that might go wrong
                try:
                    Logging.debugPrint(3, "LN2: Starting LN2 Control")
                    # some start up stuff here
                    ln2_max = 0.1
                    ln2_min = -0.2 
                    valve_max = 4095/2
                    time.sleep(self.SLEEP_TIME)

                    # Normal program loop
                    while ProfileInstance.getInstance().active_profile and HardwareStatusInstance.getInstance().operational_vacuum:
                        Logging.debugPrint(3, "LN2: Starting LN2 Control Loop")
                        dutycyclelist = []
                        platenDuty = None
                        for zoneStr in self.ThreadCollection.dutyCycleThread.zones:

                            zone = self.ThreadCollection.dutyCycleThread.zones[zoneStr]
                            # If a zone doesn't have a dutyCycle, they aren't running, so we can safely ignore them
                            if not zone.duty_cycle:
                                continue
                            #print("current zone_str: {}".format(zoneStr))
                            if zoneStr != "zone9":
                                dutycyclelist.append(zone.duty_cycle)
                            else:
                                platenDuty = zone.duty_cycle
                        Logging.debugPrint(3, "LN2: dutycyclelist: {}".format(dutycyclelist))
                        Logging.debugPrint(3, "LN2: planetDuty: {}".format(platenDuty))
                        Logging.debugPrint(3, "LN2: found duty Cycle list")
                        if dutycyclelist:
                            dutycyclemin = min(dutycyclelist)
                            Logging.debugPrint(3,"LN2: Min Duty Cycle: {}".format(dutycyclemin))

                            if dutycyclemin < ln2_max:
                                # throw safety up
                                d_out.update({'LN2-S Sol': True})
                                # 2500 is the point the valve should be opened too
                                #a_out.update({'LN2 Shroud': 4095, 'LN2 Platen': 4095})
                                PercentVavleopen = valve_max*(dutycyclemin-ln2_max)/(ln2_min-ln2_max)
                                if dutycyclemin < ln2_min:
                                    PercentVavleopen = valve_max
                                a_out.update({'LN2 Shroud': PercentVavleopen})
                                Logging.debugPrint(3,"LN2: The Shroud LN2 should be on {}".format(PercentVavleopen))
                            else:
                                Logging.debugPrint(3,"LN2: The Shroud LN2 should be off")
                                d_out.update({'LN2-S Sol': False})
                                a_out.update({'LN2 Shroud': 0})
                            # end of if/else
                        # end of if DutycycleList
                        if platenDuty:
                            if platenDuty < ln2_max:
                                # throw safety up
                                d_out.update({'LN2-P Sol': True})
                                # 2500 is the point the valve should be opened too
                                #a_out.update({'LN2 Shroud': 4095, 'LN2 Platen': 4095})
                                PercentVavleopen = valve_max*(platenDuty-ln2_max)/(ln2_min-ln2_max)
                                if platenDuty < ln2_min:
                                    PercentVavleopen = valve_max
                                a_out.update({'LN2 Platen': PercentVavleopen})
                                Logging.debugPrint(3,"LN2: The Platen LN2 should be on {}".format(PercentVavleopen))
                            else:
                                Logging.debugPrint(3,"LN2: The Platen LN2 should be off")
                                # What's the difference between this and...
                                d_out.update({'LN2-P Sol': False, })
                                a_out.update({'LN2 Platen': 0})
                        # print("Thread: {} \tcurrent loop time: {}".format(self.name,
                        #                                                   time.time() - self.time_since_last_sleep))
                        time.sleep(self.SLEEP_TIME)
                        # self.time_since_last_sleep = time.time()
                    # end of Inner While True
                except Exception as e:
                    Logging.debugPrint(1, "Error in run, LN2 Control Stub: {}".format(str(e)))
                    if Logging.debug:
                        raise e
                # end of try catch
            else:
                Logging.debugPrint(3,"LN2: AP: {}, Vacuum: {}, Door {}".format(
                    ProfileInstance.getInstance().active_profile,
                    HardwareStatusInstance.getInstance().operational_vacuum,
                    HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed
                ))
            # end of If should be running
            time.sleep(self.SLEEP_TIME)
        # end of outter while true
    # end of run()
# end of class
