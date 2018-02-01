#!/usr/bin/env python3.5
from threading import Thread
import time
import datetime
import os
import sys

if __name__ == '__main__':
    sys.path.insert(0, os.getcwd())

from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance
from Hardware_Drivers.Tdk_lamda_Genesys import Tdk_lambda_Genesys

from Logging.MySql import MySQlConnect
from Logging.Logging import Logging


class TdkLambdaUpdater(Thread):
    def __init__(self, parent=None, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        Thread.__init__(self, group=group, target=target, name=name)
        self.args = args
        self.kwargs = kwargs
        self.parent = parent

        self.pwr_supply = Tdk_lambda_Genesys()
        self.zoneProfiles = ProfileInstance.getInstance().zoneProfiles
        self.hw = HardwareStatusInstance.getInstance()
        self.ps_read_peroid = 4.0  # 0.5s loop period

    # def logVoltagesData(self):
      # TODO: delete or update DB to hold this
        # coloums = "( profile_I_ID, guage, pressure, time )"
        # values  = "( \"{}\",{},{},\"{}\" ),\n".format(self.zoneProfiles.profileUUID,
        #                                        self.gauges.get_cryopump_address(),
        #                                        self.gauges.get_cryopump_pressure(),
        #                                        datetime.datetime.fromtimestamp(time.time()))
        # values += "( \"{}\",{},{},\"{}\" ),\n".format(self.zoneProfiles.profileUUID,
        #                                        self.gauges.get_chamber_address(),
        #                                        self.gauges.get_chamber_pressure(),
        #                                        datetime.datetime.fromtimestamp(time.time()))
        # values += "( \"{}\",{},{},\"{}\" )".format(self.zoneProfiles.profileUUID,
        #                                     self.gauges.get_roughpump_address(),
        #                                     self.gauges.get_roughpump_pressure(),
        #                                     datetime.datetime.fromtimestamp(time.time()))
        # sql = "INSERT INTO tvac.Pressure {} VALUES {};".format(coloums, values)
        # # print(sql)
        # mysql = MySQlConnect()
        # try:
        #     mysql.cur.execute(sql)
        #     mysql.conn.commit()
        # except Exception as e:
        #     raise e
        #     #return e

    def run(self):
        '''
        '''
        if os.name == 'posix':
            userName = os.environ['LOGNAME']
        else:
            userName = "User"
        while True:
            # While true to restart the thread if it errors out
            try:
                # Thread "Start up" stuff goes here
                Logging.logEvent("Debug", "Status Update",
                                {"message": "TDK Lambda Genesys Control Stub Thread",
                                 "level": 2})

                if "root" in userName:
                    self.pwr_supply.open_port()
                    update_power_supplies = [{'addr': self.hw.tdk_lambda_ps.get_platen_left_addr()},
                                             {'addr': self.hw.tdk_lambda_ps.get_platen_right_addr()},
                                             {'addr': self.hw.tdk_lambda_ps.get_shroud_left_addr()},
                                             {'addr': self.hw.tdk_lambda_ps.get_shroud_right_addr()}]
                    for ps in update_power_supplies:
                        self.pwr_supply.set_addr(ps['addr'])
                        ps.update(self.pwr_supply.get_out())
                        if not self.hw.operation_vacuum:
                            self.pwr_supply.set_out_off()
                        ps.update(self.pwr_supply.get_idn())
                        ps.update(self.pwr_supply.get_rev())
                        ps.update(self.pwr_supply.get_sn())
                        ps.update(self.pwr_supply.get_date())
                        ps.update(self.pwr_supply.get_ast())
                        ps.update(self.pwr_supply.get_out())
                        ps.update(self.pwr_supply.get_mode())
                    self.hw.tdk_lambda_ps.update(update_power_supplies)
                next_status_read_time = time.time()
                while True:
                    next_status_read_time += self.ps_read_peroid
                    if "root" in userName:
                        # TODO: Not sure on the location of flush port
                        self.pwr_supply.flush_port()
                        update_power_supplies = [{'addr': self.hw.tdk_lambda_ps.get_platen_left_addr()},
                                                 {'addr': self.hw.tdk_lambda_ps.get_platen_right_addr()},
                                                 {'addr': self.hw.tdk_lambda_ps.get_shroud_left_addr()},
                                                 {'addr': self.hw.tdk_lambda_ps.get_shroud_right_addr()}]
                        for ps in update_power_supplies:
                            self.pwr_supply.set_addr(ps['addr'])
                            if not self.hw.operational_vacuum and self.hw.tdk_lambda_ps.get_val(ps['addr'], 'output enable'):
                                Logging.debugPrint(2,"TDK, either not in vacuum, or turned off")
                                self.pwr_supply.set_out_off()
                            ps.update(self.pwr_supply.get_status())
                            ps.update(self.pwr_supply.get_out())
                            ps.update(self.pwr_supply.get_mode())
                        self.hw.tdk_lambda_ps.update(update_power_supplies)
                        while len(self.hw.tdk_lambda_cmds):
                            self.Process_Commands(self.hw.tdk_lambda_cmds.pop(0))
                    else:
                        Logging.logEvent("Debug", "Status Update",
                                         {"message": "Test run of TDK Lambda Power Supplies loop",
                                          "level": 4})
                        f_tdk_lambda = open("../virtualized/hw-files/tdk_lambda.txt", "r")
                        tdk_lambda = []
                        for line in f_tdk_lambda:
                            tdk_lambda.append(float(line.strip()))
                        f_tdk_lambda.close()


                        # end test else
                        time.sleep(5)
                    HardwareStatusInstance.getInstance().tdk_lambda_power = True
                    if time.time() < next_status_read_time:
                        time.sleep(next_status_read_time - time.time())

            except Exception as e:
                HardwareStatusInstance.getInstance().tdk_lambda_power = False
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                Logging.logEvent("Error", "TDK Lambda Power Supplies Interface Thread",
                                 {"type": exc_type,
                                  "filename": fname,
                                  "line": exc_tb.tb_lineno,
                                  "thread": "TdkLambdaUpdater",
                                  "ThreadCollection":self.parent,
                                  "item":"Tdk-Lambda Heater",
                                  "itemID":-1,
                                  "details":"A TDK-Lambda is probably powered off"
                                  })
                Logging.logEvent("Debug", "Status Update",
                                 {"message": "There was a {} error in TdkLambdaUpdater. File: {}:{}\n{}".format(
                                     exc_type, fname, exc_tb.tb_lineno, e),
                                  "level": 1})
                if Logging.debug:
                    raise e
                if "root" in userName:
                    self.pwr_supply.close_port()
                time.sleep(4)
            # nicely close things, to open them back up again...

    def run_set_cmd(self, addr, fun, val):
        self.pwr_supply.set_addr(addr)
        fun(val)

    def Process_Commands(self, cmd):
        Logging.debugPrint(2,"Tdk command: {}".format(cmd))
        if 'Set Platen Left' == cmd[0]:
            if cmd[2] == 'V':
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_left_addr(),
                                 self.pwr_supply.set_pv, cmd[1])
            if cmd[2] == 'C':
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_left_addr(),
                                 self.pwr_supply.set_pc, cmd[1])
        elif 'Set Platen Right' == cmd[0]:
            if cmd[2] == 'V':
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_right_addr(),
                                 self.pwr_supply.set_pv, cmd[1])
            if cmd[2] == 'C':
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_right_addr(),
                                 self.pwr_supply.set_pc, cmd[1])
        elif 'Set Shroud Left' == cmd[0]:
            if cmd[2] == 'V':
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_left_addr(),
                                 self.pwr_supply.set_pv, cmd[1])
            if cmd[2] == 'C':
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_left_addr(),
                                 self.pwr_supply.set_pc, cmd[1])
        elif 'Set Shroud Right' == cmd[0]:
            if cmd[2] == 'V':
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_right_addr(),
                                 self.pwr_supply.set_pv, cmd[1])
            if cmd[2] == 'C':
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_right_addr(),
                                 self.pwr_supply.set_pc, cmd[1])
        elif 'Enable All Output' == cmd[0]:  # Duty cycle is a value from 0-1
            if self.hw.operation_vacuum:
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_left_addr(),
                                 self.pwr_supply.set_out, True)
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_right_addr(),
                                 self.pwr_supply.set_out, True)
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_left_addr(),
                                 self.pwr_supply.set_out, True)
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_right_addr(),
                                 self.pwr_supply.set_out, True)
            else:
                Logging.logEvent("Debug", "Status Update",
                                 {
                                     "message": 'TDK Lambda Powers Supply Cant be turned on when not in Operational vacuum',
                                     "level": 3})
        elif 'Enable Platen Output' == cmd[0]:  # Duty cycle is a value from 0-1
            if self.hw.operation_vacuum:
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_left_addr(),
                                 self.pwr_supply.set_out, True)
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_right_addr(),
                                 self.pwr_supply.set_out, True)
            else:
                Logging.logEvent("Debug", "Status Update",
                                 {
                                     "message": 'TDK Lambda Powers Supply Cant be turned on when not in Operational vacuum',
                                     "level": 3})
        elif 'Enable Shroud Output' == cmd[0]:  # Duty cycle is a value from 0-1
            if self.hw.operation_vacuum:
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_left_addr(),
                                 self.pwr_supply.set_out, True)
                self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_right_addr(),
                                 self.pwr_supply.set_out, True)
            else:
                Logging.logEvent("Debug", "Status Update",
                                 {
                                     "message": 'TDK Lambda Powers Supply Cant be turned on when not in Operational vacuum',
                                     "level": 3})
        elif 'Setup Platen' == cmd[0]:  # Duty cycle is a value from 0-1
            Logging.logEvent("Debug", "Status Update",
             {
             "message": 'Setting up Platen Heaters',
             "level": 2})
            if self.hw.operation_vacuum:
                for addr in [self.hw.tdk_lambda_ps.get_platen_left_addr(),
                             self.hw.tdk_lambda_ps.get_platen_right_addr()]:
                    self.pwr_supply.set_addr(addr)
                    self.pwr_supply.set_pc(0.0)
                    self.pwr_supply.set_pv(0.0)
                    self.pwr_supply.set_out_on()
            else:
                Logging.logEvent("Debug", "Status Update",
                                 {
                                     "message": 'TDK Lambda Powers Supply Cant be turned on when not in Operational vacuum',
                                     "level": 3})
        elif 'Setup Shroud' == cmd[0]:  # Duty cycle is a value from 0-1
            Logging.logEvent("Debug", "Status Update",
                             {
                                 "message": 'Setting up Shroud Heaters',
                                 "level": 2})
            if self.hw.operation_vacuum:
                for addr in [self.hw.tdk_lambda_ps.get_shroud_left_addr(),
                             self.hw.tdk_lambda_ps.get_shroud_right_addr()]:
                    self.pwr_supply.set_addr(addr)
                    self.pwr_supply.set_pc(0.0)
                    self.pwr_supply.set_pv(0.0)
                    self.pwr_supply.set_out_on()
            else:
                Logging.logEvent("Debug", "Status Update",
                                 {
                                     "message": 'TDK Lambda Powers Supply Cant be turned on when not in Operational vacuum',
                                     "level": 3})
        elif 'Disable All Output' == cmd[0]:  # Duty cycle is a value from 0-1
            self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_left_addr(),
                             self.pwr_supply.set_out, False)
            self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_right_addr(),
                             self.pwr_supply.set_out, False)
            self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_left_addr(),
                             self.pwr_supply.set_out, False)
            self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_right_addr(),
                             self.pwr_supply.set_out, False)
        elif 'Disable Platen Output' == cmd[0]:  # Duty cycle is a value from 0-1
            self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_left_addr(),
                             self.pwr_supply.set_out, False)
            self.run_set_cmd(self.hw.tdk_lambda_ps.get_platen_right_addr(),
                             self.pwr_supply.set_out, False)
        elif 'Disable Shroud Output' == cmd[0]:  # Duty cycle is a value from 0-1
            self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_left_addr(),
                             self.pwr_supply.set_out, False)
            self.run_set_cmd(self.hw.tdk_lambda_ps.get_shroud_right_addr(),
                             self.pwr_supply.set_out, False)
        elif 'Platen Duty Cycle' == cmd[0]:  # Duty cycle is a value from 0-1
            if self.hw.operation_vacuum:
                if cmd[1] > 1:
                    dutycycle = 1.0
                elif cmd[1] < 0:
                    dutycycle = 0.0
                else:
                    dutycycle = float(cmd[1])
                current = 5.5 * dutycycle
                voltage = current * 80.0
                for addr in [self.hw.tdk_lambda_ps.get_platen_left_addr(),
                             self.hw.tdk_lambda_ps.get_platen_right_addr()]:
                    self.pwr_supply.set_addr(addr)
                    self.pwr_supply.set_pc(current)
                    self.pwr_supply.set_pv(voltage)
            else:
                Logging.logEvent("Debug", "Status Update",
                                 {
                                     "message": 'TDK Lambda Powers Supply Cant be turned on when not in Operational vacuum',
                                     "level": 3})
        elif 'Shroud Duty Cycle' == cmd[0]:  # Duty cycle is a value from 0-1
            if self.hw.operation_vacuum:
                if cmd[1] > 1:
                    dutycycle = 1.0
                elif cmd[1] < 0:
                    dutycycle = 0.0
                else:
                    dutycycle = float(cmd[1])
                current = 3 * dutycycle
                voltage = current * 80.0
                for addr in [self.hw.tdk_lambda_ps.get_shroud_left_addr(),
                             self.hw.tdk_lambda_ps.get_shroud_right_addr()]:
                    self.pwr_supply.set_addr(addr)
                    self.pwr_supply.set_pc(current)
                    self.pwr_supply.set_pv(voltage)
            else:
                Logging.logEvent("Debug", "Status Update",
                                 {
                                     "message": 'TDK Lambda Powers Supply Cant be turned on when not in Operational vacuum',
                                     "level": 3})
        else:
            Logging.logEvent("Error", 'Unknown TDK Lambda command: "%s"' % cmd[0],
                             {"type": 'Unknown TdkLambda_Cmd',
                              "filename": 'ThreadControls/TdkLambdaUpdater.py',
                              "line": 93,
                              "thread": "TdkLambdaUpdater"
                              })


