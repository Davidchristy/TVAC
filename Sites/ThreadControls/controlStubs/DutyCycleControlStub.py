from threading import Thread
import time
import datetime
import sys
import os


from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance
from PID.PID import PID

from Logging.MySql import MySQlConnect
from Logging.Logging import Logging


def fill_temps_for_set_point(current_temp, current_time, real_time, interval_temp, interval_time, ramp_end_time):
    """

    :param current_temp:
    :param current_time:
    :param real_time:
    :param interval_temp:
    :param interval_time:
    :param ramp_end_time:
    :return:
    """
    temp_temperatures = []
    for i, temp_set_point in enumerate(range(current_time, ramp_end_time, interval_time)):
        if temp_set_point > real_time:
            y = current_temp + (i * interval_temp)
            temp_temperatures.append(y)
    return temp_temperatures

def fill_times_for_set_point(current_time, real_time, interval_time, ramp_end_time):
    temp_times = []
    for i, temp_set_point in enumerate(range(current_time, ramp_end_time, interval_time)):
        if temp_set_point > real_time:
            temp_times.append(temp_set_point)
    return temp_times

def generate_current_time(start_time):
    # if given a startTime, use that, otherwise, use current
    if start_time:
        Logging.debugPrint(3, "DCCS: Starttime is: {}\t current: {}".format(start_time, time.time()))
        if "datetime.datetime" in str(type(start_time)):
            start_time = time.mktime(start_time.timetuple())
        current_time = int(start_time)
    else:
        current_time = int(time.time())
    return current_time

def get_zone_temp(zone_number):
    sql = "SELECT zone{}_Temp FROM tvac.Profile_Instance where endTime is null;".format(zone_number)
    mysql = MySQlConnect()
    try:
        mysql.cur.execute(sql)
        mysql.conn.commit()
    except Exception as e:
        Logging.debugPrint(3, "sql: {}".format(sql))
        Logging.debugPrint(1, "Error in get_current_temp: {}".format(str(e)))
        if Logging.debug:
            raise e
    result = mysql.cur.fetchone()
    current_temp = float(result["zone{}_Temp".format(zone_number)])
    Logging.debugPrint(1, "current_temp: {}".format(current_temp))
    return current_temp

def create_expected_time_values(set_points, interval_time, start_time=None):
    """
    This is a helper function that given a list of set points
    containing a GoalTemp, RampTime and SoakTime. It will
    generate a list time values and matching temperature values

    :param interval_time:
    :type start_time: object
    :param set_points:
    :param start_time:
    :return:
    """
    current_time = generate_current_time(start_time)

    expected_time_values = []
    for set_point in set_points:
        # get values out from set point
        ramp_time = set_point.ramp
        soak_time = set_point.soakduration
        real_time = time.time()
        # skip ramp section if rampTime == 0
        if ramp_time != 0:
            ramp_end_time = current_time+ramp_time

            temp_times = fill_times_for_set_point(current_time, real_time, interval_time, ramp_end_time)

            expected_time_values.extend(temp_times)
        else:
            ramp_end_time = current_time

        for temp_set_point in range(ramp_end_time, ramp_end_time+soak_time, interval_time):
            if temp_set_point > real_time:
                expected_time_values.append(temp_set_point)

        current_time = ramp_end_time+soak_time
    # end of for loop, end generating outputs

    return expected_time_values

def create_expected_temp_values(set_points, interval_time, zone_number, start_time=None, get_zone_temp_fun=get_zone_temp):
    """
    This is a helper function that given a list of set points
    containing a GoalTemp, RampTime and SoakTime. It will
    generate a list time values and matching temperature values
    """

    current_time = generate_current_time(start_time)

    current_temp = get_zone_temp_fun(zone_number)

    expected_temp_values = []
    for set_point in set_points:
        # get values out from set point
        goal_temp = set_point.tempGoal
        ramp_time = set_point.ramp
        soak_time = set_point.soakduration
        real_time = time.time()
        # skip ramp section if rampTime == 0
        if ramp_time != 0:
            temp_delta = goal_temp-current_temp
            number_of_jumps = ramp_time/interval_time
            interval_temp = temp_delta/number_of_jumps
            ramp_end_time = current_time+ramp_time

            # setting all values all for ramp
            temp_temperatures = fill_temps_for_set_point(current_temp, current_time, real_time, interval_temp,
                                                        interval_time, ramp_end_time)
            expected_temp_values.extend(temp_temperatures)
        else:
            ramp_end_time = current_time

        for temp_set_point in range(ramp_end_time, ramp_end_time+soak_time, interval_time):
            if temp_set_point > real_time:
                expected_temp_values.append(goal_temp)
        current_time = ramp_end_time+soak_time
        current_temp = goal_temp
    # end of for loop, end generating outputs

    return expected_temp_values

