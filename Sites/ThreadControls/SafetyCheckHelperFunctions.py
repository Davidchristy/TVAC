import datetime

from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance
from Logging.Logging import Logging
from ThreadControls.ThreadHelperFunctions import release_hold


def power_failure():
    results = True
    # Done
    results = results and HardwareStatusInstance.getInstance().pfeiffer_gauge_power
    # Done
    results = results and HardwareStatusInstance.getInstance().shi_compressor_power
    # Done
    results = results and HardwareStatusInstance.getInstance().shi_mcc_power
    # Done
    results = results and HardwareStatusInstance.getInstance().tdk_lambda_power
    # Done
    results = results and HardwareStatusInstance.getInstance().thermocouple_power

    results = results and HardwareStatusInstance.getInstance().pc_104_power
    return not results


def enter_safe_mode(error_mesg):
    ProfileInstance.getInstance().active_profile = False
    Logging.debug_print(1, error_mesg)
    print(error_mesg)
    d_out = HardwareStatusInstance.getInstance().pc_104.digital_out
    d_out.update({"IR Lamp 1 PWM DC": 0})
    d_out.update({"IR Lamp 2 PWM DC": 0})
    d_out.update({"IR Lamp 3 PWM DC": 0})
    d_out.update({"IR Lamp 4 PWM DC": 0})
    d_out.update({"IR Lamp 5 PWM DC": 0})
    d_out.update({"IR Lamp 6 PWM DC": 0})
    d_out.update({"IR Lamp 7 PWM DC": 0})
    d_out.update({"IR Lamp 8 PWM DC": 0})
    d_out.update({"IR Lamp 9 PWM DC": 0})
    d_out.update({"IR Lamp 10 PWM DC": 0})
    d_out.update({"IR Lamp 11 PWM DC": 0})
    d_out.update({"IR Lamp 12 PWM DC": 0})
    d_out.update({"IR Lamp 13 PWM DC": 0})
    d_out.update({"IR Lamp 14 PWM DC": 0})
    d_out.update({"IR Lamp 15 PWM DC": 0})
    d_out.update({"IR Lamp 16 PWM DC": 0})
    HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Shroud Duty Cycle', 0])
    HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Platen Duty Cycle', 0])


def is_error_in_list(error, error_in_list, error_list):
    for temp_error in error_list:
        if error["event"] == temp_error["event"] and error["item"] == temp_error["item"] and error['itemID'] == \
                temp_error['itemID']:
            error_in_list = True
    return error_in_list


def log_event(error, error_list_raw):
    pi = ProfileInstance.getInstance()
    error_list = error_list_raw[:]
    error_in_list = False
    error_in_list = is_error_in_list(error, error_in_list, error_list)
    if not error_in_list:
        pi.error_list.append(error)

    return error_list


def test_outside_tc(max_touch_temp, min_touch_temp, outside_thermo_couples, tc, temp_error_dict):
    pi = ProfileInstance.getInstance()
    try:
        if tc.Thermocouple in outside_thermo_couples:
            if tc.temp > max_touch_temp:
                error_detail = "TC # {} is above max_touch_temp ({}). Currently {}c".format(
                    tc.Thermocouple, max_touch_temp, tc.temp)
                error = {
                    "time": str(datetime.datetime.now()),
                    "event": "Human Touch Alarm: High Temperature",
                    "item": "Thermocouple",
                    "itemID": tc.Thermocouple,
                    "details": error_detail,
                    "actions": ["Log Event"]
                }
                log_event(error, pi.error_list)
                temp_error_dict[error['event']] = True
            # end of max touch test

            if tc.temp < min_touch_temp:
                error_detail = "TC # {} is below m_i_n__t_o_u_c_h__t_e_m_p ({}). Currently {}c".format(
                    tc.Thermocouple, min_touch_temp, tc.temp)
                error = {
                    "time": str(datetime.datetime.now()),
                    "event": "Human Touch Alarm: Low Temperature",
                    "item": "Thermocouple",
                    "itemID": tc.Thermocouple,
                    "details": error_detail,
                    "actions": ["Log Event"]
                }
                log_event(error, pi.error_list)
                temp_error_dict[error['event']] = True
            # end of min touch test
        # if of outside thermal test
    except Exception as e:
        Logging.logEvent("Event", "Missed Error",{
                             "message": "The Safety Check encountered an error while checking outside temperatures are safe. ({})".format(e),
                             "ProfileInstance": pi})

def test_if_tc_is_under_user_defined_min(tc, temp_error_dict, minHeatError):
    pi = ProfileInstance.getInstance()
    try:
        if tc.temp < minHeatError:
            error_detail = "TC # {} is below MIN_UUT_TEMP ({}). Currently {}c".format(
                tc.Thermocouple,
                minHeatError,
                tc.temp)
            error = {
                "time": str(datetime.datetime.now()),
                "event": "Product Saver Alarm: Low Temperature",
                "item": "Thermocouple",
                "itemID": tc.Thermocouple,
                "details": error_detail,
                "actions": ["Turned off LN flow", "Log Event"]
            }
            log_event(error, pi.error_list)
            temp_error_dict[error['event']] = True
    except Exception as e:
        Logging.logEvent("Event", "Missed Error",{
                             "message": "The Safety Check encountered an error while checking if under min user defined temperature. ({})".format(e),
                             "ProfileInstance": pi})

