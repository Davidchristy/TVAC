import datetime, time
import ThreadControls.ThreadHelperFunctions

from Collections.ProfileInstance import ProfileInstance
from Collections.ProfileHelperFunctions import set_vacuum_wanted
from Logging.Logging import Logging, insert_into_sql, sql_fetch_one
from Collections.HardwareStatusInstance import HardwareStatusInstance


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


def generate_current_time(start_time, time_func=time.time):
    # if given a startTime, use that, otherwise, use current
    if start_time:
        Logging.debug_print(3, "DCCS: Starttime is: {}\t current: {}".format(start_time, time.time()))
        if "datetime.datetime" in str(type(start_time)):
            start_time = time.mktime(start_time.timetuple())
        current_time = int(start_time)
    else:
        current_time = int(time_func())
    return current_time


def get_zone_temp(zone_number):
    sql_str = "SELECT zone{}_Temp FROM tvac.Profile_Instance where endTime is null;".format(zone_number)
    result = sql_fetch_one(sql_str=sql_str)

    current_temp = float(result["zone{}_Temp".format(zone_number)])
    Logging.debug_print(1, "current_temp: {}".format(current_temp))
    return current_temp


def create_expected_time_values(set_points, interval_time, start_time=None, time_func=time.time):
    """
    This is a helper function that given a list of set points
    containing a GoalTemp, RampTime and SoakTime. It will
    generate a list time values and matching temperature values

    :param time_func:
    :param interval_time:
    :type start_time: object
    :param set_points:
    :param start_time:
    :return:
    """
    current_time = generate_current_time(start_time, time_func=time_func)

    expected_time_values = []
    for set_point in set_points:
        # get values out from set point
        ramp_time = set_point.ramp
        soak_time = set_point.soakduration
        real_time = time_func()
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


def create_expected_set_start_times(set_points, start_time=None, time_func=time.time):
    """
    This is a helper function that given a list of set points
    containing a GoalTemp, RampTime and SoakTime. It will
    generate a list time values and matching temperature values
    :type start_time: object
    :param set_points:
    :param start_time:
    :return:
    """

    current_time = generate_current_time(start_time,time_func=time_func)


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

# Outdated function, commented out for pending removal
# def create_expected_values(set_points, zone_name, interval_time, zone_number, start_time=None, get_zone_temp_fun=get_zone_temp):
#     """
#     This is a helper function that given a list of set points
#     containing a GoalTemp, RampTime and SoakTime. It will
#     generate a list time values and matching temperature values
#     :param zone_number:
#     :param interval_time:
#     :type start_time: object
#     :param zone_name:
#     :param get_zone_temp_fun:
#     :type get_zone_temp_fun: function
#     :param set_points:
#     :param start_time:
#     :return:
#     """
#
#     Logging.logEvent("Debug","Status Update",
#     {"message": "DCCS: Creating Expected temperature values: {}".format(zone_name),
#      "level":2})
#
#     current_time = generate_current_time(start_time)
#
#     current_temp = get_zone_temp_fun(zone_number)
#
#     expected_temp_values = []
#     expected_time_values = []
#     set_point_start_times = []
#     for set_point in set_points:
#         # get values out from set point
#         goal_temp = set_point.tempGoal
#         ramp_time = set_point.ramp
#         soak_time = set_point.soakduration
#         real_time = time.time()
#         # skip ramp section if rampTime == 0
#         if ramp_time != 0:
#             temp_delta = goal_temp-current_temp
#             number_of_jumps = ramp_time/interval_time
#             interval_temp = temp_delta/number_of_jumps
#             ramp_end_time = current_time+ramp_time
#
#             # Debug prints
#             debug_status = {
#             "goal temperature":goal_temp,
#             "Time at Start of Set Point": current_time,
#             "Ramp Duration": ramp_time,
#             "Delta temp per Update": interval_temp,
#             "Update Time" : interval_time,
#             "TempDelta Total": temp_delta,
#             }
#             Logging.logEvent("Debug","Data Dump",
#                 {"message": "DCCS: Set point {}: Ramp Status".format(set_point.thermalsetpoint),
#                  "level":3,
#                  "dict":debug_status})
#
#             # setting all values all for ramp
#             temp_temperatures = fill_temps_for_set_point(current_temp, current_time, real_time, interval_temp,
#                                                         interval_time, ramp_end_time)
#
#             temp_times = fill_times_for_set_point(current_time, real_time, interval_time, ramp_end_time)
#
#             expected_temp_values.extend(temp_temperatures)
#             expected_time_values.extend(temp_times)
#         else:
#             ramp_end_time = current_time
#         set_point_start_times.append([current_time, 0])
#
#         # Debug prints
#         debug_status = {
#         "Soak Duration": soak_time,
#         "goal temperature":goal_temp,
#         }
#         Logging.logEvent("Debug","Data Dump",
#             {"message": "DCCS: Setpoint {}: Soak Status".format(set_point.thermalsetpoint),
#              "level":3,
#              "dict":debug_status})
#
#         #Setting all soak values
#         set_point_start_times[-1][1] = ramp_end_time
#         for temp_set_point in range(ramp_end_time, ramp_end_time+soak_time, interval_time):
#             if temp_set_point > real_time:
#                 y = goal_temp
#                 expected_time_values.append(temp_set_point)
#                 expected_temp_values.append(y)
#         current_time = ramp_end_time+soak_time
#         current_temp = goal_temp
#     # end of for loop, end generating outputs
#
#     return expected_temp_values, expected_time_values, set_point_start_times