def create_expected_set_start_times(set_points, start_time=None):
    """
    This is a helper function that given a list of set points
    containing a GoalTemp, RampTime and SoakTime. It will
    generate a list time values and matching temperature values
    :type start_time: object
    :param set_points:
    :param start_time:
    :return:
    """

    current_time = generate_current_time(start_time)


    set_point_start_times = []
    for set_point in set_points:
        # get values out from set point
        ramp_time = set_point.ramp
        soak_time = set_point.soakduration
        # skip ramp section if rampTime == 0
        if ramp_time != 0:
            ramp_end_time = current_time+ramp_time
        else:
            ramp_end_time = current_time

        set_point_start_times.append([current_time, ramp_end_time])

        current_time = ramp_end_time+soak_time
    # end of for loop, end generating outputs

    return set_point_start_times

def create_expected_values(set_points, zone_name, interval_time, zone_number, start_time=None, get_zone_temp_fun=get_zone_temp):
    """
    This is a helper function that given a list of set points
    containing a GoalTemp, RampTime and SoakTime. It will
    generate a list time values and matching temperature values
    :param zone_number:
    :param interval_time:
    :type start_time: object
    :param zone_name:
    :param get_zone_temp_fun:
    :type get_zone_temp_fun: function
    :param set_points:
    :param start_time:
    :return:
    """

    Logging.logEvent("Debug","Status Update",
    {"message": "DCCS: Creating Expected temperature values: {}".format(zone_name),
     "level":2})

    current_time = generate_current_time(start_time)

    current_temp = get_zone_temp_fun(zone_number)

    expected_temp_values = []
    expected_time_values = []
    set_point_start_times = []
    for set_point in set_points:
        # get values out from set point
        goal_temp = set_point.tempGoal
        ramp_time = set_point.ramp
        soak_time = set_point.soakduration
        real_time = time.time()
        # skip ramp section if rampTime == 0
        if ramp_time != 0:
            temp_delta = goal_temp-current_temp
            number_of_jumps = ramp_time/interval_time
            interval_temp = temp_delta/number_of_jumps
            ramp_end_time = current_time+ramp_time

            # Debug prints
            debug_status = {
            "goal temperature":goal_temp,
            "Time at Start of Set Point": current_time,
            "Ramp Duration": ramp_time,
            "Delta temp per Update": interval_temp,
            "Update Time" : interval_time,
            "TempDelta Total": temp_delta,
            }
            Logging.logEvent("Debug","Data Dump",
                {"message": "DCCS: Set point {}: Ramp Status".format(set_point.thermalsetpoint),
                 "level":3,
                 "dict":debug_status})

            # setting all values all for ramp
            temp_temperatures = fill_temps_for_set_point(current_temp, current_time, real_time, interval_temp,
                                                        interval_time, ramp_end_time)

            temp_times = fill_times_for_set_point(current_time, real_time, interval_time, ramp_end_time)

            expected_temp_values.extend(temp_temperatures)
            expected_time_values.extend(temp_times)
        else:
            ramp_end_time = current_time
        set_point_start_times.append([current_time, 0])

        # Debug prints
        debug_status = {
        "Soak Duration": soak_time,
        "goal temperature":goal_temp,
        }
        Logging.logEvent("Debug","Data Dump",
            {"message": "DCCS: Setpoint {}: Soak Status".format(set_point.thermalsetpoint),
             "level":3,
             "dict":debug_status})

        #Setting all soak values
        set_point_start_times[-1][1] = ramp_end_time
        for temp_set_point in range(ramp_end_time, ramp_end_time+soak_time, interval_time):
            if temp_set_point > real_time:
                y = goal_temp
                expected_time_values.append(temp_set_point)
                expected_temp_values.append(y)
        current_time = ramp_end_time+soak_time
        current_temp = goal_temp
    # end of for loop, end generating outputs

    return expected_temp_values, expected_time_values, set_point_start_times