def test_if_tc_is_over_user_defined_max(tc, temp_error_dict, max_heat_error):
    pi = ProfileInstance.getInstance()
    try:
        if tc.temp > max_heat_error:
            error_detail = "TC # {} is above MAX_UUT_TEMP ({}). Currently {}c".format(
                tc.Thermocouple,
                max_heat_error,
                tc.temp)
            error = {
                "time": str(datetime.datetime.now()),
                "event": "Product Saver Alarm: High Temperature",
                "item": "Thermocouple",
                "itemID": tc.Thermocouple,
                "details": error_detail,
                "actions": ["Turned off heater", "Log Event"]
            }
            log_event(error, pi.error_list)
            temp_error_dict[error['event']] = True
    except Exception as e:
        Logging.logEvent("Event", "Missed Error",{
                             "message": "The Safety Check encountered an error while checking if over max user defined temperature. ({})".format(e),
                             "ProfileInstance": pi})



def log_over_heated_tc(max_operating_temperature, overheated_tc, tc, temp_error_dict):
    pi = ProfileInstance.getInstance()
    try:
        if tc.temp > max_operating_temperature:
            overheated_tc = True
            error_detail = "TC # {} is above MAX_OPERATING_TEMP ({}). Currently {}c".format(
                tc.Thermocouple, max_operating_temperature, tc.temp)
            error = {
                "time": str(datetime.datetime.now()),
                "event": "System Alarm: High Temperature",
                "item": "Thermocouple",
                "itemID": tc.Thermocouple,
                "details": error_detail,
                "actions": ["Turned off heater", "Log Event"]
            }
            log_event(error, pi.error_list)
            temp_error_dict[error['event']] = True

            enter_safe_mode("ERROR Heat was above max operating temperature ({})")

            release_hold()
    except Exception as e:
        Logging.logEvent("Event", "Missed Error",
                         {
                             "message": "The Safety Check encountered an error while checking if over max operational temperature. ({})".format(
                                 e),
                             "ProfileInstance": pi})
    return overheated_tc


def log_removed_tcs(hw):
    pi = ProfileInstance.getInstance()
    try:
        for tc in hw.thermocouples.recently_disconnected:
            error_log = {
                "time": str(datetime.datetime.now()),
                "event": "Thermocouple {} Disconnected".format(tc.Thermocouple),
                "item": "Thermocouple",
                "itemID": tc.Thermocouple,
                "details": "Thermocouple(s) lost: {}".format(
                    list(tc.Thermocouple for tc in hw.thermocouples.recently_disconnected)),
                "actions": ["Log Event"]
            }
            print("TC {} has been removed".format(tc.Thermocouple))
            print("the list length: {}".format(len(hw.thermocouples.recently_disconnected)))
            log_event(error_log, pi.error_list)
            print("After Event log")
            hw.thermocouples.recently_disconnected.remove(tc)
    except Exception as e:
        Logging.logEvent("Event", "Missed Error",
                         {"message": "The Safety Check encountered an error while checking for recently disconnected thermocouples. ({})".format(e),
                          "ProfileInstance": pi})


def log_hw_error(pi, item, error_details):

    error_log = {
        "time": str(datetime.datetime.now()),
        "event": "Hardware  Error",
        "item": item,
        "itemID": 0,
        "details": error_details,
        "actions": ["Log Event"]
    }
    enter_safe_mode(error_details)
    log_event(error_log, pi.error_list)
    pi.active_profile = False


def test_if_left_vacuum_while_in_active_profile(hw, pi, temp_error_dict):
    # TODO: operational_vacuum can't be updated if there isn't an active profile...this needs to change
    try:
        current_pressure = hw.pfeiffer_gauges.get_chamber_pressure()

        if current_pressure and current_pressure > 1e-4 and pi.active_profile:
            error_detail = "Chamber Pressure is above Operational Vacuum ({}) while in active profile".format(current_pressure)
            error = {
                "time": str(datetime.datetime.now()),
                "event": "Raised Pressure While Testing",
                "item": "Pressure",
                "itemID": 0,
                "details": error_detail,
                "actions": ["Log Event"]
            }
            log_event(error, pi.error_list)
            temp_error_dict[error['event']] = True
            error_mesg = "ERROR Pressure is above 10^- while in active profile. ({})".format(current_pressure)
            enter_safe_mode(error_mesg)
            release_hold()
        # end if vacuum in bad condition
    except Exception as e:
        Logging.logEvent("Event", "Missed Error",{
                             "message": "The Safety Check encountered an error while checking if above an operational vacuum while in active profile. ({})".format(e),
                             "ProfileInstance": pi})


def test_thermocouples_for_errors(MAX_OPERATING_TEMP, MAX_TOUCH_TEMP, MIN_TOUCH_TEMP, temp_error_dict):
    pi = ProfileInstance.getInstance()
    hw = HardwareStatusInstance.getInstance()
    overheated_tc = False
    for tc in hw.thermocouples.ValidTCs:
        # if there are any TC's higher than max temp
        overheated_tc = log_over_heated_tc(MAX_OPERATING_TEMP, overheated_tc, tc, temp_error_dict)

        if tc.userDefined and tc.zone != 0:
            test_if_tc_is_over_user_defined_max(tc, temp_error_dict,
                                                pi.zone_dict[tc.name].maxHeatError)

            test_if_tc_is_under_user_defined_min(tc, temp_error_dict,
                                                 pi.zone_dict[tc.name].minHeatError)
        # end of user test

        # Get the full list
        outside_thermo_couples = []
        test_outside_tc(MAX_TOUCH_TEMP, MIN_TOUCH_TEMP, outside_thermo_couples, tc, temp_error_dict)
    # End of TC for loop
    hw.overheated_tc = overheated_tc