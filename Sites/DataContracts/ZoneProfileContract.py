import threading, math, time, datetime

from Collections.HardwareStatusInstance import HardwareStatusInstance
from DataContracts.ThermalProfileContract import ThermalProfileContract
from PID.PID import PID
from Logging.Logging import Logging, insert_into_sql
from ThreadControls.SafetyCheckHelperFunctions import enter_safe_mode


def log_expected_temperature_data(data, pi):
    '''
    data = {
         "expected_temp_values": expected_temp_values,
         "expected_time_values": expected_time_values,
         "Zone"                : self.args[0],
         "profileUUID"         : self.zoneProfile.profileUUID,
    '''
    expected_temp_values = data["expected_temp_values"]
    expected_time_values = data["expected_time_values"]
    zone = data["zone"]
    profile = data["profileUUID"]

    coloums = "( profile_I_ID, time, zone, temperature )"
    values = ""
    for i in range(len(expected_temp_values)):
        time_str = expected_time_values[i]
        time_str = datetime.datetime.fromtimestamp(time_str)

        temperature = expected_temp_values[i]
        values += "( \"{}\", \"{}\", {}, {} ),\n".format(profile, time_str.strftime('%Y-%m-%d %H:%M:%S'), int(zone[4:]),
                                                         temperature)

    sql_str = "INSERT INTO tvac.Expected_Temperature {} VALUES {};".format(coloums, values[:-2])
    insert_into_sql(sql_str=sql_str)

