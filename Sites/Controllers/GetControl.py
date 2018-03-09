import json
import time

from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance
from ThreadControls.ThreadCollectionInstance import ThreadCollectionInstance
import ThreadControls.ThreadHelperFunctions
import Collections.ProfileHelperFunctions as ProfileHelperFunctions

from Logging.Logging import Logging, insert_into_sql

def get_tvac_status():
    hw = HardwareStatusInstance.getInstance()
    pi = ProfileInstance.getInstance()
    out = {
        "recordData": pi.record_data,
        "OperationalVacuum": hw.operational_vacuum,
        "activeProfile": pi.active_profile,
        "vacuumWanted": pi.vacuum_wanted,
        "currentSetpoint": pi.current_setpoint,
        "inRamp": pi.in_ramp,
        "inHold": pi.in_hold,
        "inPause": False,
        'inCryoPumpRegen': hw.shi_cryopump.is_regen_active(),
        'CryoPressure': hw.pfeiffer_gauges.get_cryopump_pressure(),
        'ChamberPressure': hw.pfeiffer_gauges.get_chamber_pressure(),
        'RoughingPressure': hw.pfeiffer_gauges.get_roughpump_pressure(),
        "VacuumState": hw.vacuum_state,
        }
    if not pi.active_profile:
        out["inRamp"] = None
    return json.dumps(out)


def get_vacuum_state():
    return json.dumps({"VacuumState": HardwareStatusInstance.getInstance().vacuum_state})


def abort_regen_cycle():
    try:
        hw = HardwareStatusInstance.getInstance()
        if hw.shi_cryopump.is_regen_active():
            hw.shi_mcc_cmds.append(['Start_Regen', 0])
            return "{'result':'success'}"
        else:
            return "{'result':'Cryopump not generating so Can't abort regeneration cycle.'}"
    except Exception as e:
        return "{'error':'{}'}".format(e)


def do_regen_cycle():
    try:
        hw = HardwareStatusInstance.getInstance()
        if not hw.shi_cryopump.is_regen_active():
            hw.shi_mcc_cmds.append(['Start_Regen', 1])
            return "{'result':'success'}"
        else:
            return "{'result':'Cryopump not generating so Can't abort regeneration cycle.'}"
    except Exception as e:
        return "{'error':'{}'}".format(e)


def stop_recording_data():
    ProfileInstance.getInstance().record_data = False


def record_data():
    ProfileInstance.getInstance().record_data = True


def run_profile():
    # Does not allow the system to start a profile until the door is closed
    if not HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed:
        return "{'error':'{}'}".format("Door is open")

    # If the shourd heaters are on, turn them off when starting a profile
    HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Shroud Duty Cycle', 0])
    HardwareStatusInstance.getInstance().tdk_lambda_cmds.append(['Disable Shroud Output'])
    pi = ProfileInstance.getInstance()
    result = ProfileHelperFunctions.run_profile(pi,first_start = True)
    return result


def get_zone_temps():
    pi = ProfileInstance.getInstance()
    temps=dict(ZoneTemps=[])

    for i in range(1,10):
        zone = pi.zone_dict["zone{}".format(i)]
        if zone.active_zone_profile:
            # If it errors out, add a nan
            try:
                temps['ZoneTemps'].append(zone.getTemp())
            except AttributeError as e:
                temps['ZoneTemps'].append(float('nan'))

            try:
                temps['ZoneTemps'].append(zone.pid.SetPoint)
            except AttributeError as e:
                temps['ZoneTemps'].append(float('nan'))
        else:
            temps['ZoneTemps'].append(float('nan'))
            temps['ZoneTemps'].append(float('nan'))
    buff=json.dumps(temps)
    return buff


def get_pressure_gauges():
    gauges = HardwareStatusInstance.getInstance().pfeiffer_gauges
    resp = {'CryoPressure': gauges.get_cryopump_pressure(),
            'ChamberPressure': gauges.get_chamber_pressure(),
            'RoughingPressure': gauges.get_roughpump_pressure()}
    return json.dumps(resp)


def get_pc104_analog():
    pins = HardwareStatusInstance.getInstance().pc_104
    return '{"out":%s,"in":%s}' % (pins.analog_out.getJson(),
                                   pins.analog_in.getJson())


def get_pc104_switches():
    pins = HardwareStatusInstance.getInstance().pc_104
    return '{"in sw":%s,"sw wf":%s}' % (
        pins.digital_in.getJson_Switches(),
        pins.digital_in.getJson_Switches_WF())


def get_pc104_digital():
    pins = HardwareStatusInstance.getInstance().pc_104
    return '{"out":%s,"in bits":%s,"in sw":%s,"sw wf":%s}' % (
        pins.digital_out.getJson(),
        pins.digital_in.getJson_bits(),
        pins.digital_in.getJson_Switches(),
        pins.digital_in.getJson_Switches_WF()
    )


def get_cryopump_plots():
    return HardwareStatusInstance.getInstance().shi_cryopump.get_json_plots()


def get_cryopump_params():
    return HardwareStatusInstance.getInstance().shi_cryopump.getJson_Params()


