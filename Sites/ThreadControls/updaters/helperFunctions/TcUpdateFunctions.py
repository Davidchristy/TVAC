import math, time
from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance
from ThreadControls.SafetyCheckHelperFunctions import log_hw_error

from Logging.Logging import Logging, insert_into_sql

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
    sql_str = "INSERT INTO tvac.Real_Temperature {} VALUES {};".format(coloums, values[:-2])

    sql_str.replace("nan", "NULL")

    insert_into_sql(sql_str)

def initialize_thermocouples(keysight):
    pi = ProfileInstance.getInstance()
    Logging.logEvent("Debug", "Status Update",
                     {"message": "Starting ThermoCoupleUpdater",
                      "level": 2})

    try:
        keysight.init_sys()
    except RuntimeError as e:
        item = "KeySight"
        error_details = "ERROR: {}: There has been an error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
        error = True
    except TimeoutError as e:
        HardwareStatusInstance.getInstance().thermocouple_power = False
        item = "KeySight"
        error_details = "ERROR: {}: There has been a Timeout error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
        error = True
    else:
        HardwareStatusInstance.getInstance().thermocouple_power = True
        error = False


    tc_read_time = time.time()
    return error, tc_read_time


def thermocouple_update(keysight, tc_read_time, tc_read_period):
    hw = HardwareStatusInstance.getInstance()
    pi = ProfileInstance.getInstance()

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
        item = "KeySight"
        error_details = "ERROR: {}: There has been an error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
        error = True
    except TimeoutError as e:
        HardwareStatusInstance.getInstance().thermocouple_power = False
        item = "KeySight"
        error_details = "ERROR: {}: There has been a Timeout error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
        error = True
    else:
        HardwareStatusInstance.getInstance().thermocouple_power = True
        error = False


        if ProfileInstance.getInstance().record_data:
            log_live_temperature_data({"time": tc_values['time'],
                                       "tcList": tc_values['tcList'],
                                       "profileUUID": ProfileInstance.getInstance().profile_uuid})
        hw.thermocouples.update(tc_values)
        Logging.logEvent("Debug", "Data Dump",
                         {"message": "Current TC reading",
                          "level": 4,
                          "dict": tc_values['tcList']})

    return error, tc_read_time

