from threading import Thread
import json
import uuid
import time
import datetime
import sys
import os

from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance

from Logging.MySql import MySQlConnect
from Logging.Logging import Logging


class VacuumControlStub(Thread):
    '''
    This class contains the main inteligences for getting and keeping the test chaber under vacuum,
    '''

    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):

        Logging.logEvent("Debug", "Status Update",
                         {"message": "Creating VacuumControlStub:",
                          "level": 3})

        Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs

        self.zoneProfiles = ProfileInstance.getInstance().zoneProfiles
        self.profile = ProfileInstance.getInstance()
        self.hw = HardwareStatusInstance.getInstance()
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

        self.updatePeriod = 1

    def run(self):
        # While true to restart the thread if it errors out
        while True:
            # This has no startup, but should wait until all drivers and updaters are running
            Logging.logEvent("Debug", "Status Update",
                             {"message": "VCS: Starting VacuumControlStub",
                              "level": 2})
            try:
                while not self.wait_for_hardware():  # Wait for hardware drivers to read sensors.
                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "VCS: VacuumControlStub waiting for hardware to read the sensors.",
                                      "level": 4})
                    time.sleep(1)
                self.cryoPumpPressure = self.hw.pfeiffer_gauges.get_cryopump_pressure()
                self.chamberPressure = self.hw.pfeiffer_gauges.get_chamber_pressure()
                self.roughPumpPressure = self.hw.pfeiffer_gauges.get_roughpump_pressure()

                self.state = self.determin_current_vacuum_state()
                if self.hw.shi_cryopump.is_regen_active():
                    Logging.logEvent("Event", "Vacuum State",
                                     {"message": "Starting in Vacuum State: '{}' with a Cryopump Regeneration Active."
                                                 "".format(self.state),
                                      "ProfileInstance": ProfileInstance.getInstance()})
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
                    self.cryoPumpPressure = self.hw.pfeiffer_gauges.get_cryopump_pressure()
                    self.chamberPressure = self.hw.pfeiffer_gauges.get_chamber_pressure()
                    self.roughPumpPressure = self.hw.pfeiffer_gauges.get_roughpump_pressure()

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

                    if self.hw.shi_cryopump.is_regen_active():
                        self.hw.pc_104.digital_out.update({'RoughP GateValve': False})
                        step = self.hw.shi_cryopump.get_mcc_status('Regen Step')
                        if self.hw.shi_cryopump.get_mcc_status('Roughing Interlock: Roughing Needed'):
                            if self.hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
                                if self.roughPumpPressure < self.cryoPumpPressure:
                                    self.hw.shi_mcc_cmds.append(['Clear_RoughingInterlock'])
                                    Logging.logEvent("Event", "Cryopump Regeneration",
                                                     {"message": "Clearing Roughing Interlock.".format(self.state),
                                                      "ProfileInstance": ProfileInstance.getInstance()})
                            else:
                                if self.hw.pc_104.digital_in.getVal('RoughP_Powered'):
                                    self.hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
                                    self.hw.pc_104.digital_out.update({'RoughP Start': True})
                                else:
                                    self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
                                    self.hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
                        elif (not self.hw.shi_cryopump.get_mcc_status('Roughing Valve State')) and \
                                (not step.startswith('T:')) and (not step.startswith('J:')) and \
                                (not step.startswith('H:')):
                            self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
                            self.hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
                        if step.startswith('C:') or step.startswith('D:') or step.startswith('E:'):
                            self.hw.shi_compressor_cmds.append('off')
                        if self.hw.shi_cryopump.get_mcc_status('PumpOn?') or step.startswith('M:'):
                            self.hw.shi_compressor_cmds.append('on')

                    self.hw.vacuum_state = self.state

                    if "Operational Vacuum" in self.state:
                        self.hw.operation_vacuum = True
                    else:
                        self.hw.operation_vacuum = False

                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "VCS: Current chamber state: {}".format(self.state),
                                      "level": 4})

                    if old_state != self.state:
                        Logging.logEvent("Event", "Vacuum State",
                                         {"message": "New Vacuum State: '{}'".format(self.state),
                                          "ProfileInstance": ProfileInstance.getInstance()})

                    # sleep until the next time around
                    time.sleep(self.updatePeriod)

                # end of inner while True
            except Exception as e:

                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print("Error: {} in file {}:{}".format(exc_type, fname, exc_tb.tb_lineno))

                # FileCreation.pushFile("Error",self.zoneUUID,'{"errorMessage":"%s"}'%(e))
                ProfileInstance.getInstance().zoneProfiles.activeProfile = False
                Logging.debugPrint(1, "VCS: Error in check run, vacuum Control Stub: {}".format(str(e)))
                if Logging.debug:
                    raise e
            # end of try, catch
        # end of outer while true

    # end of run()

    def state_00(self):  # Chamber: Atm; CryoP: Vac
        if (self.cryoPumpPressure > self.pres_atm) and \
                (self.chamberPressure > self.pres_atm):
            self.state = 'Chamber: Atm; CryoP: Atm'
        if self.chamberPressure < self.pres_ruffon:
            self.state = 'Non-Operational Vacuum'
        if self.profile.vacuumWanted and (not self.hw.shi_cryopump.is_regen_active()):
            if self.cryoPumpPressure < self.pres_cryoP_Prime:
                self.hw.shi_mcc_cmds.append(['Close_PurgeValve'])
                self.hw.shi_mcc_cmds.append(['Close_RoughingValve'])
                self.hw.shi_compressor_cmds.append('on')
                self.hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
                self.hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
                self.hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
                self.state = 'PullingVac: CryoCool; Rough Chamber'
            else:
                if not self.hw.pc_104.digital_in.getVal('RoughP_Powered'):
                    self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
                    Logging.debugPrint(3, "Vacuum Ctl (@Atm): Applying power to the Ruffing Pump")
                else:
                    if not self.hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
                        self.hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
                        self.hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
                        Logging.debugPrint(3, "Vacuum Ctl (@Atm): Switching on the Ruffing Pump")
                    else:
                        self.state = 'PullingVac: Start'

    def state_01(self):  # Chamber: Atm; CryoP: Atm
        if self.cryoPumpPressure < self.pres_ruffon:
            self.state = 'Chamber: Atm; CryoP: Vac'
        if self.chamberPressure < self.pres_ruffon:
            self.state = 'Non-Operational Vacuum'
        if self.profile.vacuumWanted and (not self.hw.shi_cryopump.is_regen_active()):
            if not self.hw.pc_104.digital_in.getVal('RoughP_Powered'):
                self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
                Logging.debugPrint(3, "Vacuum Ctl (@Atm): Applying power to the Ruffing Pump")
            else:
                if not self.hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
                    self.hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
                    self.hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
                    Logging.debugPrint(3, "Vacuum Ctl (@Atm): Switching on the Ruffing Pump")
                else:
                    self.state = 'PullingVac: Start'

    def state_02(self):  # PullingVac: Start
        if self.profile.vacuumWanted and (not self.hw.shi_cryopump.is_regen_active()):
            if self.roughPumpPressure < self.pres_ruffon:
                self.state = 'PullingVac: RoughingCryoP'
                self.hw.shi_mcc_cmds.append(['Close_PurgeValve'])
                self.hw.shi_mcc_cmds.append(['Open_RoughingValve'])
        else:
            self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            self.hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
            self.state = 'Non-Operational Vacuum'

    def state_03(self):  # PullingVac: RoughingCryoP
        if self.profile.vacuumWanted and (not self.hw.shi_cryopump.is_regen_active()):
            if self.cryoPumpPressure < self.pres_cryoP_Prime:
                self.hw.shi_mcc_cmds.append(['Close_RoughingValve'])
                self.hw.shi_compressor_cmds.append('on')
                self.hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
                self.hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
                self.hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
                self.state = 'PullingVac: CryoCool; Rough Chamber'
            else:
                if self.hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
                    self.hw.shi_mcc_cmds.append(['Open_RoughingValve'])
                else:
                    self.hw.shi_mcc_cmds.append(['Close_RoughingValve'])
                    self.state = 'Chamber: Atm; CryoP: Atm'
        else:
            if (not self.hw.shi_cryopump.get_mcc_status('Roughing Valve State')) and \
                    (not self.hw.pc_104.digital_in.getVal('RoughP_On_Sw')):
                self.hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
                self.state = 'Non-Operational Vacuum'

    def state_04(self):  # PullingVac: CryoCool; Rough Chamber
        if self.profile.vacuumWanted and (not self.hw.shi_cryopump.is_regen_active()):
            if self.hw.shi_cryopump.is_cryopump_ready() and \
                    (self.chamberPressure < self.pres_chamber_crossover):
                self.state = 'PullingVac: Cryo Pumping; Cross Over'
            elif self.chamberPressure < self.pres_min_roughing:
                self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            else:
                if self.hw.pc_104.digital_in.getVal('RoughP_Powered'):
                    if self.hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
                        if (self.chamberPressure > self.roughPumpPressure) and \
                                (not self.hw.shi_cryopump.get_mcc_status('Roughing Valve State')):
                            self.hw.pc_104.digital_out.update({'RoughP GateValve': True})
                            Logging.debugPrint(3, "Vacuum Ctl (@OpVac): Ruffing the Chamber")
                        else:
                            self.hw.shi_mcc_cmds.append(['Close_RoughingValve'])
                    else:
                        self.hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
                        self.hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
                        Logging.debugPrint(3, "Vacuum Ctl (@OpVac): Switching on the Ruffing Pump")
                else:
                    self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
                    Logging.debugPrint(3, "Vacuum Ctl (@OpVac): Applying power to the Ruffing Pump")
        else:
            if not self.hw.shi_cryopump.get_mcc_status('PumpOn?'):
                self.state = 'PullingVac: M CryoCool; Rough Chamber'

    def state_05(self):  # PullingVac: M CryoCool; Rough Chamber
        if self.profile.vacuumWanted and (not self.hw.shi_cryopump.is_regen_active()):
            if self.hw.shi_cryopump.get_mcc_status('PumpOn?'):
                if self.hw.shi_cryopump.is_cryopump_ready() and \
                        (self.chamberPressure < self.pres_chamber_crossover):
                    self.state = 'PullingVac: Cryo Pumping; Cross Over'
                else:
                    self.state = 'PullingVac: CryoCool; Rough Chamber'
        else:
            if (not self.hw.shi_cryopump.get_mcc_status('Roughing Valve State')) and \
                    (not self.hw.pc_104.digital_in.getVal('RoughP_On_Sw')):
                self.hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
                self.state = 'Non-Operational Vacuum'

    def state_06(self):  # PullingVac: Cryo Pumping; Cross Over
        self.hw.pc_104.digital_out.update({'RoughP GateValve': False})
        # wait here until the valve is closed
        # TODO Replace Sleep with a check of the Gate valve switches
        time.sleep(10)
        # Open the cryopump gate valve
        self.hw.pc_104.digital_out.update({'CryoP GateValve': True})
        if self.hw.pc_104.digital_in.getVal('CryoP_GV_Open'):
            self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            self.hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
            self.state = 'PullingVac: Cryo Pumping Chamber'

    def state_07(self):  # PullingVac: Cryo Pumping Chamber
        if self.chamberPressure < (self.pres_opVac * 0.8):
            self.state = 'Operational Vacuum'
        if not self.hw.shi_cryopump.get_mcc_status('PumpOn?'):
            self.state = 'Non-Operational Vacuum'

    def state_08(self):  # Operational Vacuum: Cryo Pumping
        if self.chamberPressure > self.pres_opVac:
            self.state = 'Non-Operational Vacuum'
        elif self.hw.pc_104.digital_in.getVal('CryoP_GV_Closed') or \
                (not self.hw.shi_cryopump.get_mcc_status('PumpOn?')):
            self.state = 'Operational Vacuum'
        elif self.hw.shi_cryopump.is_regen_active() or \
                (not self.hw.shi_cryopump.is_cryopump_cold()):
            self.state = 'Operational Vacuum'
            self.hw.pc_104.digital_out.update({'CryoP GateValve': False})
            if not self.hw.pc_104.digital_in.getVal('CryoP_GV_Closed'):
                time.sleep(4)

    def state_09(self):  # Operational Vacuum
        if self.chamberPressure > self.pres_opVac:
            self.state = 'Non-Operational Vacuum'
        elif self.hw.shi_cryopump.get_mcc_status('PumpOn?') and \
                (not self.hw.shi_cryopump.cryopump_needs_regen()) and \
                (self.cryoPumpPressure < self.chamberPressure) and \
                (not self.hw.shi_cryopump.is_regen_active()):
            if (not self.hw.pc_104.digital_in.getVal('CryoP_GV_Closed')) or \
                    self.profile.vacuumWanted:
                if self.hw.pc_104.digital_in.getVal('RoughP_Powered'):
                    self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
                    self.hw.pc_104.digital_out.update({'RoughP PurgeGass': False})

                self.hw.pc_104.digital_out.update({'CryoP GateValve': True})
                self.state = 'Operational Vacuum: Cryo Pumping'
                Logging.debugPrint(3, "Vacuum Ctl (@OpVac): Switching from OV to OV:CP")
                time.sleep(4)
            else:
                self.hw.pc_104.digital_out.update({'CryoP GateValve': False})
        elif self.profile.vacuumWanted and \
                (not self.hw.shi_cryopump.is_regen_active()) and \
                (not self.hw.shi_cryopump.get_mcc_status('PumpOn?')):
            # self.hw.pc_104.digital_out.update({'CryoP GateValve': False})
            if self.cryoPumpPressure < self.pres_cryoP_Prime:
                self.hw.shi_mcc_cmds.append(['Close_PurgeValve'])
                self.hw.shi_mcc_cmds.append(['Close_RoughingValve'])
                self.hw.shi_compressor_cmds.append('on')
                self.hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
                self.hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
                self.hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
                time.sleep(5)
                self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
                self.hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
                Logging.debugPrint(3, "Vacuum Ctl (@OpVac): Starting the Cryo Pump; Roughing Pump Off.")
            else:
                if self.hw.pc_104.digital_in.getVal('RoughP_Powered'):
                    if self.hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
                        self.hw.shi_mcc_cmds.append(['Close_PurgeValve'])
                        self.hw.shi_mcc_cmds.append(['Open_RoughingValve'])
                        Logging.debugPrint(3, "Vacuum Ctl (@OpVac): Ruffing the Cryo Pump")
                    else:
                        self.hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
                        self.hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
                        Logging.debugPrint(3, "Vacuum Ctl (@OpVac): Switching on the Ruffing Pump")
                else:
                    self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
                    Logging.debugPrint(3, "Vacuum Ctl (@OpVac): Applying power to the Ruffing Pump")
        else:
            self.hw.pc_104.digital_out.update({'CryoP GateValve': False})

    def state_10(self):  # Non-Operational Vacuum
        if self.chamberPressure < (self.pres_opVac * 0.8):
            self.state = 'Operational Vacuum'
        if self.chamberPressure > self.pres_atm:
            if self.cryoPumpPressure < self.pres_ruffon:
                self.state = 'Chamber: Atm; CryoP: Vac'
            else:
                self.state = 'Chamber: Atm; CryoP: Atm'
        if self.profile.vacuumWanted and (not self.hw.shi_cryopump.is_regen_active()):
            if self.cryoPumpPressure < self.pres_cryoP_Prime:
                self.hw.shi_mcc_cmds.append(['Close_PurgeValve'])
                self.hw.shi_mcc_cmds.append(['Close_RoughingValve'])
                self.hw.shi_compressor_cmds.append('on')
                self.hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
                self.hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
                self.hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
                self.state = 'PullingVac: CryoCool; Rough Chamber'
            else:
                if not self.hw.pc_104.digital_in.getVal('RoughP_Powered'):
                    self.hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
                    Logging.debugPrint(3, "Vacuum Ctl (@Atm): Applying power to the Ruffing Pump")
                else:
                    if not self.hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
                        self.hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
                        self.hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
                        Logging.debugPrint(3, "Vacuum Ctl (@Atm): Switching on the Ruffing Pump")
                    else:
                        self.state = 'PullingVac: Start'

    def wait_for_hardware(self):
        ready = True
        ready &= self.hw.pc_104.digital_in.getVal('CryoP_GV_Open') is not None
        ready &= self.hw.pc_104.digital_in.getVal('CryoP_GV_Closed') is not None
        ready &= self.hw.pc_104.digital_in.getVal('RoughP_Powered') is not None
        ready &= self.hw.pc_104.digital_in.getVal('RoughP_On_Sw') is not None
        ready &= self.hw.pc_104.digital_in.getVal('Chamber Closed') is not None
        ready &= self.hw.pfeiffer_gauges.get_roughpump_pressure() is not None
        ready &= self.hw.pfeiffer_gauges.get_chamber_pressure() is not None
        ready &= self.hw.pfeiffer_gauges.get_cryopump_pressure() is not None
        ready &= self.hw.shi_cryopump.is_cryopump_cold() is not None
        ready &= self.hw.shi_cryopump.is_regen_active() is not None
        ready &= self.hw.shi_cryopump.cryopump_needs_regen() is not None
        ready &= self.hw.shi_cryopump.cryopump_wants_regen_soon() is not None
        ready &= self.hw.shi_cryopump.get_mcc_status('Tc Pressure') is not None
        ready &= self.hw.shi_cryopump.get_mcc_params('Tc Pressure State') is not None
        ready &= self.hw.shi_cryopump.get_mcc_status('Stage 1 Temp') is not None
        ready &= self.hw.shi_cryopump.get_mcc_status('Stage 2 Temp') is not None
        ready &= self.hw.shi_cryopump.get_compressor('Helium Discharge Temperature') is not None
        ready &= self.hw.shi_cryopump.get_compressor('Water Outlet Temperature') is not None
        ready &= self.hw.shi_cryopump.get_compressor('System ON') is not None
        ready &= self.profile.vacuumWanted is not None
        if os.name == "posix":
            userName = os.environ['LOGNAME']
        else:
            userName = "user"
        if not ready and "root" in userName:
            out = "CryoP_GV_Open: {}   \n".format(self.hw.pc_104.digital_in.getVal('CryoP_GV_Open'))
            out += "CryoP_GV_Closed: {}\n".format(self.hw.pc_104.digital_in.getVal('CryoP_GV_Closed'))
            out += "RoughP_Powered: {} \n".format(self.hw.pc_104.digital_in.getVal('RoughP_Powered'))
            out += "RoughP_On_Sw: {}   \n".format(self.hw.pc_104.digital_in.getVal('RoughP_On_Sw'))
            out += "Chamber Closed: {} \n".format(self.hw.pc_104.digital_in.getVal('Chamber Closed'))
            out += "get_roughpump_pressure: {}\n".format(self.hw.pfeiffer_gauges.get_roughpump_pressure())
            out += "get_chamber_pressure: {}  \n".format(self.hw.pfeiffer_gauges.get_chamber_pressure())
            out += "get_cryopump_pressure: {} \n".format(self.hw.pfeiffer_gauges.get_cryopump_pressure())
            out += "Is Cryopump Cold: {}    \n".format(self.hw.shi_cryopump.is_cryopump_cold())
            out += "Is Regen Active: {}     \n".format(self.hw.shi_cryopump.is_regen_active())
            out += "Cryopump needs Regen: {}\n".format(self.hw.shi_cryopump.cryopump_needs_regen())
            out += "Cryopump wants Regen: {}\n".format(self.hw.shi_cryopump.cryopump_wants_regen_soon())
            out += "Tc Pressure: {}      \n".format(self.hw.shi_cryopump.get_mcc_status('Tc Pressure'))
            out += "Tc Pressure State: {}\n".format(self.hw.shi_cryopump.get_mcc_params('Tc Pressure State'))
            out += "Stage 1 Temp: {}     \n".format(self.hw.shi_cryopump.get_mcc_status('Stage 1 Temp'))
            out += "Stage 2 Temp: {}     \n".format(self.hw.shi_cryopump.get_mcc_status('Stage 2 Temp'))
            out += "Helium Discharge Temp: {}\n".format(
                self.hw.shi_cryopump.get_compressor('Helium Discharge Temperature'))
            out += "Water Outlet Temperature: {}\n".format(
                self.hw.shi_cryopump.get_compressor('Water Outlet Temperature'))
            out += "System ON: {}\n".format(self.hw.shi_cryopump.get_compressor('System ON'))
            out += "Vacuum Wanted: {}\n<-------->".format(self.profile.vacuumWanted)
            Logging.debugPrint(3, out)
        return ready

    def determin_current_vacuum_state(self):
        if self.chamberPressure < self.pres_opVac:  ##
            return 'Operational Vacuum'
        if self.chamberPressure < self.pres_chamber_crossover:  ##
            if self.hw.shi_cryopump.get_mcc_status('PumpOn?'):
                if self.hw.shi_cryopump.is_cryopump_cold() and \
                        (not self.hw.pc_104.digital_in.getVal('CryoP_GV_Closed')):
                    self.hw.pc_104.digital_out.update({'CryoP GateValve': True})
                    return 'PullingVac: Cryo Pumping Chamber'
                else:
                    self.hw.pc_104.digital_out.update({'CryoP GateValve': False})
                    return 'PullingVac: CryoCool; Rough Chamber'
        if self.hw.pc_104.digital_in.getVal('RoughP_On_Sw'):
            if self.hw.shi_cryopump.get_mcc_status('Roughing Valve State'):
                self.hw.pc_104.digital_out.update({'RoughP GateValve': False})
                self.hw.pc_104.digital_out.update({'CryoP GateValve': False})
                if self.hw.shi_cryopump.is_regen_active():
                    pass
                else:
                    return 'PullingVac: RoughingCryoP'
            else:
                if self.hw.pc_104.digital_out.getVal('RoughP GateValve'):
                    if self.hw.shi_cryopump.get_mcc_status('PumpOn?'):
                        self.hw.pc_104.digital_out.update({'CryoP GateValve': False})
                        return 'PullingVac: CryoCool; Rough Chamber'
                    else:
                        return 'PullingVac: M CryoCool; Rough Chamber'
                else:  # Both Roughing valves are closed
                    pass  # leave the roughing pump on

        return 'Non-Operational Vacuum'
