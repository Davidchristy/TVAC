#!/usr/bin/env python3.5
import datetime
import os
import sys
import time
from threading import Thread

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


def read_all_params(hw, pressure_gauge):
    paramslist = [{'addr': 1,
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
    hw.pfeiffer_gauges.update(paramslist)


class PfeifferGaugeUpdater(Thread):
    def __init__(self, parent=None, group=None, target=None, name=None,
                 args=(), kwargs=None):
        Thread.__init__(self, group=group, target=target, name="PfeifferGaugeUpdater")
        self.args = args
        self.kwargs = kwargs

        self.Pgauge = PfeifferGauge()
        self.pressure_read_peroid = 0.5  # 0.5s loop period
        self.param_period = 5  # 5 second period

        self.number_continuous_errors = 0
        self.MAX_NUMBER_OF_ERRORS = 1

        # sleep time in seconds
        self.sleep_time = .1

    def run(self):
        hw = HardwareStatusInstance.getInstance()
        pi = ProfileInstance.getInstance()
        while True:
            # While true to restart the thread if it errors out
            try:
                # Thread "Start up" stuff goes here
                Logging.logEvent("Debug", "Status Update",
                                {"message": "Starting Pfeiffer Guage Updater Thread",
                                 "level": 2})

                read_all_params(hw, self.Pgauge)
                next_param_read_time = time.time()
                while True:
                    hw.pfeiffer_gauges.update([{'addr': 1, 'Pressure': self.Pgauge.GetPressure(1)},
                                        {'addr': 2, 'Pressure': self.Pgauge.GetPressure(2)},
                                        {'addr': 3, 'Pressure': self.Pgauge.GetPressure(3)}])
                    # end test else
                    if time.time() > next_param_read_time:
                        hw.pfeiffer_gauges.update([{'addr': 1, 'error': self.Pgauge.GetError(1),
                                             'cc on': self.Pgauge.GetCCstate(1)},
                                            {'addr': 2, 'error': self.Pgauge.GetError(2),
                                             'cc on': self.Pgauge.GetCCstate(2)},
                                            {'addr': 3, 'error': self.Pgauge.GetError(3)}])
                        Logging.logEvent("Debug", "Status Update",
                                         {"message": "Reading and writing with PfeifferGaugeUpdater.\n"
                                                     "Cryopump: {:f}; Chamber: {:f}; RoughPump: {:f}"
                                                     "".format(hw.pfeiffer_gauges.get_cryopump_pressure(),
                                                               hw.pfeiffer_gauges.get_chamber_pressure(),
                                                               hw.pfeiffer_gauges.get_roughpump_pressure()),
                                          "level": 3})

                        if pi.record_data:
                            log_pressure_data()
                        next_param_read_time += self.param_period

                        Logging.logEvent("Debug", "Status Update",
                                 {"message": "Current Pressure in Chamber is {}".format(hw.pfeiffer_gauges.get_chamber_pressure()),
                                  "level": 4})

                    time.sleep(self.sleep_time)

                    hw.pfeiffer_gauge_power = True
                    self.number_continuous_errors = 0
                # End inner while True
            # End try
            except Exception as e:
                self.number_continuous_errors += 1
                if self.number_continuous_errors >= self.MAX_NUMBER_OF_ERRORS:
                    hw.pfeiffer_gauge_power = False
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                Logging.logEvent("Error", "Pfeiffer Interface Thread",
                                 {"type": exc_type,
                                  "filename": fname,
                                  "line": exc_tb.tb_lineno,
                                  "thread": "PfeifferGaugeUpdater"
                                  })
                Logging.logEvent("Debug", "Status Update",
                                 {"message": "There was a {} error in PfeifferGaugeUpdater. File: {}:{}\n{}".format(
                                     exc_type, fname, exc_tb.tb_lineno, e),
                                  "level": 1})
                # Sleep to let system "cool down" afte error
                time.sleep(4)
            #end Except
        #end outer while true
    # end run()


