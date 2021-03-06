#!/usr/bin/env python3.5
import os
import sys
import time
from threading import Thread

if __name__ == '__main__':
    sys.path.insert(0, os.getcwd())

from Collections.HardwareStatusInstance import HardwareStatusInstance
from Collections.ProfileInstance import ProfileInstance
from Hardware_Drivers.Shi_Compressor import ShiCompressor

from Logging.Logging import Logging


class ShiCompressorUpdater(Thread):
    def __init__(self, parent=None, target=None, name=None,
                 args=(), kwargs=None):
        Thread.__init__(self, target=target, name="ShiCompressorUpdater")
        self.args = args
        self.kwargs = kwargs
        self.parent = parent

        self.compressor = ShiCompressor()
        self.hw = HardwareStatusInstance.getInstance()
        # self.compressor_read_period = 4  # 0.5s loop period
        self.op_hours_read_period = 120  # 120s = 2 min read period

        self.number_continuous_errors = 0
        self.MAX_NUMBER_OF_ERRORS = 3

        self.sleep_time = 3

    def run(self):
        if os.name == "posix":
            userName = os.environ['LOGNAME']
        else:
            userName = "user"
        # While true to restart the thread if it errors out
        while True:
            # Catch anything that goes wrong
            # This has no check because it should always be running
            try:
                # Thread "Start up" stuff goes here
                Logging.logEvent("Debug", "Status Update",
                                {"message": "Starting Shi Compressor Updater",
                                "level": 2})


                if "root" in userName:
                    # Live systems go here
                    Logging.logEvent("Debug", "Status Update",
                                    {"message": "Power on the Shi Compressor",
                                    "level": 3})
                    self.compressor.open_port()
                    while self.hw.pc_104.digital_out.getVal('CryoP Pwr Relay 1') is None:
                        time.sleep(1)
                    Currently_powered = self.hw.pc_104.digital_out.getVal('CryoP Pwr Relay 1')

                    self.hw.pc_104.digital_out.update({'CryoP Pwr Relay 1': True})
                    if not Currently_powered:
                        time.sleep(5)
                    self.compressor.flush_port()

                next_op_hours_read_time = time.time()
                # setup is done, this loop is the normal thread loop
                while True:
                    # next_compressor_read_time = time.time() + self.compressor_read_period
                    # self.hw.shi_compressor_power = self.hw.pc_104.digital_out.getVal('CryoP Pwr Relay 1')
                    if "root" in userName:
                        Logging.logEvent("Debug", "Status Update",
                                         {"message": "Reading and writing with ShiCompressorUpdater.",
                                          "level": 4})
                        val = {}
                        val.update(self.compressor.get_temperatures())
                        val.update(self.compressor.get_pressure())
                        val.update(self.compressor.get_status_bits())
                        if time.time() > next_op_hours_read_time:
                            val.update(self.compressor.get_id())
                            next_op_hours_read_time += self.op_hours_read_period
                        self.hw.shi_cryopump.update({'Compressor': val})

                        while len(self.hw.shi_compressor_cmds):
                            cmd = self.hw.shi_compressor_cmds.pop()
                            if 'on' == cmd:
                                self.compressor.set_compressor_on()
                            elif 'off' == cmd:
                                self.compressor.set_compressor_off()
                            elif 'reset' == cmd:
                                self.compressor.set_reset()
                            else:
                                Logging.logEvent("Error", 'Unknown Shi_Compressor_Cmds: "%s"' % cmd,
                                                 {"type": 'Unknown Shi_Compressor_Cmds',
                                                  "filename": 'ThreadControls/ShiCompressorUpdater.py',
                                                  "line": 0,
                                                  "thread": "ShiCompressorUpdater"
                                                  })
                            #end if/else
                        #end while
                    # end if root
                    else:
                        Logging.logEvent("Debug", "Status Update",
                                         {"message": "Test run of Shi Compressor loop",
                                          "level": 4})

                        f_compressor = open("../virtualized/hw-files/shi_compressor.txt", "r")
                        compressor = []
                        for line in f_compressor:
                            compressor.append(float(line.strip()))
                        f_compressor.close()

                    HardwareStatusInstance.getInstance().shi_compressor_power = True
                    self.number_continuous_errors = 0
                    # print("Compressor Sucess")
                    time.sleep(self.sleep_time)

                #end of inner while true
            # end of try
            except Exception as e:
                self.number_continuous_errors += 1
                print("Number of Compressor errors: {}".format(self.number_continuous_errors))
                if self.number_continuous_errors >= self.MAX_NUMBER_OF_ERRORS:
                    HardwareStatusInstance.getInstance().shi_compressor_power = False
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                Logging.logEvent("Error", "Shi Compressor Interface Thread",
                                 {"type": exc_type,
                                  "filename": fname,
                                  "line": exc_tb.tb_lineno,
                                  "thread": "ShiCompressorUpdater"
                                  })
                Logging.logEvent("Debug", "Status Update",
                                 {"message": "There was a {} error in ShiCompressorUpdater. File: {}:{}\n{}".format(
                                     exc_type, fname, exc_tb.tb_lineno, e),
                                  "level": 2})
                if Logging.debug:
                    raise e
                if "root" in userName:
                    self.compressor.close_port()
                time.sleep(4)


# if __name__ == '__main__':
#     # adding debug info
#     if(len(sys.argv)>1):
#         for arg in sys.argv:
#             if arg.startswith("-v"):
#                 Logging.verbose = arg.count("v")
#     Logging.logEvent("Debug","Status Update",
#         {"message": "Debug on: Level {}".format(Logging.verbose),
#          "level":1})
#
#     hw_status = HardwareStatusInstance.getInstance()
#     hw_status.pc_104.digital_out.update({'CryoP Pwr Relay 1': True})
#
#     thread = ShiCompressorUpdater()
#     thread.daemon = True
#     thread.start()
#
#     while True:
#         time.sleep(5)
#         print(hw_status.shi_cryopump.getJson())
#