# if __name__ == '__main__':
    # adding debug info
    # if(len(sys.argv)>1):
    #     for arg in sys.argv:
    #         if arg.startswith("-v"):
    #             Logging.verbos = arg.count("v")
    # Logging.logEvent("Debug","Status Update",
    #     {"message": "Debug on: Level {}".format(Logging.verbos),
    #      "level":1})
    # thread = TdkLambdaUpdater()
    # thread.daemon = True
    # thread.start()

    # hw = HardwareStatusInstance.getInstance()
    # p = HardwareStatusInstance.getInstance().tdk_lambda_ps
    # c = HardwareStatusInstance.getInstance().tdk_lambda_cmds

    # time.sleep(10)
    # print(p.getJson())

    # hw.operation_vacuum = True
    # time.sleep(5)
    # print(p.getJson())
    # c.append(['Setup Platen', ''])
    # time.sleep(5)
    # print(p.getJson())
    # c.append(['Platen Duty Cycle', 0.1])
    # time.sleep(5)
    # print(p.getJson())
    # c.append(['Platen Duty Cycle', 0.05])
    # time.sleep(5)
    # print(p.getJson())
    # c.append(['Platen Duty Cycle', 1.0])
    # time.sleep(5)
    # print(p.getJson())
    # c.append(['Platen Duty Cycle', 0.5])
    # c.append(['Platen Duty Cycle', 0.5])
    # c.append(['Platen Duty Cycle', 0.5])
    # c.append(['Platen Duty Cycle', 0.5])
    # time.sleep(5)
    # print(p.getJson())
    # c.append(['Platen Duty Cycle', 0.0])
    # time.sleep(5)
    # print(p.getJson())
    # c.append(['Disable Platen Output', ''])
    # time.sleep(5)
    # print(p.getJson())