class ZoneControlStub:
    def __init__(self, name, lamps=None, parent=None):
        Logging.logEvent("Debug","Status Update", 
        {"message": "Creating ZoneControlStub: {}".format(name),
         "level":3})

        self.zone_profile = ProfileInstance.getInstance().zoneProfiles.getZone(name)
        self.duty_cycle = None

        self.lamps = lamps
        self.name = name
        self.parent = parent
        self.temp_temperature = None

        self.max_temp_rise_per_min = None
        self.max_temp_rise_per_update = None
        self.expected_temp_values = None

        self.pid = PID()
        if lamps:
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
    # end init

    def update_duty_cycle(self):
        """
        Given that temp_temperature is assigned to a value, this will 
        update the duty cycle for the lamps
        """

        self.pid.SetPoint = self.temp_temperature
        self.pid.update(self.zone_profile.getTemp(self.zone_profile.average))
        self.duty_cycle = self.pid.error_value / self.max_temp_rise_per_update

        # TODO: pick what lamp you want to use. Do you want to use upper or lower lamp, now it's set for both
        if self.lamps:
            if os.name == "posix":
                user_name = os.environ['LOGNAME']
            else:
                user_name = "user"
            if "root" in user_name:
                self.parent.d_out.update({self.lamps[1] + " PWM DC": self.duty_cycle})
                self.parent.d_out.update({self.lamps[0] + " PWM DC": self.duty_cycle})
            else:
                # TODO: Update the virualized text file here
                pass
        else:
            # for zone 9, the platen
            HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Platen Duty Cycle', self.duty_cycle])

        Logging.debugPrint(2, "{}: avg ({})\goal({}) -- {}".format(self.name,
                                                                   self.zone_profile.getTemp(self.zone_profile.average),
                                                                   self.temp_temperature,
                                                                   self.duty_cycle))
        # If false is here because it was showing too much data
        if False:
            Logging.logEvent("Debug","Status Update",
                {"message": "{}: Current temp: {}".format(self.name,self.zone_profile.getTemp(self.zone_profile.average)),
                "level":2})
            Logging.logEvent("Debug","Status Update",
                {"message": "{}: Temp Goal temperature is {}".format(self.name,self.temp_temperature),
                "level":2})
            Logging.logEvent("Debug","Status Update",
                {"message": "{}: Current duty Cycle: {}".format(self.name,self.duty_cycle),
                "level":2})

        Logging.logExpectedTemperatureData(
        {"expected_temp_values": [self.temp_temperature],
         "expected_time_values": [time.time()],
         "zone"                : self.name,
         "profileUUID"         : self.zone_profile.profileUUID,
         "ProfileInstance"     : ProfileInstance.getInstance()
        })
    # end update_duty_cycle



def update_db_with_end_time():
    sql = "update tvac.Profile_Instance set endTime=\"{}\" where endTime is null;".format(datetime.datetime.fromtimestamp(time.time()))
    mysql = MySQlConnect()
    try:
        mysql.cur.execute(sql)
        mysql.conn.commit()
    except Exception as e:
        Logging.debugPrint(1, "Error in updateDBwithEndTime, Duty Cycle control: {}".format(str(e)))
        if Logging.debug:
            raise e


