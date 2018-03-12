from threading import Thread
import time
import sys
import os

from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance

from Logging.Logging import Logging


def regen_cryopump_ending(step):
    hw = HardwareStatusInstance.getInstance()
    if step.startswith('C:') or step.startswith('D:') or step.startswith('E:'):
        hw.shi_compressor_cmds.append('off')
    if hw.shi_cryopump.get_mcc_status('PumpOn?') or step.startswith('M:'):
        hw.shi_compressor_cmds.append('on')


def wait_for_hardware():
    hw = HardwareStatusInstance.getInstance()
    pi = ProfileInstance.getInstance()
    ready = True
    ready &= hw.pc_104.digital_in.getVal('CryoP_GV_Open') is not None
    ready &= hw.pc_104.digital_in.getVal('CryoP_GV_Closed') is not None
    ready &= hw.pc_104.digital_in.getVal('RoughP_Powered') is not None
    ready &= hw.pc_104.digital_in.getVal('RoughP_On_Sw') is not None
    ready &= hw.pc_104.digital_in.getVal('Chamber Closed') is not None
    ready &= hw.pfeiffer_gauges.get_roughpump_pressure() is not None
    ready &= hw.pfeiffer_gauges.get_chamber_pressure() is not None
    ready &= hw.pfeiffer_gauges.get_cryopump_pressure() is not None
    ready &= hw.shi_cryopump.is_cryopump_cold() is not None
    ready &= hw.shi_cryopump.is_regen_active() is not None
    ready &= hw.shi_cryopump.cryopump_needs_regen() is not None
    ready &= hw.shi_cryopump.cryopump_wants_regen_soon() is not None
    ready &= hw.shi_cryopump.get_mcc_status('Tc Pressure') is not None
    ready &= hw.shi_cryopump.get_mcc_params('Tc Pressure State') is not None
    ready &= hw.shi_cryopump.get_mcc_status('Stage 1 Temp') is not None
    ready &= hw.shi_cryopump.get_mcc_status('Stage 2 Temp') is not None
    ready &= hw.shi_cryopump.get_compressor('Helium Discharge Temperature') is not None
    ready &= hw.shi_cryopump.get_compressor('Water Outlet Temperature') is not None
    ready &= hw.shi_cryopump.get_compressor('System ON') is not None
    ready &= pi.vacuum_wanted is not None
    return ready


