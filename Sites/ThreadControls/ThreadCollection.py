from Collections.ProfileInstance import ProfileInstance
from Logging.Logging import Logging, insert_into_sql
from ThreadControls.SafetyCheck import SafetyCheck
from ThreadControls.controlStubs.DutyCycleControlStub import DutyCycleControlStub
from ThreadControls.controlStubs.VacuumControlStub import VacuumControlStub
from ThreadControls.updaters.PfeifferGaugeUpdater import PfeifferGaugeUpdater
from ThreadControls.updaters.hardwareUpdater import HardwareUpdater
from ThreadControls.updaters.TsRegistersUpdater import TsRegistersUpdater
import Collections.ProfileHelperFunctions as ProfileHelperFunctions

class ThreadCollection:

    # noinspection PyTypeChecker
    def __init__(self):
        pi = ProfileInstance.getInstance()
        self.dutyCycleThread = DutyCycleControlStub(parent=self)
        self.hardwareInterfaceThreadDict = self.create_hardware_interfaces(parent=self)
        self.safetyThread = SafetyCheck(parent=self)

        self.run_threads()
        result = {}
        try:
            result = ProfileHelperFunctions.return_active_profile()
            # if there is a half finished profile in the database
            active_profile_present = True
        except RuntimeError:
            active_profile_present = False
        Logging.debug_print(3, "Active Profile?: {}".format(active_profile_present))
        if active_profile_present:
            Logging.debug_print(1, "Unfinished profile found: {}".format(str(result['profile_name'])))

            # load up ram (zone collection) with info from the database and the given start time
            pi.load_profile(result['profile_name'], result['profile_Start_Time'],
                            result['thermal_Start_Time'])

            # after it's in memory, run it!
            ProfileHelperFunctions.run_profile(pi=pi, first_start = False)
        # end if no active profile
    #end of function 

    def create_hardware_interfaces(self, parent):
        # sending parent for testing, getting current profile data to zone instance
        return {
            1: TsRegistersUpdater(parent=parent),
            2: HardwareUpdater(parent=parent),
            3: PfeifferGaugeUpdater(),
            4: VacuumControlStub(),
            }


    def run_threads(self):
        # Starts all the hw threads
        try:
            for key in sorted(self.hardwareInterfaceThreadDict.keys()):
                self.hardwareInterfaceThreadDict[key].daemon = True
                self.hardwareInterfaceThreadDict[key].start()
            self.safetyThread.daemon = True
            self.safetyThread.start()
            self.dutyCycleThread.daemon = True
            self.dutyCycleThread.start()
        except Exception as e:
            Logging.debug_print(1, "Error in runThreads, ThreadCollections: {}".format(str(e)))
            if Logging.debug:
                raise e


    def holdThread(self,data=None):
        Logging.debug_print(3, "Holding Zones")
        ProfileInstance.getInstance().in_hold = True
        sql_str = "UPDATE System_Status SET in_hold=1;"
        insert_into_sql(sql_str=sql_str)
