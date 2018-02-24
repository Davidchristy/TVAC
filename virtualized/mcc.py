from threading import Thread
import time


def get_checksum(cmd):  # append the sum of the string's bytes mod 256 + '\r'
    # print("Checksum cmd: {}".format(cmd))
    d = sum(cmd.encode())
    #       0x30 + ( (d2 to d6) or (d0 xor d6) or ((d1 xor d7) shift to d2)
    return 0x30 + ((d & 0x3c) |
                   ((d & 0x01) ^ ((d & 0x40) >> 6)) |  # (d0 xor d6)
                   ((d & 0x02) ^ ((d & 0x80) >> 6)))  # (d1 xor d7)

def process_mcc_cmd(cmd):
    print("MCC: command: {}".format(cmd))
    if "$P6?6" in cmd:
        return "65"
    if "i?" in cmd:
        return "2"
    return ""



class Mcc(Thread):
    def __init__(self):
        Thread.__init__(self, name="mcc")

    def run(self):
        while True:
            try:

                port = open('/home/vagrant/mcc', 'r+b', buffering=0)
                buffer = ''
                print("MCC: About to start loop")
                while True:
                    # print("Holding for reading")
                    buff = port.read(1).decode()
                    # print("Byte found: {}\ncurrent buffer: {}".format(buff, buffer))
                    buffer += buff
                    if buff == "\r" or len(buffer) >= 128:

                        reply = "A" + process_mcc_cmd(buffer)
                        final_reply = "${}{}\r".format(reply,chr(get_checksum(reply)))
                        print("MCC: cmd: {}\treply: {}".format(buffer, final_reply))
                        port.write(final_reply.encode())
                        buffer = ''
                        # time.sleep(.1)
            except Exception as e:
                raise e
                time.sleep(1)

        # end loop
    # end run()