class VacuumControlStub(Thread):
    '''
    This class contains the main inteligences for getting and keeping the test chaber under vacuum,
    '''

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):

        Logging.logEvent("Debug", "Status Update",
                         {"message": "Creating VacuumControlStub:",
                          "level": 3})

        Thread.__init__(self, group=group, target=target, name="VacuumControlStub")
        self.args = args
        self.kwargs = kwargs

        # self.profile = ProfileInstance.getInstance()
        # self.hw = HardwareStatusInstance.getInstance()
        self.state = None
        self.pres_opVac = 9e-5
        self.pres_atm = 100
        self.pres_cryoP_Prime = 40e-3
        self.pres_chamber_crossover = 25e-3
        self.pres_chamber_max_crossover = 40e-3
        self.pres_min_roughing = 9e-4
        self.pres_ruffon = 70
        self.cryoPumpPressure = None
        self.chamberPressure = None
        self.roughPumpPressure = None

        self.update_period = 1

        self.time_since_last_sleep = time.time()

    def run(self):
        pi = ProfileInstance.getInstance()
        hw = HardwareStatusInstance.getInstance()
        # While true to restart the thread if it errors out
        while True:
            # This has no startup, but should wait until all drivers and updaters are running
            Logging.logEvent("Debug", "Status Update",
                             {"message": "VCS: Starting VacuumControlStub",
                              "level": 2})
            try:
                while not wait_for_hardware(): # Wait for hardware drivers to read sensors.
                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "VCS: VacuumControlStub waiting for hardware to read the sensors.",
                                      "level": 4})
                    time.sleep(1)
                if not hw.pc_104.digital_in.chamber_closed:
                    Logging.logEvent("Event", "Vacuum State",
                                     {"message": "Doors must be closed before Automated Vacuum Control can begin."
                                                 "".format(self.state),
                                      "ProfileInstance": pi})

                while not hw.pc_104.digital_in.chamber_closed:
                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "VCS: Waiting for doors to be closed",
                                      "level": 4})
                    time.sleep(1)
                self.cryoPumpPressure = hw.pfeiffer_gauges.get_cryopump_pressure()
                self.chamberPressure = hw.pfeiffer_gauges.get_chamber_pressure()
                self.roughPumpPressure = hw.pfeiffer_gauges.get_roughpump_pressure()

                self.state = self.determine_current_vacuum_state()
                if hw.shi_cryopump.is_regen_active():
                    Logging.logEvent("Event", "Vacuum State",
                                     {"message": "Starting in Vacuum State: '{}' with a Cryopump Regeneration Active."
                                                 "".format(self.state),
                                      "ProfileInstance": pi})
                else:
                    Logging.logEvent("Event", "Vacuum State",
                                     {"message": "Starting in Vacuum State: '{}'".format(self.state),
                                      "ProfileInstance": ProfileInstance.getInstance()})

                while True:
                    # With an active profile, we start putting the system under pressure

                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "VCS: Running Vacuum Control Stub",
                                      "level": 5})

                    # Reading of pressure gauges
                    self.cryoPumpPressure = hw.pfeiffer_gauges.get_cryopump_pressure()
                    self.chamberPressure = hw.pfeiffer_gauges.get_chamber_pressure()
                    self.roughPumpPressure = hw.pfeiffer_gauges.get_roughpump_pressure()

                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "VCS: Current chamber pressure: {}".format(self.chamberPressure),
                                      "level": 4})

                    old_state = self.state
                    {
                        'Chamber: Atm; CryoP: Vac': self.state_00,
                        'Chamber: Atm; CryoP: Atm': self.state_01,
                        'PullingVac: Start': self.state_02,
                        'PullingVac: RoughingCryoP': self.state_03,
                        'PullingVac: CryoCool; Rough Chamber': self.state_04,
                        'PullingVac: M CryoCool; Rough Chamber': self.state_05,
                        'PullingVac: Cryo Pumping; Cross Over': self.state_06,
                        'PullingVac: Cryo Pumping Chamber': self.state_07,
                        'Operational Vacuum: Cryo Pumping': self.state_08,
                        'Operational Vacuum': self.state_09,
                        'Non-Operational Vacuum': self.state_10,
                    }[self.state]()

                    if hw.shi_cryopump.is_regen_active():
                        self.regen_cryopump()

                    hw.vacuum_state = self.state

                    if "Operational Vacuum" in self.state and "Non-Operational Vacuum" not in self.state:
                        hw.operational_vacuum = True

                        # If we wanted to get a vacuum, and have gotten one, mark it as so.
                        if ProfileInstance.getInstance().vacuum_wanted:
                            ProfileInstance.getInstance().vacuum_obtained = True

                    else:
                        hw.operational_vacuum = False

                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "VCS: Current chamber state: {}".format(self.state),
                                      "level": 4})

                    if old_state != self.state:
                        Logging.logEvent("Event", "Vacuum State",
                                         {"message": "New Vacuum State: '{}'".format(self.state),
                                          "ProfileInstance": pi})

                    # sleep until the next time around
                    time.sleep(self.update_period)

                # end of inner while True
            except Exception as e:

                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print("Error: {} in file {}:{}".format(exc_type, fname, exc_tb.tb_lineno))

                ProfileInstance.getInstance().active_profile = False
                Logging.debug_print(1, "VCS: Error in check run, vacuum Control Stub: {}".format(str(e)))
                time.sleep(1)
                if Logging.debug:
                    raise e
            # end of try, catch
        # end of outer while true

    def regen_cryopump(self):
        hw = HardwareStatusInstance.getInstance()
        hw.pc_104.digital_out.update({'RoughP GateValve': False})
        step = hw.shi_cryopump.get_mcc_status('Regen Step')

        if hw.shi_cryopump.get_mcc_status('Roughing Interlock: Roughing Needed'):
            # If the roughing pump is running, not just on.
            if hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
                if self.roughPumpPressure < self.cryoPumpPressure:
                    hw.shi_mcc_cmds.append(['Clear_RoughingInterlock'])
                    Logging.logEvent("Event", "Cryopump Regeneration",
                                     {"message": "Clearing Roughing Interlock.".format(self.state),
                                      "ProfileInstance": ProfileInstance.getInstance()})
            else:
                # If the Roughing pump is on, make it start, if not, turn it on.
                if hw.pc_104.digital_in.getVal('RoughP_Powered'):
                    hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
                    hw.pc_104.digital_out.update({'RoughP Start': True})
                else:
                    hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
                    hw.pc_104.digital_out.update({'RoughP PurgeGass': True})

        # If the cryopump doesn't need the roughing pump, turn it off
        elif (not hw.shi_cryopump.get_mcc_status('Roughing Valve State')) and \
                (not step.startswith('T:')) and (not step.startswith('J:')) and \
                (not step.startswith('H:')):
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
        regen_cryopump_ending(step)

    # end of run()

    def state_00(self):  # Chamber: Atm; CryoP: Vac
        """
        Used Variables:

        cryoPumpPressure
        chamberPressure
        pres_atm
        pres_ruffon
        vacuum_wanted
        hw.shi_cryopump.is_regen_active()
        pres_cryoP_Prime
        hw.pc_104.digital_in.getVal('RoughP_Powered')
        hw.pc_104.digital_in.getVal('RoughP_On_Sw')

        :return:
        """
        hw = HardwareStatusInstance.getInstance()
        pi = ProfileInstance.getInstance()
        if (self.cryoPumpPressure > self.pres_atm) and (self.chamberPressure > self.pres_atm):
            self.state = 'Chamber: Atm; CryoP: Atm'

        if self.chamberPressure < self.pres_ruffon:
            self.state = 'Non-Operational Vacuum'

        if not pi.vacuum_wanted or hw.shi_cryopump.is_regen_active():
            return

        if self.cryoPumpPressure < self.pres_cryoP_Prime:
            hw.shi_mcc_cmds.append(['Close_PurgeValve'])
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])
            hw.shi_compressor_cmds.append('on')
            hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
            hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
            hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
            self.state = 'PullingVac: CryoCool; Rough Chamber'
            return

        if not hw.pc_104.digital_in.getVal('RoughP_Powered'):
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Applying power to the Ruffing Pump")
            return

        if not hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Switching on the Ruffing Pump")
        else:
            self.state = 'PullingVac: Start'

    def state_01(self):  # Chamber: Atm; CryoP: Atm
        """

        cryoPumpPressure
        chamberPressure
        pres_atm
        pres_ruffon
        vacuum_wanted
        hw.shi_cryopump.is_regen_active()
        hw.pc_104.digital_in.getVal('RoughP_Powered')
        hw.pc_104.digital_in.getVal('RoughP_On_Sw')
        :return:
        """
        pi = ProfileInstance.getInstance()
        hw = HardwareStatusInstance.getInstance()
        if self.cryoPumpPressure < self.pres_ruffon:
            self.state = 'Chamber: Atm; CryoP: Vac'
        if self.chamberPressure < self.pres_ruffon:
            self.state = 'Non-Operational Vacuum'

        if not pi.vacuum_wanted or hw.shi_cryopump.is_regen_active():
            return

        if not hw.pc_104.digital_in.getVal('RoughP_Powered'):
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Applying power to the Ruffing Pump")
            return

        if not hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Switching on the Ruffing Pump")
        else:
            self.state = 'PullingVac: Start'

    def state_02(self):  # PullingVac: Start
        """
        pi.vacuum_wanted
        hw.shi_cryopump.is_regen_active()
        roughPumpPressure
        pres_ruffon
        :return:
        """
        pi = ProfileInstance.getInstance()
        hw = HardwareStatusInstance.getInstance()
        if not pi.vacuum_wanted or hw.shi_cryopump.is_regen_active():
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
            self.state = 'Non-Operational Vacuum'
            return

        # If the roughing pump pressure is less 70 torr, start roughing out the cryopump
        if self.roughPumpPressure < self.pres_ruffon:
            hw.shi_mcc_cmds.append(['Close_PurgeValve'])
            hw.shi_mcc_cmds.append(['Open_RoughingValve'])
            self.state = 'PullingVac: RoughingCryoP'

    def state_03(self):  # PullingVac: RoughingCryoP
        pi = ProfileInstance.getInstance()
        hw = HardwareStatusInstance.getInstance()
        if not pi.vacuum_wanted or hw.shi_cryopump.is_regen_active():
            # If we aren't pumping the chamber, close the roughing pump, and set set non-operational vacuum
            if not hw.shi_cryopump.get_mcc_status('Roughing Valve State') and \
                   not hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
                hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
                self.state = 'Non-Operational Vacuum'
            return

        # When the cryopump gets below pressure, start the cryopump
        if self.cryoPumpPressure < self.pres_cryoP_Prime:
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])
            hw.shi_compressor_cmds.append('on')
            hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
            hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
            hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
            self.state = 'PullingVac: CryoCool; Rough Chamber'
            return

        # If the roughing pump is pumping, open the roughing valve
        if hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
            hw.shi_mcc_cmds.append(['Open_RoughingValve'])
        else:
            # Else, turn off the close the roughing valve
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])
            self.state = 'Chamber: Atm; CryoP: Atm'

    def state_04(self):  # PullingVac: CryoCool; Rough Chamber
        pi = ProfileInstance.getInstance()
        hw = HardwareStatusInstance.getInstance()
        if not pi.vacuum_wanted or hw.shi_cryopump.is_regen_active():
            if not hw.shi_cryopump.get_mcc_status('PumpOn?'):
                self.state = 'PullingVac: M CryoCool; Rough Chamber'
            return

        if hw.shi_cryopump.is_cryopump_ready() and \
                (self.chamberPressure < self.pres_chamber_crossover):
            self.state = 'PullingVac: Cryo Pumping; Cross Over'
            return

        if self.chamberPressure < self.pres_min_roughing:
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            return

        if not hw.pc_104.digital_in.getVal('RoughP_Powered'):
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Applying power to the Ruffing Pump")
            return

        if not hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Switching on the Ruffing Pump")
            return

        if (self.chamberPressure > self.roughPumpPressure) and \
                (not hw.shi_cryopump.get_mcc_status('Roughing Valve State')):
            hw.pc_104.digital_out.update({'RoughP GateValve': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Ruffing the Chamber")
        else:
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])

    def state_05(self):  # PullingVac: M CryoCool; Rough Chamber
        pi = ProfileInstance.getInstance()
        hw = HardwareStatusInstance.getInstance()
        if not pi.vacuum_wanted or hw.shi_cryopump.is_regen_active():
            if (not hw.shi_cryopump.get_mcc_status('Roughing Valve State')) and \
                    (not hw.pc_104.digital_in.getVal('RoughP_On_Sw')):
                hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
                self.state = 'Non-Operational Vacuum'
            return

        if not (hw.shi_cryopump.get_mcc_status('PumpOn?')):
            return

        if hw.shi_cryopump.is_cryopump_ready() and \
                (self.chamberPressure < self.pres_chamber_crossover):
            self.state = 'PullingVac: Cryo Pumping; Cross Over'
        else:
            self.state = 'PullingVac: CryoCool; Rough Chamber'

    def state_06(self):  # PullingVac: Cryo Pumping; Cross Over
        hw = HardwareStatusInstance.getInstance()
        hw.pc_104.digital_out.update({'RoughP GateValve': False})
        # wait here until the valve is closed
        # TODO Replace Sleep with a check of the Gate valve switches

        Logging.logEvent("Event", "Vacuum State",
                         {"message": "Notice: Close the Front/Back door guard vacuum valve at this time.",
                          "ProfileInstance": ProfileInstance.getInstance()})
        time.sleep(10)
        # Open the cryopump gate valve
        hw.pc_104.digital_out.update({'CryoP GateValve': True})
        if hw.pc_104.digital_in.getVal('CryoP_GV_Open'):
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
            self.state = 'PullingVac: Cryo Pumping Chamber'

    def state_07(self):  # PullingVac: Cryo Pumping Chamber
        hw = HardwareStatusInstance.getInstance()
        if self.chamberPressure < (self.pres_opVac * 0.8):
            self.state = 'Operational Vacuum'
        if not hw.shi_cryopump.get_mcc_status('PumpOn?'):
            self.state = 'Non-Operational Vacuum'

    def state_08(self):  # Operational Vacuum: Cryo Pumping
        hw = HardwareStatusInstance.getInstance()
        if self.chamberPressure > self.pres_opVac:
            self.state = 'Non-Operational Vacuum'
            return

        if hw.pc_104.digital_in.getVal('CryoP_GV_Closed') or \
                (not hw.shi_cryopump.get_mcc_status('PumpOn?')):
            self.state = 'Operational Vacuum'
            return

        if hw.shi_cryopump.is_regen_active() or \
                (not hw.shi_cryopump.is_cryopump_cold()):
            self.state = 'Operational Vacuum'
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            if not hw.pc_104.digital_in.getVal('CryoP_GV_Closed'):
                time.sleep(4)

    def state_09(self):  # Operational Vacuum
        hw = HardwareStatusInstance.getInstance()
        pi = ProfileInstance.getInstance()
        if self.chamberPressure > self.pres_opVac:
            self.state = 'Non-Operational Vacuum'
            return
        if hw.shi_cryopump.get_mcc_status('PumpOn?') and \
                (not hw.shi_cryopump.cryopump_needs_regen()) and \
                (self.cryoPumpPressure < self.chamberPressure) and \
                (not hw.shi_cryopump.is_regen_active()):

            if hw.pc_104.digital_in.getVal('CryoP_GV_Closed') and not pi.vacuum_wanted:
                hw.pc_104.digital_out.update({'CryoP GateValve': False})
                return

            if hw.pc_104.digital_in.getVal('RoughP_Powered'):
                hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
                hw.pc_104.digital_out.update({'RoughP PurgeGass': False})

            hw.pc_104.digital_out.update({'CryoP GateValve': True})
            self.state = 'Operational Vacuum: Cryo Pumping'
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Switching from OV to OV:CP")
            time.sleep(4)
            return

        if not (pi.vacuum_wanted and
                (not hw.shi_cryopump.is_regen_active()) and
                (not hw.shi_cryopump.get_mcc_status('PumpOn?'))):
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            return

        if self.cryoPumpPressure < self.pres_cryoP_Prime:
            hw.shi_mcc_cmds.append(['Close_PurgeValve'])
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])
            hw.shi_compressor_cmds.append('on')
            hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
            hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
            hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
            time.sleep(5)
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Starting the Cryo Pump; Roughing Pump Off.")
            return

        if not (hw.pc_104.digital_in.getVal('RoughP_Powered')):
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Applying power to the Ruffing Pump")
            return

        if hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
            hw.shi_mcc_cmds.append(['Close_PurgeValve'])
            hw.shi_mcc_cmds.append(['Open_RoughingValve'])
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Ruffing the Cryo Pump")
        else:
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Switching on the Ruffing Pump")

    def state_10(self):  # Non-Operational Vacuum
        hw = HardwareStatusInstance.getInstance()
        pi = ProfileInstance.getInstance()
        if self.chamberPressure < (self.pres_opVac * 0.8):
            self.state = 'Operational Vacuum'
        if self.chamberPressure > self.pres_atm:
            if self.cryoPumpPressure < self.pres_ruffon:
                self.state = 'Chamber: Atm; CryoP: Vac'
            else:
                self.state = 'Chamber: Atm; CryoP: Atm'
        if not (pi.vacuum_wanted and (not hw.shi_cryopump.is_regen_active())):
            return

        if self.cryoPumpPressure < self.pres_cryoP_Prime:
            hw.shi_mcc_cmds.append(['Close_PurgeValve'])
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])
            hw.shi_compressor_cmds.append('on')
            hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
            hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
            hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
            self.state = 'PullingVac: CryoCool; Rough Chamber'
            return

        if not hw.pc_104.digital_in.getVal('RoughP_Powered'):
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Applying power to the Ruffing Pump")
            return

        if not hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Switching on the Ruffing Pump")
        else:
            self.state = 'PullingVac: Start'

    def determine_current_vacuum_state(self):
        hw = HardwareStatusInstance.getInstance()
        if self.chamberPressure < self.pres_opVac:  ##
            return 'Operational Vacuum'

        if self.chamberPressure < self.pres_chamber_crossover and hw.shi_cryopump.get_mcc_status('PumpOn?'):
            if hw.shi_cryopump.is_cryopump_cold() and (not hw.pc_104.digital_in.getVal('CryoP_GV_Closed')):
                hw.pc_104.digital_out.update({'CryoP GateValve': True})
                return 'PullingVac: Cryo Pumping Chamber'
            else:
                hw.pc_104.digital_out.update({'CryoP GateValve': False})
                return 'PullingVac: CryoCool; Rough Chamber'

        if not (hw.pc_104.digital_in.getVal('RoughP_On_Sw')):
            return 'Non-Operational Vacuum'

        if hw.shi_cryopump.get_mcc_status('Roughing Valve State'):
            hw.pc_104.digital_out.update({'RoughP GateValve': False})
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            if not hw.shi_cryopump.is_regen_active():
                return 'PullingVac: RoughingCryoP'

            return 'Non-Operational Vacuum'

        if not (hw.pc_104.digital_out.getVal('RoughP GateValve')):
            return 'Non-Operational Vacuum'

        if hw.shi_cryopump.get_mcc_status('PumpOn?'):
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            return 'PullingVac: CryoCool; Rough Chamber'
        else:
            return 'PullingVac: M CryoCool; Rough Chamber'
