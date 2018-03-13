#!/usr/bin/env python3.5
import datetime
import os
import sys
import time
from threading import Thread

from ThreadControls.SafetyCheckHelperFunctions import log_hw_error
from ThreadControls.SafetyCheckHelperFunctions import log_event
from ThreadControls.helperFunctions.safe_mode import enter_safe_mode

if __name__ == '__main__':
    sys.path.insert(0, os.getcwd())

from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance
from Hardware_Drivers.PfeifferGauge import PfeifferGauge


from Logging.Logging import Logging, insert_into_sql


def log_pressure_data():
    pi = ProfileInstance.getInstance()
    hw = HardwareStatusInstance.getInstance()
    coloums = "( profile_I_ID, guage, pressure, time )"
    values  = "( \"{}\",{},{},\"{}\" ),\n".format(pi.profile_uuid,
                                                hw.pfeiffer_gauges.get_cryopump_address(),
                                                hw.pfeiffer_gauges.get_cryopump_pressure(),
                                                datetime.datetime.fromtimestamp(time.time()))
    values += "( \"{}\",{},{},\"{}\" ),\n".format(pi.profile_uuid,
                                                hw.pfeiffer_gauges.get_chamber_address(),
                                                hw.pfeiffer_gauges.get_chamber_pressure(),
                                                datetime.datetime.fromtimestamp(time.time()))
    values += "( \"{}\",{},{},\"{}\" )".format(pi.profile_uuid,
                                               hw.pfeiffer_gauges.get_roughpump_address(),
                                               hw.pfeiffer_gauges.get_roughpump_pressure(),
                                        datetime.datetime.fromtimestamp(time.time()))
    sql_str = "INSERT INTO tvac.Pressure {} VALUES {};".format(coloums, values)
    insert_into_sql(sql_str=sql_str)


def initialize_pressure_gauges(hw, pressure_gauge):
    pi = ProfileInstance.getInstance()
    # Thread "Start up" stuff goes here
    Logging.logEvent("Debug", "Status Update",
                     {"message": "Starting Pfeiffer Guage Updater Thread",
                      "level": 2})
    try:
        params_list = [{'addr': 1,
                       'Model Name': pressure_gauge.GetModelName(1),
                       'Software Vir': pressure_gauge.GetSofwareV(1),
                       'CC sw mode': pressure_gauge.GetSwMode(1),
                       'Pressure SP 1': pressure_gauge.GetSwPressure(1, True),
                       'Pressure SP 2': pressure_gauge.GetSwPressure(1, False),
                       'Pirani Correction': pressure_gauge.GetCorrPir(1),
                       'CC Correction': pressure_gauge.GetCorrCC(1)},
                      {'addr': 2,
                       'Model Name': pressure_gauge.GetModelName(2),
                       'Software Vir': pressure_gauge.GetSofwareV(2),
                       'CC sw mode': pressure_gauge.GetSwMode(2),
                       'Pressure SP 1': pressure_gauge.GetSwPressure(2, True),
                       'Pressure SP 2': pressure_gauge.GetSwPressure(2, False),
                       'Pirani Correction': pressure_gauge.GetCorrPir(2),
                       'CC Correction': pressure_gauge.GetCorrCC(2)},
                      {'addr': 3,
                       'Model Name': pressure_gauge.GetModelName(3),
                       'Software Vir': pressure_gauge.GetSofwareV(3),
                       'Pressure SP 1': pressure_gauge.GetSwPressure(3, True),
                       'Pressure SP 2': pressure_gauge.GetSwPressure(3, False),
                       'Pirani Correction': pressure_gauge.GetCorrPir(3)}]
        hw.pfeiffer_gauges.update(params_list)
    except RuntimeError as e:
        item = "Pressure Gauge"
        error_details = "ERROR: {}: There has been an error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)

    except TimeoutError as e:
        hw.pfeiffer_gauge_power = False
        item = "Pressure Gauge"
        error_details = "ERROR: {}: There has been a Timeout error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
    else:
        hw.pfeiffer_gauge_power = True

    return time.time()