def log_expected_temperature_data(data):
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

    sql = "INSERT INTO tvac.Expected_Temperature {} VALUES {};".format(coloums, values[:-2])
    HardwareStatusInstance.getInstance().sql_list.append(sql)


def update_db_with_end_time():
    sql_str = "UPDATE tvac.Profile_Instance set endTime=\"{}\" where endTime is null;".format(datetime.datetime.fromtimestamp(time.time()))
    insert_into_sql(sql_str=sql_str)


def create_expected_values(pi, get_zone_temp_fun=get_zone_temp, time_func=time.time):
    for zone in pi.zone_dict:
        zone = pi.zone_dict[zone]
        if zone.active_zone_profile:
            zone.max_temp_rise_per_update = (zone.maxHeatPerMin / 60) * pi.update_period

            zone.expected_temp_values = create_expected_temp_values(zone.thermalProfiles,
                                                                    pi.update_period, zone.zone,
                                                                    start_time=pi.thermal_start_time,
                                                                    get_zone_temp_fun = get_zone_temp_fun)


    for zone in pi.zone_dict:
        zone = pi.zone_dict[zone]
        if zone.active_zone_profile:
            pi.expected_time_values = create_expected_time_values(zone.thermalProfiles,
                                                                  pi.update_period,
                                                                  start_time=pi.thermal_start_time,
                                                                  time_func=time_func)

            pi.set_points_start_time = create_expected_set_start_times(zone.thermalProfiles,
                                                                       start_time=pi.thermal_start_time,
                                                                       time_func=time_func)
            break


def stay_in_hold(pi, current_time):
    hw = HardwareStatusInstance.getInstance()
    Logging.logEvent("Event", "Hold Start",
                     {"message": "Starting Hold",
                      "ProfileInstance": pi})
    updates = find_num_of_updates_passed(pi.expected_time_values, current_time)
    update_current_temp_value(pi, updates)
    while pi.in_hold and pi.active_profile:
        update_all_duty_cycles(pi)
        ln2_update(pi=pi, hw=hw)
        time.sleep(pi.update_period)
    end_hold_time = int(time.time())
    return end_hold_time


def check_hold(pi, time_func=time.time, hold_func=stay_in_hold, zone_temp_func=get_zone_temp):
    """
    This is a helper function that keeps the loop held in same temp.
    It recreates the expected values with updated times at the end
    """
    if not pi.in_hold:
        return
    start_hold_time = int(time_func())

    end_hold_time = hold_func(pi, current_time=start_hold_time)

    # If you halted a profile while in hold, leave here.
    if not pi.active_profile:
        return

    hold_time = end_hold_time - start_hold_time

    if type(pi.thermal_start_time) == float or type(pi.thermal_start_time) == int:
        tmp_start_time = datetime.datetime.fromtimestamp(pi.thermal_start_time).timetuple()
    elif type(pi.thermal_start_time) == datetime.datetime:
        tmp_start_time = pi.thermal_start_time.timetuple()
    else:
        raise TypeError("thermal_start_time is unknown type")
    pi.thermal_start_time = time.mktime(tmp_start_time) + hold_time
    # At this point pi.startTime is an int (unix form)

    Logging.logEvent("Event","HoldEnd",
                     {"message": "Ending Hold",
                      "ProfileInstance"     : pi})

    Logging.logEvent("Debug","Status Update",
                     {"message": "Leaving hold after {} seconds in hold, new startTime {}".format(hold_time, pi.thermal_start_time),
                      "ProfileInstance"     : pi,
                      "level":2})

    # regenerate expected time, moving things forward to account for hold
    create_expected_values(pi)