class ZoneProfileContract:
    '''
    This is a Class that holds all the data on a given zone, this data includes:
    
    - A list of thermocouples
    - A list of thermalProfiles, this is a list of time points, ramps, soak times, and temps. 
    - The Average temp of all the TC's
    - Zone data number and UUID
    '''

    __lock = threading.RLock()

    def __init__(self, name, lamps, pi):
        self.name = name
        self.lamps = lamps
        self.pi = pi

        self.zone = None
        self.active_zone_profile = False
        self.average = None
        self.thermocouples = None
        self.thermalProfiles = None
        self.maxHeatError = None
        self.minHeatError = None
        self.maxHeatPerMin = None
        self.zoneUUID = False

        self.pid = PID()
        if self.lamps:
            # These are the PID settings for the lamps
            proportional_gain = .2
            integral_gain = 0
            derivative_gain = 0
        else:
            # These are the PID settings for the heaters in the platen
            proportional_gain = .4
            integral_gain = 0
            derivative_gain = 0

        self.pid.setKp(proportional_gain)
        self.pid.setKi(integral_gain)
        self.pid.setKd(derivative_gain)

        # The variable where the current temp goal is held
        self.temp_temperature = None
        # The place the current Duty cycle is held (used by outside functions)
        self.duty_cycle = None
        self.max_temp_rise_per_update = None
        self.expected_temp_values = None


    def setThermocouples(self, thermocouples):
        self.__lock.acquire()
        hwStatus = HardwareStatusInstance.getInstance()
        list = []
        for tc in thermocouples:
            list.append(hwStatus.thermocouples.getTC(tc))
        self.__lock.release()
        return list

    def setThermalProfiles(self,thermalProfiles):
        self.__lock.acquire()
        list = []
        for profile in thermalProfiles:
            list.append(ThermalProfileContract(profile))
        self.__lock.release()
        return list

    def update(self, d):
        self.__lock.acquire()
        Logging.debug_print(3, "Updating a zone profile", d)
        if 'zone' in d:
            self.zone = d['zone']
        if 'profileuuid' in d:
            self.pi.profile_uuid = d['profileuuid']
        if 'zoneuuid' in d:
            self.zoneUUID = d['zoneuuid']
        if 'average' in d:
            self.average = d['average']
        if 'thermalprofiles' in d:
            self.thermalProfiles = self.setThermalProfiles(d['thermalprofiles'])
        if 'thermocouples' in d:
            self.thermocouples = self.setThermocouples(d['thermocouples'])
        if 'max_heat_error' in d: 
            self.maxHeatError = float(d['max_heat_error'])
        if 'min_heat_error' in d: 
            self.minHeatError = float(d['min_heat_error'])
        if 'max_heat_per_min' in d: 
            self.maxHeatPerMin = float(d['max_heat_per_min'])
        self.__lock.release()


    def getTemp(self, mode=None):
        self.__lock.acquire()
        temp = ""
        if not mode:
            mode = self.average
        if mode == "Average":
            temp = (sum(tc.getTemp() for tc in self.thermocouples) / len(self.thermocouples))
        if mode == "Min":
            temp = min(self.thermocouples, key=lambda x: x.getTemp()).getTemp()
        if mode == "Max":
            temp = max(self.thermocouples, key=lambda x: x.getTemp()).getTemp()
        self.__lock.release()
        return temp


    def getJson(self):
        self.__lock.acquire()
        message = ['{"zone":%s,' % self.zone,
                   '"profileuuid":"%s",' % self.pi.profile_uuid,
                   '"average":%s,' % self.average,
                   '"zoneUUID":"%s",' % self.zoneUUID,
                   '"thermalprofiles":[']
        profileLen = len(self.thermalProfiles)
        count = 0
        for profile in self.thermalProfiles:
            message.append(profile.getJson())
            if count < (profileLen - 1):
                message.append(',')
                count = count + 1

        message.append('],')
        message.append('"thermocouples":[')
        coupleLen = len(self.thermocouples)
        count = 0
        for couple in self.thermocouples:
            message.append(couple.getJson())
            if count < (coupleLen - 1):
                message.append(',')
                count = count + 1

        message.append(']}')
        self.__lock.release()
        return ''.join(message)

    def turn_off_heat_in_zone(self):
        hw = HardwareStatusInstance.getInstance()
        if self.lamps:
            d_out = hw.pc_104.digital_out
            d_out.update({self.lamps[1] + " PWM DC": 0})
            d_out.update({self.lamps[0] + " PWM DC": 0})
        else:
            # for zone 9, the platen
            hw.tdk_lambda_cmds.append(['Platen Duty Cycle', 0])

    def calculate_duty_cycle(self, pi):
        hw = HardwareStatusInstance.getInstance()
        """
        Given that temp_temperature is assigned to a value, this will
        update the duty cycle for the lamps
        """
        # print("{}: avg ({})\goal({}) -- {}".format(self.name,
        #                                                            self.zone_profile.getTemp(self.zone_profile.average),
        #                                                            self.temp_temperature,
        #                                                            self.duty_cycle))

        if math.isnan(self.getTemp(self.average)):
            enter_safe_mode("A controlled TC has been removed or is unreadable")
            raise RuntimeError("Controlled thermocouple has been lost, setting safe state")


        self.pid.SetPoint = self.temp_temperature
        self.pid.update(self.getTemp(self.average))
        max_temp_rise_per_update = (self.maxHeatPerMin / 60) * pi.update_period
        self.duty_cycle = self.pid.error_value / max_temp_rise_per_update

        # TODO: pick what lamp you want to use. Do you want to use upper or lower lamp, now it's set for both
        if self.lamps:
            d_out = hw.pc_104.digital_out
            d_out.update({self.lamps[1] + " PWM DC": self.duty_cycle})
            d_out.update({self.lamps[0] + " PWM DC": self.duty_cycle})
        else:
            # for zone 9, the platen
            hw.tdk_lambda_cmds.append(['Platen Duty Cycle', self.duty_cycle])

        Logging.debug_print(2, "{}: avg ({})\goal({}) -- {}".format(self.name,
                                                                    self.getTemp(self.average),
                                                                    self.temp_temperature,
                                                                    self.duty_cycle))
        # If false is here because it was showing too much data
        if False:
            Logging.logEvent("Debug","Status Update",
                {"message": "{}: Current temp: {}".format(self.name,self.getTemp(self.average)),
                "level":2})
            Logging.logEvent("Debug","Status Update",
                {"message": "{}: Temp Goal temperature is {}".format(self.name,self.temp_temperature),
                "level":2})
            Logging.logEvent("Debug","Status Update",
                {"message": "{}: Current duty Cycle: {}".format(self.name,self.duty_cycle),
                "level":2})

        log_expected_temperature_data(
        {"expected_temp_values": [self.temp_temperature],
         "expected_time_values": [time.time()],
         "zone"                : self.name,
         "profileUUID"         : pi.profile_uuid,
         "ProfileInstance"     : pi,
        }, pi)