def get_cryopump_status():
    return HardwareStatusInstance.getInstance().shi_cryopump.getJson_Status()


def get_event_list():
    # data unused
    Logging.debug_print(2, "Calling: Get Event List")
    event_list = ProfileInstance.getInstance().system_status_queue
    temp_event_list = dict(time=[],category=[],message=[])
    for i, event in enumerate(event_list):
        temp_event_list['time'].append(event['time'])
        temp_event_list['category'].append(event['category'])
        temp_event_list['message'].append(event['message'])

        event_list.pop(i)
    Logging.debug_print(2, "Events :" + str(event_list))

    return json.dumps(temp_event_list)


def get_shi_temps():
    return HardwareStatusInstance.getInstance().shi_cryopump.mcc_status.get_json_plots()


def hard_stop():
    hw = HardwareStatusInstance.getInstance()
    try:
        Logging.debug_print(1, "Hard stop has been called")
        d_out = hw.pc_104.digital_out
        ProfileInstance.getInstance().active_profile = False
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

        hw.tdk_lambda_cmds.append(['Disable All Output'])
        hw.tdk_lambda_cmds.append(['Platen Duty Cycle', 0])
        hw.tdk_lambda_cmds.append(['Shroud Duty Cycle', 0])
        Logging.logEvent("Event","Profile",
            {"message": "Profile Halted:",
            "ProfileInstance": ProfileInstance.getInstance()})
        return {'result':'success'}
    except Exception as e:
        return {'result':'{}'.format(e)}


def get_last_error():
    Logging.debug_print(2, "Calling: Get Last Err")  #Todo Change to logEvent()
    error_list = ProfileInstance.getInstance().error_list
    temp_error_list = dict(time=[],event=[],item=[],itemID=[],details=[],actions=[])
    for i, error in enumerate(error_list):
        temp_error_list['time'].append(error['time'])
        temp_error_list['event'].append(error['event'])
        temp_error_list['item'].append(error['item'])
        temp_error_list['itemID'].append(error['itemID'])
        temp_error_list['details'].append(error['details'])
        temp_error_list['actions'].append(error['actions'])

        error_list.pop(i)

    return json.dumps(temp_error_list)


def get_all_zone_data():
    pass
    # TODO: If this doesn't work, why is it here?
    # This doesn't work...
    # Logging.debugPrint(2, "Calling: getAllZoneData")  #Todo Change to logEvent()
    # profile_instance = ProfileInstance.getInstance()
    # zones = profile_instance.zoneProfiles.zoneDict
    # json = "{"
    # for zone in zones:
    #     print(zones[zone].getJson())
    # return "{'result':'success'}"


def stop_roughing_pump():
    try:
        profile = ProfileInstance.getInstance()
        if not profile.active_profile:
            pins = HardwareStatusInstance.getInstance().pc_104.digital_out
            pins.update({'RoughP GateValve': False})
            # wait here until the valve is closed
            time.sleep(5)
            pins.update({'RoughP Pwr Relay': False})
            # TODO: Fix type in PurgeGass (EVERYWHERE)
            pins.update({'RoughP PurgeGass': False})
            return "{'result':'success'}"
        else:
            return "{'result':'Not Changed: Active Profile Running.'}"
    except Exception as e:
        return "{'error':'{}'}".format(e)


def stop_cryopump():
    pi = ProfileInstance.getInstance()
    hw = HardwareStatusInstance.getInstance()
    sql_str = "UPDATE System_Status SET vacuum_wanted=0;"
    try:
        if not pi.active_profile:
            insert_into_sql(sql_str=sql_str)
            pi.vacuum_wanted = False
            hw.pc_104.digital_out.update({'CryoP GateValve': False})

            time.sleep(5)
            # TODO: Wait until gate is closed
            hw.shi_mcc_cmds.append(['Turn_CryoPumpOff'])
            hw.shi_compressor_cmds.append('off')
            return "{'result':'success'}"
        else:
            return "{'result':'Not Changed: Active Profile Running.'}"
    except Exception as e:
        Logging.debug_print(3, "sql: {}".format(sql_str))
        Logging.debug_print(1, "Error in ThreadCollection, holdThread: {}".format(str(e)))
        return "{'error':'{}'}".format(e)


def stop_cryopumping_chamber():
    pi = ProfileInstance.getInstance()
    hw = HardwareStatusInstance.getInstance()
    sql_str = "UPDATE System_Status SET vacuum_wanted=0;"
    try:
        if not pi.active_profile:
            insert_into_sql(sql_str=sql_str)
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            pi.vacuum_wanted = False
            return "{'result':'success'}"
        else:
            return "{'result':'Not Changed: Active Profile Running.'}"
    except Exception as e:
        Logging.debug_print(3, "sql: {}".format(sql_str))
        Logging.debug_print(1, "Error in ThreadCollection, holdThread: {}".format(str(e)))
        return "{'error':'{}'}".format(e)


