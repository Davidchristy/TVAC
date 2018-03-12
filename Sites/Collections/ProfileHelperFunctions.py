import math, time, uuid, datetime
from Logging.Logging import Logging, insert_into_sql, sql_fetch_all, sql_fetch_one
from Collections.HardwareStatusInstance import HardwareStatusInstance

def save_profile(json, pi):
    name = "Error"
    sql_str = "SELECT * FROM tvac.Thermal_Zone_Profile WHERE profile_name=\"{}\";".format(name)
    try:
        name = json["name"]
        profiles = json['profiles']
    except KeyError:
        return "{'result':'Error, JSON received is malformed'}"

    try:
        results = sql_fetch_all(sql_str=sql_str)
    except Exception as e:
        Logging.debug_print(3, "sql: {}".format(sql_str))
        Logging.debug_print(1, "Error in loadProfile, zoneCollection: {}".format(str(e)))
        return str({'result': str(e)})
    else:

        if results:
            return "{'result':'Error, profile already exists'}"
    try:
        for zone_profile in profiles:
            save_zone(name, zone_profile)
    except KeyError:
        return "{'result':'Error, JSON received is malformed'}"
    Logging.logEvent("Event", "Profile",
                     {"message": "New Profile loaded: ({})".format(name),
                      "ProfileInstance": pi})
    return "{'result':'success'}"


def save_zone(name, zone_profile):
    """
    This is a helper function for saveProfile. It saves the data needed for each zone into the DB
    """
    try:
        average = zone_profile["average"]
        zone = zone_profile["zone"]
        heat_error = zone_profile["maxTemp"]
        min_temp = zone_profile["minTemp"]
        max_slope =zone_profile["maxSlope"]
    except KeyError as e:
        raise e


    coloums = "( profile_name, zone, average, max_heat_error, min_heat_error, max_heat_per_min )"
    values = "( \"{}\",{},\"{}\",{},{},{} )".format(name,zone,average, heat_error, min_temp, max_slope)
    sql_str = "INSERT INTO tvac.Thermal_Zone_Profile {} VALUES {};".format(coloums, values)
    insert_into_sql(sql_str=sql_str)

    coloums = "( profile_name, zone, set_point, temp_goal, ramp_time, soak_time )"
    values = ""
    for profile in zone_profile["thermalprofiles"]:
        set_point = profile["thermalsetpoint"]
        temp_goal = profile["tempgoal"]
        ramp_time = profile["ramp"]
        soak_time = profile["soakduration"]

        values += "( \"{}\", {}, {}, {}, {}, {} ),\n".format(name, zone, set_point, temp_goal, ramp_time, soak_time)
    sql_str = "INSERT INTO tvac.Thermal_Profile {} VALUES {};".format(coloums, values[:-2])
    insert_into_sql(sql_str=sql_str)

    # Saving the TC as well
    coloums = "( profile_name, zone, thermocouple )"
    values = ""
    for tc in zone_profile["thermocouples"]:
        values += "( \"{}\", {}, {} ),\n".format(name, zone, tc)
    sql_str = "INSERT INTO tvac.TC_Profile {} VALUES {};".format(coloums, values[:-2])
    insert_into_sql(sql_str=sql_str)


def load_thermal_profiles(profile_name, zone):
    '''
    This is a helper medthod for LoadProfile, this will load thermal profiles
    '''
    sql_str = "SELECT * FROM tvac.Thermal_Profile WHERE profile_name=\"{}\" AND zone=\"{}\";".format(profile_name,zone)

    results = sql_fetch_all(sql_str=sql_str)

    thermalprofiles = []
    for result in results:
        TP = {
            'thermalsetpoint': int(result['set_point']),
            'tempgoal': float(result['temp_goal']),
            'soakduration': int(result['soak_time']),
            'ramp': int(result['ramp_time'])}
        thermalprofiles.append(TP)

    return thermalprofiles


