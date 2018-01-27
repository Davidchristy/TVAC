import json
import time

from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance
from ThreadControls.ThreadCollectionInstance import ThreadCollectionInstance

from Logging.Logging import Logging
from Logging.MySql import MySQlConnect

def get_tvac_status():
    hw = HardwareStatusInstance.getInstance()
    out = {
        "recordData": ProfileInstance.getInstance().record_data,
        "OperationalVacuum": HardwareStatusInstance.getInstance().operational_vacuum,
        "activeProfile": ProfileInstance.getInstance().activeProfile,
        "vacuumWanted": ProfileInstance.getInstance().vacuumWanted,
        "currentSetpoint": ProfileInstance.getInstance().currentSetpoint,
        "inRamp": ProfileInstance.getInstance().inRamp,
        "inHold": ProfileInstance.getInstance().inHold,
        "inPause": ProfileInstance.getInstance().inPause,
        'inCryoPumpRegen': hw.shi_cryopump.is_regen_active(),
        'CryoPressure': hw.pfeiffer_gauges.get_cryopump_pressure(),
        'ChamberPressure': hw.pfeiffer_gauges.get_chamber_pressure(),
        'RoughingPressure': hw.pfeiffer_gauges.get_roughpump_pressure(),
        "VacuumState": HardwareStatusInstance.getInstance().vacuum_state,
        }
    if not ProfileInstance.getInstance().activeProfile:
        out["inRamp"] = None
    return json.dumps(out)


def get_vacuum_state():
    return json.dumps({"VacuumState": HardwareStatusInstance.getInstance().vacuum_state})


def abort_regen_cycle():
    try:
        hw = HardwareStatusInstance.getInstance()
        if hw.shi_cryopump.is_regen_active():
            hw.Shi_MCC_Cmds.append(['Start_Regen', 0])
            return "{'result':'success'}"
        else:
            return "{'result':'Cryopump not generating so Can't abort regeneration cycle.'}"
    except Exception as e:
        return "{'error':'{}'}".format(e)


def do_regen_cycle():
    try:
        hw = HardwareStatusInstance.getInstance()
        if not hw.shi_cryopump.is_regen_active():
            hw.Shi_MCC_Cmds.append(['Start_Regen', 1])
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
    HardwareStatusInstance.getInstance().tdk_lambda__cmds.append(['Shroud Duty Cycle', 0])
    HardwareStatusInstance.getInstance().tdk_lambda__cmds.append(['Disable Shroud Output'])
    thread_instance = ThreadCollectionInstance.getInstance()
    result = thread_instance.threadCollection.run_profile()
    return result


def get_zone_temps():

    temps=dict(ZoneTemps=[])

    for i in range(1,10):
        str_zone="zone"+str(i)
        try:
            temps['ZoneTemps'].append(ProfileInstance.getInstance().zoneProfiles.getZone(str_zone).getTemp())
        #TODO:Change these to the Exception that might happen here.
        except Exception as e:
            temps['ZoneTemps'].append(float('nan'))
        try:
            temps['ZoneTemps'].append(ThreadCollectionInstance.getInstance().threadCollection.dutyCycleThread.zones["zone{}".format(i)].pid.SetPoint)
        except Exception as e:
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
    Logging.debugPrint(2,"Calling: Get Event List")
    event_list = ProfileInstance.getInstance().systemStatusQueue
    temp_event_list = dict(time=[],category=[],message=[])
    for i, event in enumerate(event_list):
        temp_event_list['time'].append(event['time'])
        temp_event_list['category'].append(event['category'])
        temp_event_list['message'].append(event['message'])

        event_list.pop(i)
    Logging.debugPrint(2, "Events :" + str(event_list))

    return json.dumps(temp_event_list)


def get_shi_temps():
    return HardwareStatusInstance.getInstance().shi_cryopump.mcc_status.get_json_plots()


def hard_stop():
    try:
        Logging.debugPrint(1,"Hard stop has been called")
        d_out = HardwareStatusInstance.getInstance().pc_104.digital_out
        ProfileInstance.getInstance().activeProfile = False
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

        HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Disable All Output'])
        HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Platen Duty Cycle', 0])
        HardwareStatusInstance.getInstance().TdkLambda_Cmds.append(['Shroud Duty Cycle', 0])
        Logging.logEvent("Event","Profile",
            {"message": "Profile Halted:",
            "ProfileInstance": ProfileInstance.getInstance()})
        return {'result':'success'}
    except Exception as e:
        return {'result':'{}'.format(e)}