def vacuum_not_needed():
    pi = ProfileInstance.getInstance()
    sql_str = "UPDATE System_Status SET vacuum_wanted=0;"
    try:
        if not pi.active_profile:
            insert_into_sql(sql_str=sql_str)

            pi.vacuum_wanted = False
            return "{'result':'success'}"
        else:
            return "{'result':'Not Changed: Active Profile Running.'}"
    except Exception as e:
        Logging.debug_print(3, "sql: {}".format(sql_str))
        Logging.debug_print(1, "Error in ThreadCollection, holdThread: {}".format(str(e)))
        return "{'error':'{}'}".format(e)


def un_hold_all_zones():
    try:

        ThreadControls.ThreadHelperFunctions.release_hold()
    except Exception as e:
        return "{'error':'{}'}".format(e)
    return "{'result':'success'}"


def resume_all_zones():
    try:
        thread_instance = ThreadCollectionInstance.getInstance()
        thread_instance.threadCollection.holdThread()
        return "{'result':'success'}"
    except Exception as e:
        return "{'error':'{}'}".format(e)


def hold_all_zones():
    try:
        thread_instance = ThreadCollectionInstance.getInstance()
        thread_instance.threadCollection.holdThread()
        return "{'result':'success'}"
    except Exception as e:
        return "{'error':'{}'}".format(e)


def get_all_thermocouple_data():
    Logging.debug_print(2, "Calling: getAllThermoCoupleData")
    hardware_status_instance = HardwareStatusInstance.getInstance()
    tc_json = hardware_status_instance.thermocouples.getJson('K')
    return tc_json


def put_under_vacuum():
    if HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed:
        sql_str = "UPDATE System_Status SET vacuum_wanted=1;"
        try:
            insert_into_sql(sql_str=sql_str)
            ProfileInstance.getInstance().vacuum_wanted = True
            return "{'result':'success'}"
        except Exception as e:
            Logging.debug_print(3, "sql: {}".format(sql_str))
            Logging.debug_print(1, "Error in ThreadCollection, holdThread: {}".format(str(e)))
            return "{'error':'{}'}".format(e)
    else:
        return "{'result':'Error: Door is open'}"

def chamber_door_status():
    try:
        chamber_closed = HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed

        return "{'result':'" + str(chamber_closed) + "'}"
    except Exception as e:
        return "{'error':'{}'}".format(e)

def get_system_power():
    message = {
        "pfeiffer_gauge": HardwareStatusInstance.getInstance().pfeiffer_gauge_power,
        "shi_compressor": HardwareStatusInstance.getInstance().shi_compressor_power,
        "shi_mcc": HardwareStatusInstance.getInstance().shi_mcc_power,
        "tdk_lambda": HardwareStatusInstance.getInstance().tdk_lambda_power,
        "thermocouple": HardwareStatusInstance.getInstance().thermocouple_power,
        "pc_104": HardwareStatusInstance.getInstance().pc_104_power,
        }

    return json.dumps(message)

def get_interlock_status():

    message = {
        "door_interlock":  HardwareStatusInstance.getInstance().pc_104.digital_in.chamber_closed ,
        "overTemp" : not HardwareStatusInstance.getInstance().overheated_tc,
        "overPressure": HardwareStatusInstance.getInstance().operational_vacuum,
        "roughing_pump_valve_open": HardwareStatusInstance.getInstance().pc_104.digital_out.getVal('RoughP GateValve'),
        "roughing_pump_valve_closed": not HardwareStatusInstance.getInstance().pc_104.digital_out.getVal('RoughP GateValve'),
        "thermocouple": HardwareStatusInstance.getInstance().thermocouple_power,
        "pfeiffer_gauge": HardwareStatusInstance.getInstance().pfeiffer_gauge_power,
        "ln2_shroud_open": HardwareStatusInstance.getInstance().pc_104.digital_in.getVal('LN2_S_Sol_Open'),
        "ln2_shroud_closed": HardwareStatusInstance.getInstance().pc_104.digital_in.getVal('LN2_S_Sol_Closed'),
        "ln2_platen_open": HardwareStatusInstance.getInstance().pc_104.digital_in.getVal('LN2_P_Sol_Open'),
        "ln2_platen_closed": HardwareStatusInstance.getInstance().pc_104.digital_in.getVal('LN2_P_Sol_Closed'),
        "cryopump_valve_open": HardwareStatusInstance.getInstance().pc_104.digital_in.getVal('CryoP_GV_Open'),
        "cryopump_valve_closed": HardwareStatusInstance.getInstance().pc_104.digital_in.getVal('CryoP_GV_Closed'),
        "tdk_lambda": HardwareStatusInstance.getInstance().tdk_lambda_power,
        "pc_104": HardwareStatusInstance.getInstance().pc_104_power,        
        "shi_compressor": HardwareStatusInstance.getInstance().shi_compressor_power,
        "shi_mcc": HardwareStatusInstance.getInstance().shi_mcc_power,
    }
    return json.dumps(message)

def get_sql_data():
    sql_list = HardwareStatusInstance.getInstance().sql_list[:]
    HardwareStatusInstance.getInstance().sql_list = []
    return {"sql_data":sql_list}