def pressure_update(hw, pi, next_param_read_time, param_period, pfeiffer_gauge):
    try:
        # Every update, get the pressure of the three gauges
        hw.pfeiffer_gauges.update([{'addr': 1, 'Pressure': pfeiffer_gauge.GetPressure(1)},
                                   {'addr': 2, 'Pressure': pfeiffer_gauge.GetPressure(2)},
                                   {'addr': 3, 'Pressure': pfeiffer_gauge.GetPressure(3)}])
        if time.time() < next_param_read_time:
            return next_param_read_time
        next_param_read_time += param_period

        hw.pfeiffer_gauges.update([
            {
                'addr': 1,
                'error': pfeiffer_gauge.GetError(1),
                'cc on': pfeiffer_gauge.GetCCstate(1)
            }, {
                'addr': 2,
                'error': pfeiffer_gauge.GetError(2),
                'cc on': pfeiffer_gauge.GetCCstate(2)
            }, {
                'addr': 3,
                'error': pfeiffer_gauge.GetError(3)
            }])
        Logging.logEvent("Debug", "Status Update",
                         {"message": "Reading and writing with PfeifferGaugeUpdater.\n\t"
                                     "Cryopump: {:f}; Chamber: {:f}; RoughPump: {:f}"
                         .format(hw.pfeiffer_gauges.get_cryopump_pressure(),
                                 hw.pfeiffer_gauges.get_chamber_pressure(),
                                 hw.pfeiffer_gauges.get_roughpump_pressure()),
                          "level": 3})

        if pi.record_data:
            log_pressure_data()

        Logging.logEvent("Debug", "Status Update",
                         {"message": "Current Pressure in Chamber is {}".format(
                             hw.pfeiffer_gauges.get_chamber_pressure()),
                             "level": 4})
    except RuntimeError as e:
        item = "Pressure Gauge"
        error_details = "ERROR: {}: There has been an error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)

    except TimeoutError as e:
        hw.pfeiffer_gauge_power = False
        item = "Pressure Gauge"
        error_details = "ERROR: {}: There has been a Timeout error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
    else:
        hw.pfeiffer_gauge_power = True

    return next_param_read_time


class PfeifferGaugeUpdater(Thread):
    def __init__(self, parent=None, group=None, target=None, name=None,
                 args=(), kwargs=None):
        Thread.__init__(self, group=group, target=target, name="PfeifferGaugeUpdater")
        self.args = args
        self.kwargs = kwargs

        self.pfeiffer_gauge = PfeifferGauge()
        self.pressure_read_period = 0.5  # 0.5s loop period
        self.param_period = 5  # 5 second period


    def run(self):
        hw = HardwareStatusInstance.getInstance()
        pi = ProfileInstance.getInstance()
        while True:
            # While true to restart the thread if it errors out
            try:

                next_param_read_time = initialize_pressure_gauges(hw, self.pfeiffer_gauge)

                while True:
                    next_param_read_time = pressure_update(hw, pi, next_param_read_time, self.param_period, self.pfeiffer_gauge)
                    time.sleep(self.pressure_read_period)
                    # self.number_continuous_errors = 0
                # End inner while True
            # End try
            except Exception as e:
                error_details = "Unknown Pressure Gauge Error: ({})".format(e)
                raise e
                error_log = {
                    "time": str(datetime.datetime.now()),
                    "event": "P",
                    "item": "Unknown Hardware Error",
                    "itemID": 0,
                    "details": error_details,
                    "actions": ["Log Event"]
                }
                enter_safe_mode(pi, error_details)
                log_event(error_log, pi.error_list)
                pi.active_profile = False

                # Sleep to let system "cool down" after error
                time.sleep(4)
            #end Except
        #end outer while true



