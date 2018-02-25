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
    # print("MCC: command: {}".format(cmd))
    if "$P6?6" in cmd:
        return "65"
    if "i?" in cmd:
        return "2"
    if "E?" in cmd:
        purgeValve = "1"
        return purgeValve
    if "Q?" in cmd:
        return "1"
    if "K:" in cmd:
        second_stage_temp = "14"
        return second_stage_temp
    if "L=" in cmd:
        cryopump_vessel_pressure = "30"
        # in milli-torr
        return cryopump_vessel_pressure
    if "XOI??" in cmd:
        duty_cycle = "23"
        # duty_cycle [0-23]
        return duty_cycle
    if "D?" in cmd:
        roughing_valve_state = "1"
        return roughing_valve_state
    if "J;" in cmd:
        first_stage_temp = "64"
        return first_stage_temp
    if "A??" in cmd:
        return "11"
    if "eT" in cmd:
        error_value = "@"
        return error_value
    if "O>" in cmd:
        regen_step = "z"
        return regen_step
    if "S16" in cmd:
        status = "`"
        return status
    if "Y?" in cmd:
        uptime = "100"
        return uptime
    if "I?" in cmd:
        second_stage_temp = "12"
        return second_stage_temp
    if "B?" in cmd:
        return "1"
    if "t?" in cmd:
        return "0"
    if "H?" in cmd:
        return "465"
    if "P" in cmd and "?" in cmd:
        return "100"
    if "k" in cmd:
         return "10"
    if "l" in cmd:
        return "0"
    if "j?" in cmd:
        return "0"
    if "n_" in cmd:
        return "8"
    if "a" in cmd:
        return "500"
    if "m\\" in cmd:
        return "0"
    if "Z?" in cmd:
        return "11"

    return ""



class Mcc(Thread):
    def __init__(self, time_delay=0):
        Thread.__init__(self, name="mcc")
        self.time_delay = time_delay

    def run(self):
        while True:
            try:

                port = open('/home/vagrant/mcc', 'r+b', buffering=0)
                buffer = ''

                print("MCC: About to start loop")
                while True:

                    buff = port.read(1).decode()
                    buffer += buff
                    if buff == "\r" or len(buffer) >= 128:
                        # start_time = time.time()

                        reply = "A" + process_mcc_cmd(buffer)
                        final_reply = "${}{}\r".format(reply,chr(get_checksum(reply)))
                        print("MCC: cmd: {}".format(buffer))
                        time.sleep(self.time_delay)
                        port.write(final_reply.encode())
                        buffer = ''
                        # print("runTime: {}".format(round(time.time() - start_time, 4)))
            except Exception as e:
                raise e
                time.sleep(1)

        # end loop
    # end run()