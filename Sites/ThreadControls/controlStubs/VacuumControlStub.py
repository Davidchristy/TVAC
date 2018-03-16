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


def update_data_state():
    hw = HardwareStatusInstance.getInstance()
    pi = ProfileInstance.getInstance()
    data = {'cryopump_gv_closed'    : hw.pc_104.digital_in.getVal('CryoP_GV_Closed'),
            'vacuum_wanted'         : pi.vacuum_wanted,
            'is_regen_active'       : hw.shi_cryopump.is_regen_active(),
            'rough_pump_pumping'    : hw.pc_104.digital_in.getVal('RoughP_On_Sw'),
            'cryopump_pumping'      : hw.shi_cryopump.get_mcc_status('PumpOn?'),
            'rough_pump_powered'    : hw.pc_104.digital_in.getVal('RoughP_Powered'),
            'is_cryopump_ready'     : hw.shi_cryopump.is_cryopump_ready(),
            'roughing_gv_open'      : hw.shi_cryopump.get_mcc_status('Roughing Valve State'),
            'cryopump_needs_regen'  : hw.shi_cryopump.cryopump_needs_regen(),
            'is_cryopump_cold'      : hw.shi_cryopump.is_cryopump_cold(),
            'cryopump_gv_open'      : hw.pc_104.digital_in.getVal('CryoP_GV_Open'),
            "chamber_pres"          : hw.pfeiffer_gauges.get_chamber_pressure(),
            'cryopump_pres'         : hw.pfeiffer_gauges.get_cryopump_pressure(),
            'rough_pump_pres'       : hw.pfeiffer_gauges.get_roughpump_pressure(),
            'op_vac_pres'           : 9e-5,
            'chamber_x_over_pres'   : 25e-3,
            'atm_pres'              : 100,
            'weak_vac_x_over_pres'  : 70,
            'cryopump_x_over_pres'  : 40e-3,
            'min_roughing_pres'     : 9e-4
            }
    return data

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

        self.state = None
        # self.pres_opVac = 9e-5
        # self.pres_atm = 100
        # self.pres_cryoP_Prime = 40e-3
        # self.pres_chamber_crossover = 25e-3
        # self.pres_chamber_max_crossover = 40e-3
        # self.pres_min_roughing = 9e-4
        # self.pres_ruffon = 70
        # self.cryoPumpPressure = None
        # self.chamberPressure = None
        # self.roughPumpPressure = None

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

                current_system_state = update_data_state()

                self.state = self.determine_current_vacuum_state(current_system_state)
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
                    # self.cryoPumpPressure = hw.pfeiffer_gauges.get_cryopump_pressure()
                    # self.chamberPressure = hw.pfeiffer_gauges.get_chamber_pressure()
                    # self.roughPumpPressure = hw.pfeiffer_gauges.get_roughpump_pressure()

                    current_system_state = update_data_state()
                    Logging.logEvent("Debug", "Status Update",
                                     {"message": "VCS: Current chamber pressure: {}".format(current_system_state['chamber_pres']),
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
                    }[self.state](current_system_state)

                    if hw.shi_cryopump.is_regen_active():
                        self.regen_cryopump(current_system_state)

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

    def regen_cryopump(self, current_state):
        hw = HardwareStatusInstance.getInstance()
        hw.pc_104.digital_out.update({'RoughP GateValve': False})
        step = hw.shi_cryopump.get_mcc_status('Regen Step')

        if hw.shi_cryopump.get_mcc_status('Roughing Interlock: Roughing Needed'):
            # If the roughing pump is running, not just on.
            if current_state['rough_pump_pumping']:

                if current_state['rough_pump_pres'] < current_state['cryopump_pres']:
                    hw.shi_mcc_cmds.append(['Clear_RoughingInterlock'])
                    Logging.logEvent("Event", "Cryopump Regeneration",
                                     {"message": "Clearing Roughing Interlock.".format(self.state),
                                      "ProfileInstance": ProfileInstance.getInstance()})
            else:
                # If the Roughing pump is on, make it start, if not, turn it on.

                if current_state['rough_pump_powered']:
                    hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
                    hw.pc_104.digital_out.update({'RoughP Start': True})
                else:
                    hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
                    hw.pc_104.digital_out.update({'RoughP PurgeGass': True})

        # If the cryopump doesn't need the roughing pump, turn it off
        elif (not current_state['roughing_gv_open']) and \
                (not step.startswith('T:')) and (not step.startswith('J:')) and \
                (not step.startswith('H:')):
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
        regen_cryopump_ending(step)

    # end of run()

    def state_00(self, current_state):  # Chamber: Atm; CryoP: Vac
        """

        :return:
        """
        hw = HardwareStatusInstance.getInstance()

        if (current_state['cryopump_pres'] > current_state['atm_pres']) and \
                (current_state['chamber_pres'] > current_state['atm_pres']):
            self.state = 'Chamber: Atm; CryoP: Atm'

        if current_state['chamber_pres'] < current_state['weak_vac_x_over_pres']:
            self.state = 'Non-Operational Vacuum'

        if not current_state['vacuum_wanted'] or current_state['is_regen_active']:
            return
        if current_state['cryopump_pres'] < current_state['cryopump_x_over_pres']:
            hw.shi_mcc_cmds.append(['Close_PurgeValve'])
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])
            hw.shi_compressor_cmds.append('on')
            hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
            hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
            hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
            self.state = 'PullingVac: CryoCool; Rough Chamber'
            return

        if not current_state['rough_pump_powered']:
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Applying power to the Ruffing Pump")
            return

        if not current_state['rough_pump_pumping']:
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Switching on the Ruffing Pump")
        else:
            self.state = 'PullingVac: Start'

    def state_01(self, current_state):  # Chamber: Atm; CryoP: Atm
        """

        :return:
        """
        hw = HardwareStatusInstance.getInstance()
        if current_state['cryopump_pres'] < current_state['weak_vac_x_over_pres']:
            self.state = 'Chamber: Atm; CryoP: Vac'

        if current_state['chamber_pres'] < current_state['weak_vac_x_over_pres']:
            self.state = 'Non-Operational Vacuum'

        if not current_state['vacuum_wanted'] or current_state['is_regen_active']:
            return

        if not current_state['rough_pump_powered']:
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Applying power to the Ruffing Pump")
            return

        if not current_state['rough_pump_pumping']:
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Switching on the Ruffing Pump")
        else:
            self.state = 'PullingVac: Start'

    def state_02(self, current_state):  # PullingVac: Start
        """

        :return:
        """
        hw = HardwareStatusInstance.getInstance()
        if not current_state['vacuum_wanted'] or current_state['is_regen_active']:
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
            self.state = 'Non-Operational Vacuum'
            return

        # If the roughing pump pressure is less 70 torr, start roughing out the cryopump

        if current_state['rough_pump_pres'] < current_state['weak_vac_x_over_pres']:
            hw.shi_mcc_cmds.append(['Close_PurgeValve'])
            hw.shi_mcc_cmds.append(['Open_RoughingValve'])
            self.state = 'PullingVac: RoughingCryoP'

    def state_03(self, current_state):  # PullingVac: RoughingCryoP
        """
\
        :return:
        """
        hw = HardwareStatusInstance.getInstance()
        if not current_state['vacuum_wanted'] or current_state['is_regen_active']:

            # If we aren't pumping the chamber, close the roughing pump, and set set non-operational vacuum
            if not current_state['roughing_gv_open'] and \
                   not current_state['rough_pump_pumping']:
                hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
                self.state = 'Non-Operational Vacuum'
            return

        # When the cryopump gets below pressure, start the cryopump
        if current_state['cryopump_pres'] < current_state['cryopump_x_over_pres']:
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])
            hw.shi_compressor_cmds.append('on')
            hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
            hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
            hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
            self.state = 'PullingVac: CryoCool; Rough Chamber'
            return

        # If the roughing pump is pumping, open the roughing valve
        if current_state['rough_pump_pumping']:
            hw.shi_mcc_cmds.append(['Open_RoughingValve'])
        else:
            # Else, turn off the close the roughing valve
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])
            self.state = 'Chamber: Atm; CryoP: Atm'

    def state_04(self, current_state):  # PullingVac: CryoCool; Rough Chamber
        """
        :return:
        """
        hw = HardwareStatusInstance.getInstance()
        if not current_state['vacuum_wanted'] or current_state['is_regen_active']:
            if not current_state['cryopump_pumping']:
                self.state = 'PullingVac: M CryoCool; Rough Chamber'
            return

        if current_state['is_cryopump_ready'] and \
                (current_state['chamber_pres'] < current_state['chamber_x_over_pres']):
            self.state = 'PullingVac: Cryo Pumping; Cross Over'
            return

        # TODO: if this line is hit before the roughing gate valve is closed, there will be problems
        if current_state['chamber_pres'] < current_state['min_roughing_pres']:
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            return

        if not current_state['rough_pump_powered']:
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Applying power to the Ruffing Pump")
            return

        if not current_state['rough_pump_pumping']:
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Switching on the Ruffing Pump")
            return

        if (current_state['chamber_pres'] > current_state['rough_pump_pres']) and \
                (not current_state['roughing_gv_open']):
            hw.pc_104.digital_out.update({'RoughP GateValve': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Ruffing the Chamber")
        else:
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])

    def state_05(self, current_state):  # PullingVac: M CryoCool; Rough Chamber
        """

        :return:
        """
        hw = HardwareStatusInstance.getInstance()
        if not current_state['vacuum_wanted'] or current_state['is_regen_active']:
            if (not current_state['roughing_gv_open']) and \
                    (not current_state['rough_pump_pumping']):
                hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
                self.state = 'Non-Operational Vacuum'
            return


        if not (current_state['cryopump_pumping']):
            return

        if current_state['is_cryopump_ready'] and \
                (current_state['chamber_pres'] < current_state['chamber_x_over_pres']):
            self.state = 'PullingVac: Cryo Pumping; Cross Over'
        else:
            self.state = 'PullingVac: CryoCool; Rough Chamber'

    def state_06(self, current_state):  # PullingVac: Cryo Pumping; Cross Over
        """
        :return:
        """
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

        if current_state['cryopump_gv_open']:
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
            hw.pc_104.digital_out.update({'RoughP PurgeGass': False})
            self.state = 'PullingVac: Cryo Pumping Chamber'

    def state_07(self, current_state):  # PullingVac: Cryo Pumping Chamber
        """
        :return:
        """

        if current_state['chamber_pres'] < (current_state['op_vac_pres'] * 0.8):
            self.state = 'Operational Vacuum'
            # TODO: This probably be a return here, not allowing it to check the next one.

        if not current_state['cryopump_pumping']:
            self.state = 'Non-Operational Vacuum'

    def state_08(self, current_state):  # Operational Vacuum: Cryo Pumping
        """

        :return:
        """
        hw = HardwareStatusInstance.getInstance()
        if current_state['chamber_pres'] > current_state['op_vac_pres']:
            self.state = 'Non-Operational Vacuum'
            return

        if current_state['cryopump_gv_closed'] or \
                (not current_state['cryopump_pumping']):
            self.state = 'Operational Vacuum'
            return

        if current_state['is_regen_active'] or \
                (not current_state['is_cryopump_cold']):
            # TODO: Why are both these op-vac?
            self.state = 'Operational Vacuum'
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            if not current_state['cryopump_gv_closed']:
                time.sleep(4)

    def state_09(self, current_state):  # Operational Vacuum
        """
        :return:
        """
        hw = HardwareStatusInstance.getInstance()
        if current_state['chamber_pres'] > current_state['op_vac_pres']:
            self.state = 'Non-Operational Vacuum'
            return
        if current_state['cryopump_pumping'] and \
                (not current_state['cryopump_needs_regen']) and \
                (current_state['cryopump_pres'] < current_state['chamber_pres']) and \
                (not current_state['is_regen_active']):


            if current_state['cryopump_gv_closed'] and not current_state['vacuum_wanted']:
                hw.pc_104.digital_out.update({'CryoP GateValve': False})
                return

            if current_state['rough_pump_powered']:
                hw.pc_104.digital_out.update({'RoughP Pwr Relay': False})
                hw.pc_104.digital_out.update({'RoughP PurgeGass': False})

            hw.pc_104.digital_out.update({'CryoP GateValve': True})
            self.state = 'Operational Vacuum: Cryo Pumping'
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Switching from OV to OV:CP")
            time.sleep(4)
            return

        if not (current_state['vacuum_wanted'] and
                (not current_state['is_regen_active']) and
                (not current_state['cryopump_pumping'])):
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            return

        if current_state['cryopump_pres'] < current_state['cryopump_x_over_pres']:
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

        if not current_state['rough_pump_powered']:
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Applying power to the Ruffing Pump")
            return


        if current_state['rough_pump_pumping']:
            hw.shi_mcc_cmds.append(['Close_PurgeValve'])
            hw.shi_mcc_cmds.append(['Open_RoughingValve'])
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Ruffing the Cryo Pump")
        else:
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@OpVac): Switching on the roughing Pump")

    def state_10(self, current_state):  # Non-Operational Vacuum
        """
        :return:
        """
        hw = HardwareStatusInstance.getInstance()
        if current_state['chamber_pres'] < (current_state['op_vac_pres'] * 0.8):
            self.state = 'Operational Vacuum'
        if current_state['chamber_pres'] > current_state['atm_pres']:
            if current_state['cryopump_pres'] < current_state['weak_vac_x_over_pres']:
                self.state = 'Chamber: Atm; CryoP: Vac'
            else:
                self.state = 'Chamber: Atm; CryoP: Atm'
        if not current_state['vacuum_wanted'] or current_state['is_regen_active']:
            return

        if current_state['cryopump_pres'] < current_state['cryopump_x_over_pres']:
            hw.shi_mcc_cmds.append(['Close_PurgeValve'])
            hw.shi_mcc_cmds.append(['Close_RoughingValve'])
            hw.shi_compressor_cmds.append('on')
            hw.shi_mcc_cmds.append(['FirstStageTempCTL', 50, 2])
            hw.shi_mcc_cmds.append(['SecondStageTempCTL', 10])
            hw.shi_mcc_cmds.append(['Turn_CryoPumpOn'])
            self.state = 'PullingVac: CryoCool; Rough Chamber'
            return

        if not current_state['rough_pump_powered']:
            hw.pc_104.digital_out.update({'RoughP Pwr Relay': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Applying power to the Ruffing Pump")
            return

        if not current_state['rough_pump_pumping']:
            hw.pc_104.digital_out.update({'RoughP Start': True})  # Turn on Roughing Pump
            hw.pc_104.digital_out.update({'RoughP PurgeGass': True})
            Logging.debug_print(3, "Vacuum Ctl (@Atm): Switching on the Ruffing Pump")
        else:
            self.state = 'PullingVac: Start'

    def determine_current_vacuum_state(self, current_state):
        hw = HardwareStatusInstance.getInstance()
        if current_state['chamber_pres'] < current_state['op_vac_pres']:  ##
            return 'Operational Vacuum'

        if current_state['chamber_pres'] < current_state['chamber_x_over_pres'] and current_state['cryopump_pumping']:

            if current_state['is_cryopump_cold'] and (not current_state['cryopump_gv_closed']):
                hw.pc_104.digital_out.update({'CryoP GateValve': True})
                return 'PullingVac: Cryo Pumping Chamber'
            else:
                hw.pc_104.digital_out.update({'CryoP GateValve': False})
                return 'PullingVac: CryoCool; Rough Chamber'

        if not current_state['rough_pump_pumping']:
            return 'Non-Operational Vacuum'

        if current_state['roughing_gv_open']:
            hw.pc_104.digital_out.update({'RoughP GateValve': False})
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            if hw.shi_cryopump.is_regen_active():
                return 'Non-Operational Vacuum'
            else:
                return 'PullingVac: RoughingCryoP'

        if not (hw.pc_104.digital_out.getVal('RoughP GateValve')):
            return 'Non-Operational Vacuum'

        if current_state['cryopump_pumping']:
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            return 'PullingVac: CryoCool; Rough Chamber'
        else:
            return 'PullingVac: M CryoCool; Rough Chamber'