def update_all_duty_cycles(pi):
    for zone in pi.zone_dict:
        zone = pi.zone_dict[zone]
        if zone.active_zone_profile and zone.temp_temperature:
            zone.calculate_duty_cycle(pi)
        else:
            zone.turn_off_heat_in_zone()
        if len(pi.expected_time_values) <= 0:
            break
        #end if
    #end for loop


def find_num_of_updates_passed(expected_time_values, current_time):
    i = 0
    while current_time > expected_time_values[i]:
        i += 1
        # If you are at the end of your profile, hard code it to -1
        if i >= len(expected_time_values):
            i = -1
            break
    return i


def update_current_temp_value(pi, updates):
    for zone in pi.zone_dict:
        zone = pi.zone_dict[zone]
        if zone.active_zone_profile:
            zone.temp_temperature = zone.expected_temp_values[updates]


def find_current_set_point(set_points_start_time, current_time):
    i = 0
    while current_time > set_points_start_time[i][0]:
        i += 1
        if i >= len(set_points_start_time):
            break
    return i

def check_if_in_ramp(set_points_start_time, current_time, set_point):
    return current_time < set_points_start_time[set_point-1][1]


def shorten_expected_values(pi, updates):
    pi.expected_time_values = pi.expected_time_values[updates:]
    for zone in pi.zone_dict:
        zone = pi.zone_dict[zone]
        if zone.active_zone_profile:
            zone.expected_temp_values = zone.expected_temp_values[updates:]


def check_active_duty_cycle():
    """
    Check to make sure there is an active profile
    and that we are sitting in an operational vacuum
    and that all drivers and updaters are running
    :return:
    """
    return ProfileInstance.getInstance().active_profile and \
           HardwareStatusInstance.getInstance().operational_vacuum and \
           HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed


def update_set_point_state(current_set_point, ramp_temporary, soak_temporary):
    pi = ProfileInstance.getInstance()
    pi.current_setpoint = current_set_point
    if ramp_temporary == True and pi.in_ramp == False:
        Logging.logEvent("Event", "Profile",
                         {"message": "Profile {} has entered set point {} Ramp".format(
                             pi.profile_name, current_set_point),
                          "ProfileInstance": pi})
        pi.in_ramp = True
    if soak_temporary == True and pi.in_soak == False:
        Logging.logEvent("Event", "Profile",
                         {"message": "Profile {} has entered set point {} Soak".format(
                             pi.profile_name, current_set_point),
                          "ProfileInstance": pi})
        pi.in_ramp = False
    pi.in_ramp = ramp_temporary
    pi.in_soak = soak_temporary


def turn_off_heat():
    pi = ProfileInstance.getInstance()
    # turning off lamps at the end of test
    for zone in pi.zone_dict:
        zone = pi.zone_dict[zone]
        zone.turn_off_heat_in_zone()


def ending_active_profile(already_logged=False):
    pi = ProfileInstance.getInstance()
    hw = HardwareStatusInstance.getInstance()
    turn_off_heat()
    if already_logged:
        Logging.logEvent("Event", "End Profile",
                         {'time': datetime.time(),
                          "message": pi.profile_name,
                          "ProfileInstance": ProfileInstance.getInstance()})
    hw.tdk_lambda_cmds.append(['Disable Platen Output', ''])
    update_db_with_end_time()
    tc_list = hw.thermocouples.tc_list
    for tc in tc_list:
        tc.update({"zone": 0, "userDefined": False})
    pi.active_profile = False
    set_vacuum_wanted(pi, False)

    pi.rebuild_zones()

    pi.profile_name = None
    pi.profile_uuid = None
    pi.current_setpoint = None
    pi.in_ramp = False
    ThreadControls.ThreadHelperFunctions.release_hold()

    pi.profile_start_time = None
    pi.thermal_start_time = None
    pi.expected_time_values = None
    pi.set_points_start_time = None