def get_last_error():
    Logging.debugPrint(2,"Calling: Get Last Err")  #Todo Change to logEvent()
    error_list = ThreadCollectionInstance.getInstance().threadCollection.safetyThread.errorList
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
        if not profile.activeProfile:
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
    sql = "UPDATE System_Status SET vacuum_wanted=0;"
    try:
        profile = ProfileInstance.getInstance()
        if not profile.activeProfile:
            profile.vacuumWanted = False
            mysql = MySQlConnect()
            mysql.cur.execute(sql)
            mysql.conn.commit()
            hw = HardwareStatusInstance.getInstance()
            hw.pc_104.digital_out.update({'CryoP GateValve': False})
            time.sleep(5)
            # TODO: Wait until gate is closed
            hw.shi_mcc_cmds.append(['Turn_CryoPumpOff'])
            hw.shi_compressor_cmds.append('off')
            return "{'result':'success'}"
        else:
            return "{'result':'Not Changed: Active Profile Running.'}"
    except Exception as e:
        Logging.debugPrint(3,"sql: {}".format(sql))
        Logging.debugPrint(1, "Error in ThreadCollection, holdThread: {}".format(str(e)))
        return "{'error':'{}'}".format(e)


def stop_cryopumping_chamber():
    sql = "UPDATE System_Status SET vacuum_wanted=0;"
    try:
        profile = ProfileInstance.getInstance()
        if not profile.activeProfile:
            mysql = MySQlConnect()
            mysql.cur.execute(sql)
            mysql.conn.commit()

            HardwareStatusInstance.getInstance().pc_104.digital_out.update({'CryoP GateValve': False})
            profile.vacuumWanted = False
            return "{'result':'success'}"
        else:
            return "{'result':'Not Changed: Active Profile Running.'}"
    except Exception as e:
        Logging.debugPrint(3,"sql: {}".format(sql))
        Logging.debugPrint(1, "Error in ThreadCollection, holdThread: {}".format(str(e)))
        return "{'error':'{}'}".format(e)


def vacuum_not_needed():
    sql = "UPDATE System_Status SET vacuum_wanted=0;"
    try:
        profile = ProfileInstance.getInstance()
        if not profile.activeProfile:
            mysql = MySQlConnect()
            mysql.cur.execute(sql)
            mysql.conn.commit()
            profile.vacuumWanted = False
            return "{'result':'success'}"
        else:
            return "{'result':'Not Changed: Active Profile Running.'}"
    except Exception as e:
        Logging.debugPrint(3,"sql: {}".format(sql))
        Logging.debugPrint(1, "Error in ThreadCollection, holdThread: {}".format(str(e)))
        return "{'error':'{}'}".format(e)


def un_hold_all_zones():
    try:
        thread_instance = ThreadCollectionInstance.getInstance()
        thread_instance.threadCollection.holdThread()
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


def pause_all_zones():
    try:
        thread_instance = ThreadCollectionInstance.getInstance()
        thread_instance.threadCollection.holdThread()
        return "{'result':'success'}"
    except Exception as e:
        return "{'error':'{}'}".format(str(e))


def hold_all_zones():
    try:
        thread_instance = ThreadCollectionInstance.getInstance()
        thread_instance.threadCollection.holdThread()
        return "{'result':'success'}"
    except Exception as e:
        return "{'error':'{}'}".format(e)


def get_all_thermocouple_data():
    Logging.debugPrint(2, "Calling: getAllThermoCoupleData")
    hardware_status_instance = HardwareStatusInstance.getInstance()
    tc_json = hardware_status_instance.thermocouples.getJson('K')
    return tc_json


def put_under_vacuum():
    sql = "UPDATE System_Status SET vacuum_wanted=1;"
    try:
        mysql = MySQlConnect()
        mysql.cur.execute(sql)
        mysql.conn.commit()
        ProfileInstance.getInstance().vacuumWanted = True
        return "{'result':'success'}"
    except Exception as e:
        Logging.debugPrint(3, "sql: {}".format(sql))
        Logging.debugPrint(1, "Error in ThreadCollection, holdThread: {}".format(str(e)))
        return "{'error':'{}'}".format(e)

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


