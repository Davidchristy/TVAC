from threading import Thread
import time


def get_checksum(cmd):  # append the sum of the string's bytes mod 256 + '\r'
    # print("Checksum cmd: {}".format(cmd))
    d = sum(cmd.encode())
    #       0x30 + ( (d2 to d6) or (d0 xor d6) or ((d1 xor d7) shift to d2)
    return 0x30 + ((d & 0x3c) |
                   ((d & 0x01) ^ ((d & 0x40) >> 6)) |  # (d0 xor d6)
                   ((d & 0x02) ^ ((d & 0x80) >> 6)))  # (d1 xor d7)

def process_tdk_cmd(cmd):
    if "OUT?" in cmd:
        return "ON"
    if "AST?" in cmd:
        return "ON"
    return "OK"


def append_checksum(cmd):
    return '{:s}${:02X}\r'.format(cmd, 0xff & sum(cmd.encode()))

class Tdk(Thread):
    def __init__(self, time_delay=0):
        Thread.__init__(self, name="tdk")
        self.time_delay = time_delay

    def run(self):
        while True:
            try:

                port = open('/home/vagrant/tdk', 'r+b', buffering=0)
                buffer = ''
                print("TDK: About to start loop")
                while True:
                    # Holding here until we need to read.
                    buff = port.read(1).decode()

                    # Adding the bytes together until it's over 128 or there is Return Carrage
                    buffer += buff
                    if buff == "\r" or len(buffer) >= 128:
                        # Always defined as A in this dummy
                        reply = process_tdk_cmd(buffer)
                        final_reply = append_checksum(reply)
                        print("TDK: cmd: {}".format(buffer))
                        time.sleep(self.time_delay)
                        port.write(final_reply.encode())
                        buffer = ''
            except Exception as e:
                raise e
                time.sleep(1)

        # end loop
    # end run()