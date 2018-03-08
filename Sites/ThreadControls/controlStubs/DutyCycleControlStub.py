from threading import Thread
import time, datetime

from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance
from Logging.Logging import Logging
from ThreadControls.controlStubs.HelperFuctions.dutyCycleFunctions import check_active_duty_cycle, \
    ending_active_profile, \
    active_profile_setup, duty_cycle_update, check_hold, ln2_update
from ThreadControls.SafetyCheckHelperFunctions import enter_safe_mode, log_event

def find_lowest_shroud_duty_cycle(pi):
    duty_cycle_list = []
    for zone in pi.zone_dict:
        zone = pi.zone_dict[zone]
        if zone.active_zone_profile and zone.duty_cycle and zone.zone != 9:
            duty_cycle_list.append(zone.duty_cycle)
    if len(duty_cycle_list) > 0:
        return min(duty_cycle_list)
    else:
        return None


class DutyCycleControlStub(Thread):
    """
    This class contains the main intelligences for reading the data from the system,
    and telling the lamps what to do. 

    It controls if we are in a ramp, hold, soak, or paused.
    It also generates the expected temp values at the given time 
    """

    def __init__(self, parent=None):
        Logging.logEvent("Debug","Status Update",
        {"message": "Creating DutyCycleControlStub",
         "level":2})

        Thread.__init__(self, name="DutyCycleControlStub")


    def run(self):
        # While true to restart the thread if it errors out
        pi = ProfileInstance.getInstance()
        hw = HardwareStatusInstance.getInstance()
        while True:
            if check_active_duty_cycle():
                try:
                    active_profile_setup(pi, hw)

                    while pi.active_profile and hw.operational_vacuum:
                        current_time = time.time()

                        check_hold(pi=pi)

                        # If profile aborted in active profile, leave here
                        if not pi.active_profile:
                            return

                        duty_cycle_update(pi, current_time)


                        ln2_update(pi=pi, hw=hw)

                        time.sleep(pi.update_period)
                except Exception as e:
                    error_details = "DutyCycle Error: ({})".format(e)
                    error_log = {
                        "time": str(datetime.datetime.now()),
                        "event": "Duty Cycle Error",
                        "item": "Unknown",
                        "itemID": 0,
                        "details": error_details,
                        "actions": ["Log Event"]
                    }
                    enter_safe_mode(error_details)
                    log_event(error_log, pi.error_list)
                    pi.active_profile = False

                # end of test
                ending_active_profile()
            else:
                # Sleeping so it doesn't busy wait
                time.sleep(1)
            # end of running check
        # end of outer while True
    # end of run()


