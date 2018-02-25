import math, time
from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance

from Logging.Logging import Logging

def log_live_temperature_data(data):
    '''
    data = {
        "time":		TCs['time'],
        "tcList":	TCs['tcList'],
        "ProfileUUID": ProfileUUID,
    }
    TCs is a list of dicitations ordered like this....
    {
    'Thermocouple': tc_num,
    'time': tc_time_offset,
    'temp': tc_tempK,
    'working': tc_working,
    'alarm': tc_alarm
    }
    '''

    time = data["time"]
    profile = data["profileUUID"]
    coloums = "( profile_I_ID, time, thermocouple, temperature )"
    values = ""

    for tc in data['tcList']:
        thermocouple = tc["Thermocouple"]
        temperature = tc["temp"]
        if math.isnan(tc["temp"]):
            continue
        values += "( \"{}\", \"{}\", {}, {} ),\n".format(profile, time.strftime('%Y-%m-%d %H:%M:%S'), thermocouple,
                                                         temperature)
    sql = "INSERT INTO tvac.Real_Temperature {} VALUES {};".format(coloums, values[:-2])

    sql.replace("nan", "NULL")

    HardwareStatusInstance.getInstance().sql_list.append(sql)


def initialize_thermocouples(keysight):
    Logging.logEvent("Debug", "Status Update",
                     {"message": "Starting ThermoCoupleUpdater",
                      "level": 2})

    try:
        keysight.init_sys()
    except RuntimeError as e:
        # TODO: This needs to log to something...anything really
        print("ERROR: KeySight: There has been an error with the KeySight ({})".format(e))
    except TimeoutError as e:
        print("ERROR: KeySight: There has been a Timeout error with the KeySight ({})".format(e))
        HardwareStatusInstance.getInstance().thermocouple_power = False
    else:
        HardwareStatusInstance.getInstance().thermocouple_power = True

    tc_read_time = time.time()
    return tc_read_time


def thermocouple_update(keysight, tc_read_time, tc_read_period):
    hw = HardwareStatusInstance.getInstance()

    # If not enough time as passed, skip function
    if time.time() < tc_read_time:
        return tc_read_time

    tc_read_time += tc_read_period

    Logging.logEvent("Debug", "Status Update",
                     {"message": "Pulling live data for TC",
                      "level": 4})
    try:
        # Get the values from the TC's
        tc_values = keysight.get_tc_values()
    except RuntimeError as e:
        # TODO: This needs to log to something...anything really
        print("ERROR: KeySight: There has been an error with the KeySight ({})".format(e))
    except TimeoutError as e:
        print("ERROR: KeySight: There has been a Timeout error with the KeySight ({})".format(e))
        HardwareStatusInstance.getInstance().thermocouple_power = False
    else:
        HardwareStatusInstance.getInstance().thermocouple_power = True


        if ProfileInstance.getInstance().record_data:
            log_live_temperature_data({"time": tc_values['time'],
                                       "tcList": tc_values['tcList'],
                                       "profileUUID": ProfileInstance.getInstance().zoneProfiles.profileUUID})
        hw.thermocouples.update(tc_values)
        Logging.logEvent("Debug", "Data Dump",
                         {"message": "Current TC reading",
                          "level": 4,
                          "dict": tc_values['tcList']})

    return tc_read_time