def active_profile_setup(pi, hw):
    hw = HardwareStatusInstance.getInstance()
    Logging.logEvent("Debug", "Status Update",
                     {"message": "DCCS: Starting Duty Cycle thread",
                      "level": 2})
    Logging.logEvent("Event", "Start Profile",
                     {'time': datetime.time(),
                      "message": pi.profile_name,
                      "ProfileInstance": pi})

    pi.update_thermal_start_time(thermal_start_time=time.time())

    Logging.logEvent("Debug", "Status Update",
                     {"message": "DCCS: Setting up Platen",
                      "level": 2})
    HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Setup Platen', ''])

    # Generate zone values
    create_expected_values(pi)

    # Close all 4 LN2 valves if they are open
    hw.pc_104.analog_out.update({'LN2 Shroud': 0,'LN2 Platen': 0})
    hw.pc_104.digital_out.update({'LN2-S Sol': False, 'LN2-P Sol': False})

def duty_cycle_update(pi, current_time):



    updates = find_num_of_updates_passed(pi.expected_time_values, current_time)
    update_current_temp_value(pi, updates)

    if updates == -1:
        pi.active_profile = False
        return

    shorten_expected_values(pi, updates)

    current_set_point = find_current_set_point(pi.set_points_start_time, current_time)
    ramp_temporary = check_if_in_ramp(pi.set_points_start_time, current_time, current_set_point)
    soak_temporary = not ramp_temporary

    Logging.logEvent("Debug", "Status Update",
                     {"message": "DCCS: Now in Set point {}, ramp: {}".format(current_set_point, ramp_temporary), "level": 2})

    update_set_point_state(current_set_point, ramp_temporary, soak_temporary)
    # With the temp goal temperature picked, make the duty cycle
    update_all_duty_cycles(pi)


def ln2_update(pi, hw):
    shroud_ln2_duty_cycle_max = 0.1
    shroud_ln2_duty_cycle_min = -0.2

    platen_ln2_duty_cycle_max = .05
    platen_ln2_duty_cycle_min = -.35
    valve_literal_max = 2047

    shroud_current_duty_cycle_min = find_lowest_shroud_duty_cycle(pi)
    if pi.zone_dict["zone9"].active_zone_profile:
        platen_duty = pi.zone_dict["zone9"].duty_cycle
    else:
        platen_duty = None

    if shroud_current_duty_cycle_min and shroud_current_duty_cycle_min < shroud_ln2_duty_cycle_max:
        # Throw the safety Valve open
        hw.pc_104.digital_out.update({'LN2-S Sol': True})

        # Calculate the percent the valve should be open
        valve_percent_open = (shroud_current_duty_cycle_min - shroud_ln2_duty_cycle_max) / (shroud_ln2_duty_cycle_min - shroud_ln2_duty_cycle_max)

        # if the duty cycle is less than the lowest, cap percent open at 100%
        if shroud_current_duty_cycle_min < shroud_ln2_duty_cycle_min:
            valve_percent_open = 1

        valve_literal = valve_percent_open * valve_literal_max

        hw.pc_104.analog_out.update({'LN2 Shroud': valve_literal})
    else:
        hw.pc_104.digital_out.update({'LN2-S Sol': False})
        hw.pc_104.analog_out.update({'LN2 Shroud': 0})

    if platen_duty and platen_duty < platen_ln2_duty_cycle_max:
        hw.pc_104.digital_out.update({'LN2-P Sol': True})

        # Calculate the percent the valve should be open
        valve_percent_open = (platen_duty - platen_ln2_duty_cycle_max) / (platen_ln2_duty_cycle_min - platen_ln2_duty_cycle_max)

        # if the duty cycle is less than the lowest, cap percent open at 100%
        if platen_duty < platen_ln2_duty_cycle_min:
            valve_percent_open = 1

        valve_literal = valve_percent_open * valve_literal_max

        hw.pc_104.analog_out.update({'LN2 Platen': valve_literal})
    else:
        hw.pc_104.digital_out.update({'LN2-P Sol': False, })
        hw.pc_104.analog_out.update({'LN2 Platen': 0})


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