class DutyCycleControlStub(Thread):
    """
    This class contains the main inteligences for reading the data from the system,
    and telling the lamps what to do. 

    It controls if we are in a ramp, hold, soak, or paused.
    It also generates the expected temp values at the given time 
    """

    def __init__(self, parent=None):
        Logging.logEvent("Debug","Status Update",
        {"message": "Creating DutyCycleControlStub",
         "level":2})

        self.zoneProfiles = ProfileInstance.getInstance().zoneProfiles
        self.parent = parent
        Thread.__init__(self)
        self.updatePeriod = ProfileInstance.getInstance().zoneProfiles.updatePeriod
        self.d_out        = HardwareStatusInstance.getInstance().pc_104.digital_out

        self.zones = {
            "zone1": ZoneControlStub(name='zone1',lamps=['IR Lamp 1','IR Lamp 2'], parent=self),
            "zone2": ZoneControlStub(name='zone2',lamps=['IR Lamp 3','IR Lamp 4'], parent=self),
            "zone3": ZoneControlStub(name='zone3',lamps=['IR Lamp 6','IR Lamp 5'], parent=self),
            "zone4": ZoneControlStub(name='zone4',lamps=['IR Lamp 7','IR Lamp 8'], parent=self),
            "zone5": ZoneControlStub(name='zone5',lamps=['IR Lamp 9','IR Lamp 10'], parent=self),
            "zone6": ZoneControlStub(name='zone6',lamps=['IR Lamp 12','IR Lamp 11'], parent=self),
            "zone7": ZoneControlStub(name='zone7',lamps=['IR Lamp 13','IR Lamp 14'], parent=self),
            "zone8": ZoneControlStub(name='zone8',lamps=['IR Lamp 15','IR Lamp 16'], parent=self),
            # zone9 is the platen
            "zone9": ZoneControlStub(name='zone9', parent=self)
            }


        self.ramp = False
        self.soak = False
        self.running = False

        self.startTime = None
        self.expected_time_values = None
        self.set_points_start_time = None


    def run(self):
        # While true to restart the thread if it errors out
        while True:
            # Check to make sure there is an active profile
            # and that we are sitting in an operational vacuum
            # and that all drivers and updaters are running
            if ProfileInstance.getInstance().activeProfile and \
                HardwareStatusInstance.getInstance().operational_vacuum and \
                ProfileInstance.getInstance().zoneProfiles.getActiveProfileStatus() and \
                    HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed:
                try:
                    # setup test
                    self.active_profile_setup()

                    # Program loop is here
                    self.active_program_loop()

                    # end of test
                    self.ending_active_profile()
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print("Error: {} in file {}:{}".format(exc_type, fname, exc_tb.tb_lineno))


                    self.running = False
                    ProfileInstance.getInstance().zoneProfiles.activeProfile = False
                    Logging.debugPrint(1, "DCCS: Error in run, Duty Cycle: {}".format(str(e)))
                    Logging.logEvent("Error", "Duty Cycle Control Stub Thread",
                     {"type": exc_type,
                      "filename": fname,
                      "line": exc_tb.tb_lineno,
                      "thread": "DutyCycleControlStub",
                      "ThreadCollection":self.parent,
                      "item":"Duty Cycle Control Stub",
                      "itemID":-1,
                      "details":"There is a software error ({})".format(e)
                    })


                    if Logging.debug:
                        raise e
                # end of try, catch
            else:
                Logging.debugPrint(4,"DCCS: activeProfile: {}".format(ProfileInstance.getInstance().activeProfile))
                Logging.debugPrint(4,"DCCS: OperationalVacuum: {}".format(HardwareStatusInstance.getInstance().operational_vacuum))
                Logging.debugPrint(4,"DCCS: getActiveProfileStatus: {}".format(ProfileInstance.getInstance().zoneProfiles.getActiveProfileStatus()))
                Logging.debugPrint(3,"Chamber Closed: {}".format(HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed))
            # Sleeping so it doesn't busy wait
            time.sleep(1)
            # end of running check
        # end of outer while True
    # end of run()

    def ending_active_profile(self):
        self.turn_off_heat()
        Logging.logEvent("Event", "End Profile",
                         {'time': datetime.time(),
                          "message": ProfileInstance.getInstance().zoneProfiles.profileName,
                          "ProfileInstance": ProfileInstance.getInstance()})
        HardwareStatusInstance.getInstance().tdk_lambda__cmds.append(['Disable Platen Output', ''])
        update_db_with_end_time()
        self.running = False
        tc_list = HardwareStatusInstance.getInstance().thermocouples.tcList
        for tc in tc_list:
            tc.update({"zone": 0, "userDefined": False})
        ProfileInstance.getInstance().activeProfile = False
        ProfileInstance.getInstance().vacuumWanted = False

    def active_profile_setup(self):
        Logging.logEvent("Debug", "Status Update",
                         {"message": "DCCS: Starting Duty Cycle thread",
                          "level": 2})
        Logging.logEvent("Event", "Start Profile",
                         {'time': datetime.time(),
                          "message": ProfileInstance.getInstance().zoneProfiles.profileName,
                          "ProfileInstance": ProfileInstance.getInstance()})

        ProfileInstance.getInstance().zoneProfiles.updateThermalStartTime(time.time())

        if self.zoneProfiles.thermalStartTime:
            self.startTime = self.zoneProfiles.thermalStartTime
        else:
            self.startTime = int(time.time())

        Logging.logEvent("Debug", "Status Update",
                         {"message": "DCCS: Setting up Platen",
                          "level": 2})

        HardwareStatusInstance.getInstance().tdk_lambda__cmds.append(['Setup Platen', ''])

        # Generate zone values
        for zone in self.zones:
            zone = self.zones[zone]
            if zone.zone_profile.activeZoneProfile:
                zone.max_temp_rise_per_min = zone.zone_profile.maxHeatPerMin
                zone.max_temp_rise_per_update = (zone.max_temp_rise_per_min / 60) * self.updatePeriod
                zone.expected_temp_values = create_expected_temp_values(zone.zone_profile.thermalProfiles, self.updatePeriod, zone.zone_profile.zone, start_time = self.zoneProfiles.thermalStartTime)
        for zone in self.zones:
            zone = self.zones[zone]
            if zone.zone_profile.activeZoneProfile:
                self.expected_time_values = create_expected_time_values(zone.zone_profile.thermalProfiles, self.updatePeriod, start_time = self.zoneProfiles.thermalStartTime)
                self.set_points_start_time = create_expected_set_start_times(zone.zone_profile.thermalProfiles, start_time = self.zoneProfiles.thermalStartTime)
                break
        return

    def turn_off_heat(self):
        # turning off lamps at the end of test
        for zone in self.zones:
            if self.zones[zone].zone_profile.activeZoneProfile:

                zone = self.zones[zone]
                if zone.lamps:
                    self.d_out.update({zone.lamps[1] + " PWM DC": 0})
                    self.d_out.update({zone.lamps[0] + " PWM DC": 0})
                else:
                    HardwareStatusInstance.getInstance().tdk_lambda__cmds.append(['Platen Duty Cycle', 0])

    def active_program_loop(self):
        current_set_point = 1
        ramp_temporary = False
        soak_temporary = True
        while ProfileInstance.getInstance().activeProfile:

            # if there is no more expected time values, break out of while True loop
            if len(self.expected_time_values) <= 0:
                break

            Logging.logEvent("Debug", "Status Update",
                             {"message": "DCCS: Running Duty Cycle Thread",
                              "level": 3})

            # get current time
            current_time = time.time()

            current_set_point, ramp_temporary, soak_temporary = self.find_current_temp_value(
                current_set_point, current_time, ramp_temporary, soak_temporary)

            self.check_hold()
            self.update_set_point_state(current_set_point, ramp_temporary, soak_temporary)
            # With the temp goal temperature picked, make the duty cycle
            self.update_all_duty_cycles()
            # sleep until the next time around
            time.sleep(self.updatePeriod)
        # end of inner while True

    def update_all_duty_cycles(self):
        for zone in self.zones:
            zone = self.zones[zone]
            if zone.zone_profile.activeZoneProfile:
                # This checks to see if a current temp has been made...
                if zone.temp_temperature:
                    zone.update_duty_cycle()
                else:
                    # TODO: Why is "Waiting..." here?
                    print("Waiting...")

            if len(self.expected_time_values) <= 0:
                break

    def update_set_point_state(self, current_set_point, ramp_temporary, soak_temporary):
        # compare the temps just made with the values in self.
        # if they are different, or important log it
        if ramp_temporary == True and self.ramp == False:
            ProfileInstance.getInstance().currentSetpoint = current_set_point
            Logging.logEvent("Event", "Profile",
                             {"message": "Profile {} has entered setpoint {} Ramp".format(
                                 ProfileInstance.getInstance().zoneProfiles.profileName, current_set_point),
                              "ProfileInstance": ProfileInstance.getInstance()})
        if soak_temporary == True and self.soak == False and current_set_point > 1:
            Logging.logEvent("Event", "Profile",
                             {"message": "Profile {} has entered setpoint {} Soak".format(
                                 ProfileInstance.getInstance().zoneProfiles.profileName, current_set_point - 1),
                              "ProfileInstance": ProfileInstance.getInstance()})
            ProfileInstance.getInstance.inRamp = False
        self.ramp = ramp_temporary
        self.soak = soak_temporary

    def find_current_temp_value(self, current_set_point_temporary, current_time, ramp_temporary, soak_temporary):
        # this will find the time value matching the current time
        # and give us the temp value it should be at that time.
        while current_time > self.expected_time_values[0]:
            for zone in self.zones:
                if self.zones[zone].zone_profile.activeZoneProfile:
                    self.zones[zone].temp_temperature = self.zones[zone].expected_temp_values[0]
                    self.zones[zone].expected_temp_values = self.zones[zone].expected_temp_values[1:]
            self.expected_time_values = self.expected_time_values[1:]
            if len(self.set_points_start_time) > 0 and current_time > self.set_points_start_time[0][0]:
                ramp_temporary = True
                soak_temporary = False
                if current_time > self.set_points_start_time[0][1]:
                    ramp_temporary = False
                    soak_temporary = True
                    self.set_points_start_time = self.set_points_start_time[1:]
                    current_set_point_temporary += 1
                if len(self.set_points_start_time) <= 0:
                    break

            if len(self.expected_time_values) <= 0:
                break
        return current_set_point_temporary, ramp_temporary, soak_temporary

    def check_hold(self):
        """
        This is a helper function that keeps the loop held in same temp.
        It recreates the expected values with updated times at the end

        TODO: NOTE: if a hold is held less than updateTime it might not recalculate or even get in here
        """

        try:
            if not ProfileInstance.getInstance().inHold:
                return

            start_hold_time = int(time.time())

            Logging.logEvent("Event","Hold Start",
            {"message": "In hold for first time",
            "ProfileInstance"     : ProfileInstance.getInstance()})
            while ProfileInstance.getInstance().inHold:
                for zone in self.zones:
                    zone = self.zones[zone]
                    if zone.zone_profile.activeZoneProfile:
                        # self.temp_temperature =
                        zone.update_duty_cycle()
                time.sleep(.5)

            end_hold_time = int(time.time())
            hold_time = end_hold_time - start_hold_time
            self.startTime = self.startTime + hold_time
            Logging.logEvent("Event","HoldEnd",
            {"message": "Just Left hold",
            "ProfileInstance"     : ProfileInstance.getInstance()})
            Logging.logEvent("Debug","Status Update",
            {"message": "Leaving hold after {} seconds in hold, new startTime {}".format(hold_time, self.startTime),
            "ProfileInstance"     : ProfileInstance.getInstance(),
            "level":2})
            # regenerate expected time, moving things forward to account for hold
            for zone in self.zones:
                zone = self.zones[zone]
                if zone.zone_profile.activeZoneProfile:
                    zone.expected_temp_values = create_expected_temp_values(zone.zone_profile.thermalProfiles,
                                                                            self.updatePeriod, zone.zone_profile.zone,
                                                                            start_time=self.zoneProfiles.thermalStartTime)
            self.expected_time_values = create_expected_time_values(zone.zone_profile.thermalProfiles,
                                                                    self.updatePeriod,
                                                                    start_time=self.zoneProfiles.thermalStartTime)
            self.parent.set_points_start_time = create_expected_set_start_times(zone.zone_profile.thermalProfiles,
                                                                               start_time=self.zoneProfiles.thermalStartTime)
        except Exception as e:
            Logging.debugPrint(1, "DCCS: Error in check Hold, Duty Cycle: {}".format(str(e)))
            if Logging.debug:
                raise e