def load_thermocouples(profile_name, zone):
    """
    This is a helper method for LoadProfile, this will load thermocouples tied to this profile
    """

    sql_str = "SELECT * FROM tvac.TC_Profile WHERE profile_name=\"{}\" AND zone=\"{}\";".format(profile_name,zone)
    results = sql_fetch_all(sql_str=sql_str)

    # Get a list of all the TC's in the current zone
    tmp_tc_list = []
    for result in results:
        tmp_tc_list.append(int(result['thermocouple']))

    # Mark that list as "user defined"
    tc_list = HardwareStatusInstance.getInstance().thermocouples.tc_list
    for tc in tc_list:
        if tc.Thermocouple in tc_list:
            tc.update({"zone":"zone"+str(int(results[0]['zone'])),"userDefined":True})

    return tmp_tc_list


def find_current_temps(zone_dict):
    # Build the SQL string to send to the DB, holding the starting temps for the profile.
    tmp_str = ""
    # Look through every zone
    for zone in zone_dict:
        # if that zone is currently used
        if zone_dict[zone].active_zone_profile:
            # Keep looping until the current temp is non NaN or or 0
            # If they are NaN or 0 that means the they haven't been loaded into the program yet by the TC updater
            while True:
                # note, if ANY of them are NaN the average will be NaN
                current_temp = zone_dict[zone].getTemp(zone_dict[zone].average)

                if not math.isnan(current_temp) and int(current_temp) != 0:
                    break
                time.sleep(.5)
            tmp_str += "{}_Temp = {},".format(zone, current_temp)
    # Remove the traveling comma
    tmp_str = tmp_str[:-1]
    return tmp_str


def transform_sql_data_to_zone_profile(profile_name, result, profile_uuid):
    zone_profile = {'profileuuid': profile_uuid,
                    'zone': result['zone'],
                    'zoneuuid': uuid.uuid4(),
                    'average': result['average'],
                    'max_heat_error': result['max_heat_error'],
                    'min_heat_error': result['min_heat_error'],
                    'max_heat_per_min': result['max_heat_per_min']
                }

    try:
        zone_profile['thermalprofiles'] = load_thermal_profiles(profile_name, result['zone'])
    except Exception as e:
        raise e
    try:
        zone_profile["thermocouples"] = load_thermocouples(profile_name, result['zone'])
    except Exception as e:
        raise e
    # After you have all the data on the zone, add it to the instance
    Logging.debug_print(3, "Loaded Profile Data Zone {}: ".format(zone_profile['zone']), zone_profile)
    return zone_profile


def add_profile_instance_to_db(pi):
    '''
    This is a helper function of runProfile that adds the new profile Instance to the DB
    '''

    coloums = "( profile_name, profile_I_ID, profile_Start_Time )"
    values = "( \"{}\",\"{}\", \"{}\" )".format(pi.profile_name,pi.profile_uuid, datetime.datetime.fromtimestamp(time.time()))
    sql_str = "INSERT INTO tvac.Profile_Instance {} VALUES {};".format(coloums, values)
    insert_into_sql(sql_str=sql_str)
    return True


def run_profile(pi, first_start = True):
    """
    This assumes a profile is already loaded in RAM, it will start the profile
    Also making an entry in the DB
    """

    # Check to make sure there is an active profile in memory
    if not pi.profile_name:
        return "{'Error':'No Profile loaded in memory'}"

    if first_start:
        add_profile_instance_to_db(pi)

    pi.active_profile = True
    set_vacuum_wanted(pi, True)
    Logging.debug_print(2, "Setting Active Profile to True")

    return "{'result':'success'}"


def set_vacuum_wanted(pi, wanted):
    pi.vacuum_wanted = wanted
    if wanted:
        wanted_str = "1"
    else:
        wanted_str = "0"
        pi.vacuum_obtained = False
    sql_str = "UPDATE System_Status SET vacuum_wanted={};".format(wanted_str)
    insert_into_sql(sql_str=sql_str)


def return_active_profile():
    """
    A helper function that will look in the DB to see if there is any half finished profile instances
    Returns the profile profile_name and Profile ID if there is, False, False if not
    """
    sql_str = "SELECT profile_name, profile_Start_Time, thermal_Start_Time, first_Soak_Start_Time FROM tvac.Profile_Instance WHERE endTime IS NULL;"
    result = sql_fetch_one(sql_str=sql_str)
    if not result:
        raise RuntimeError("Tried to return Active profile when no active profile present in DB")
    return result

