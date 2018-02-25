from threading import Thread
import time

import sys
sys.path.insert(1,"../Sites")
from PyCRC_master.PyCRC.CRC16 import CRC16

def process_compressor_cmd(cmd_raw):
    cmd = cmd_raw[1:-4]
    if "TEA" in cmd:
        return "086,040,031,000"
    if "PR1" in cmd:
        return "079"
    if "STA" in cmd:
        return "0301"
    if "ID1" in cmd:
        return "1.6,005842.1"
    return ""

class Compressor(Thread):
    def __init__(self,time_delay=0):
        Thread.__init__(self, name="mcc")
        self.time_delay = time_delay

    def run(self):
        while True:
            try:

                port = open('/home/vagrant/compressor', 'r+b', buffering=0)
                buffer = ''
                crc = CRC16(modbus_flag=True).calculate
                print("Compressor: About to start loop")
                while True:
                    buff = port.read(1).decode()
                    buffer += buff
                    if buff == "\r" or len(buffer) >= 128:
                        # start_time = time.time()
                        cmd = buffer.strip()
                        print("Compressor: cmd: '{}'".format(cmd))
                        reply = process_compressor_cmd(cmd)
                        formatted_reply = "$" + "{},{},".format(cmd[1:4],reply)
                        final_reply = formatted_reply + "{:04X}\r".format(crc(formatted_reply))
                        # print("Compressor: Final reply: '{}'".format(final_reply))
                        time.sleep(self.time_delay)
                        port.write(final_reply.encode())
                        buffer = ''
                        # print("runTime: {}".format(round(time.time()-start_time,4)))
            except Exception as e:
                raise e

        # end loop
    # end run()