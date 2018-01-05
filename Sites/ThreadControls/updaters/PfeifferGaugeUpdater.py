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

from Logging.MySql import MySQlConnect
from Logging.Logging import Logging


class PfeifferGaugeUpdater(Thread):
    def __init__(self, parent=None, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self.parent = parent

        self.zoneProfiles = ProfileInstance.getInstance().zoneProfiles
        self.Pgauge = PfeifferGauge()
        self.hw = HardwareStatusInstance.getInstance()
        self.gauges = self.hw.pfeiffer_gauges
        self.pressure_read_peroid = 0.5  # 0.5s loop period
        self.param_period = 5  # 5 second period

    def logPressureData(self):
        coloums = "( profile_I_ID, guage, pressure, time )"
        values  = "( \"{}\",{},{},\"{}\" ),\n".format(self.zoneProfiles.profileUUID,
                                               self.gauges.get_cryopump_address(),
                                               self.gauges.get_cryopump_pressure(),
                                               datetime.datetime.fromtimestamp(time.time()))
        values += "( \"{}\",{},{},\"{}\" ),\n".format(self.zoneProfiles.profileUUID,
                                               self.gauges.get_chamber_address(),
                                               self.gauges.get_chamber_pressure(),
                                               datetime.datetime.fromtimestamp(time.time()))
        values += "( \"{}\",{},{},\"{}\" )".format(self.zoneProfiles.profileUUID,
                                            self.gauges.get_roughpump_address(),
                                            self.gauges.get_roughpump_pressure(),
                                            datetime.datetime.fromtimestamp(time.time()))
        sql = "INSERT INTO tvac.Pressure {} VALUES {};".format(coloums, values)
        mysql = MySQlConnect()
        try:
            mysql.cur.execute(sql)
            mysql.conn.commit()
        except Exception as e:
            print(sql)
            Logging.debugPrint(1, "Error in logPressureData, PfeifferGaugeUpdater: {}".format(str(e)))
            if Logging.debug:
                raise e

    def run(self):
        '''
        '''
        # used for testing
        first = True
        while True:
            # While true to restart the thread if it errors out
            try:
                # Thread "Start up" stuff goes here
                Logging.logEvent("Debug", "Status Update",
                                {"message": "Starting Pfeiffer Guage Updater Thread",
                                 "level": 2})

                if os.name == "posix":
                    userName = os.environ['LOGNAME']
                else:
                    userName = "user"
                # userName = 'root'
                if "root" in userName:
                    self.read_all_params()
                next_pressure_read_time = time.time()
                next_param_read_time = time.time()
                while True:
                    next_pressure_read_time += self.pressure_read_peroid
                    if "root" in userName:
                        try:
                            self.gauges.update([{'addr': 1, 'Pressure': self.Pgauge.GetPressure(1)},
                                                {'addr': 2, 'Pressure': self.Pgauge.GetPressure(2)},
                                                {'addr': 3, 'Pressure': self.Pgauge.GetPressure(3)}])
                            Logging.logEvent("Debug", "Status Update",
                                             {"message": "Reading and writing with PfeifferGaugeUpdater.\n"
                                                         "Cryopump: {:f}; Chamber: {:f}; RoughPump: {:f}\n"
                                                         "".format(self.gauges.get_cryopump_pressure(),
                                                                   self.gauges.get_chamber_pressure(),
                                                                   self.gauges.get_roughpump_pressure()),
                                              "level": 4})
                            if time.time() > next_param_read_time:
                                self.gauges.update([{'addr': 1, 'error': self.Pgauge.GetError(1),
                                                                'cc on': self.Pgauge.GetCCstate(1)},
                                                    {'addr': 2, 'error': self.Pgauge.GetError(2),
                                                                'cc on': self.Pgauge.GetCCstate(2)},
                                                    {'addr': 3, 'error': self.Pgauge.GetError(3)}])
                                if __name__ != '__main__':
                                    if ProfileInstance.getInstance().record_data:
                                        self.logPressureData()
                                next_param_read_time += self.param_period
                        except ValueError as err:
                            exc_type, exc_obj, exc_tb = sys.exc_info()
                            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                            Logging.logEvent("Error", 'Error in PfeifferGaugeUpdater reading values: "%s"' % err,
                                             {"type": exc_type,
                                              "filename": fname,
                                              "line": exc_tb.tb_lineno,
                                              "thread": "PfeifferGaugeUpdater"
                                              })
                    else:
                        Logging.logEvent("Debug", "Status Update",
                                         {"message": "Test run of Pfeiffer Guages loop",
                                          "level": 4})
                        if first:
                            # TODO: Test the system at differnt starting pressures, it could restart at any point
                            # What happens when pressure in roughing  is more than cryo?
                            self.gauges.update([{'addr': 1, 'Pressure': 1000},
                                                {'addr': 2, 'Pressure': 0.001},
                                                {'addr': 3, 'Pressure': 999}])
                            first = False
                            goingUp = False
                        else:
                            if True or self.gauges.get_chamber_pressure() > 0.0000001 and not goingUp:
                                self.gauges.update([{'addr': 1, 'Pressure': self.gauges.get_cryopump_pressure()/2.5},
                                                             {'addr': 2, 'Pressure': self.gauges.get_chamber_pressure()/5},
                                                             {'addr': 3, 'Pressure': self.gauges.get_roughpump_pressure()/3}])
                            else:
                                goingUp = True
                                self.gauges.update([{'addr': 1, 'Pressure': self.gauges.get_cryopump_pressure()*2.5},
                                                             {'addr': 2, 'Pressure': self.gauges.get_chamber_pressure()*5},
                                                             {'addr': 3, 'Pressure': self.gauges.get_roughpump_pressure()*3}])
                        # Just to see the screen for longer
                        time.sleep(5)

                    Logging.logEvent("Debug", "Status Update",
                             {"message": "Current Pressure in Chamber is {}".format(self.gauges.get_chamber_pressure()),
                              "level": 4})
                    currentTime = time.time()
                    if currentTime < next_pressure_read_time:
                        time.sleep(next_pressure_read_time - currentTime)

            except Exception as e:
                # FileCreation.pushFile("Error",self.zoneUUID,'{"errorMessage":"%s"}'%(e))
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
                if Logging.debug:
                    raise e
                time.sleep(4)

    def read_all_params(self):
        paramslist = [{'addr': 1,
                       'Model Name': self.Pgauge.GetModelName(1),
                       'Software Vir': self.Pgauge.GetSofwareV(1),
                       'CC sw mode': self.Pgauge.GetSwMode(1),
                       'Pressure SP 1': self.Pgauge.GetSwPressure(1, True),
                       'Pressure SP 2': self.Pgauge.GetSwPressure(1, False),
                       'Pirani Correction': self.Pgauge.GetCorrPir(1),
                       'CC Correction': self.Pgauge.GetCorrCC(1)},
                      {'addr': 2,
                       'Model Name': self.Pgauge.GetModelName(2),
                       'Software Vir': self.Pgauge.GetSofwareV(2),
                       'CC sw mode': self.Pgauge.GetSwMode(2),
                       'Pressure SP 1': self.Pgauge.GetSwPressure(2, True),
                       'Pressure SP 2': self.Pgauge.GetSwPressure(2, False),
                       'Pirani Correction': self.Pgauge.GetCorrPir(2),
                       'CC Correction': self.Pgauge.GetCorrCC(2)},
                      {'addr': 3,
                       'Model Name': self.Pgauge.GetModelName(3),
                       'Software Vir': self.Pgauge.GetSofwareV(3),
                       'Pressure SP 1': self.Pgauge.GetSwPressure(3, True),
                       'Pressure SP 2': self.Pgauge.GetSwPressure(3, False),
                       'Pirani Correction': self.Pgauge.GetCorrPir(3)}]
        self.gauges.update(paramslist)

if __name__ == '__main__':
    # adding debug info
    if(len(sys.argv)>1):
        for arg in sys.argv:
            if arg.startswith("-v"):
                Logging.verbose = arg.count("v")
    Logging.logEvent("Debug","Status Update",
        {"message": "Debug on: Level {}".format(Logging.verbose),
         "level":1})
    thread = PfeifferGaugeUpdater()
    thread.daemon = True
    thread.start()

    p = HardwareStatusInstance.getInstance().PfeifferGuages
    while True:
        time.sleep(5)
        print(p.getJson())
