#!/usr/bin/env python3.5
from socket import *
import time
import math


def get_checksum(cmd):  # append the sum of the string's bytes mod 256 + '\r'
    return sum(cmd.encode()) % 256


def apply_checksum(cmd):  # append the sum of the string's bytes mod 256 + '\r'
    return "{0}{1:03d}\r".format(cmd, get_checksum(cmd))


def gen_cmd_read(address, parm=349):  # Cmd syntax see page #16 of MPT200 Operating instructions
    return apply_checksum("{:03d}00{:03d}02=?".format(address, parm))


def gen_cmd_write(address, parm, data_str):  # Cmd syntax on page #16 of MPT200 Operating instructions
    return apply_checksum("{0:03d}10{1:03d}{2:02d}{3}".format(address, parm, len(data_str), data_str))


def response_good(address, response, parm=349):
    if not response:
        return False

    if int(response[-3:]) != get_checksum(response[:-3]):
        print("R:--" + response.replace('\r', r'\r') + "---",
              "Checksum:" + str(get_checksum(response[:-3])) + "Failure")
        return False
    if int(response[:3]) != address:
        print("R:--" + response.replace('\r', r'\r') + "---", "Address:", str(address), "Failure")
        return False
    if int(response[5:8]) != parm:
        print("R:--" + response.replace('\r', r'\r') + "---", "Param:", str(parm), "Failure")
        return False
    if int(response[8:10]) != (len(response) - 13):
        print("R:--" + response.replace('\r', r'\r') + "---", "Payload size:", str(len(response) - 13),
              "Failure" + response[8:10])
        return False
    if (int(response[8:10]) == 6) and (response[10:-3] == 'NO_DEF'):
        print("R:--" + response.replace('\r', r'\r') + "---", "Error: The parameter", str(parm), "does not exist.")
        return False
    if (int(response[8:10]) == 6) and (response[10:-3] == '_RANGE'):
        print("R:--" + response.replace('\r', r'\r') + "---",
              "Error: Data length for param, " + str(parm) + ", is outside the permitted range.")
        return False
    if (int(response[8:10]) == 6) and (response[10:-3] == '_LOGIC'):
        print("R:--" + response.replace('\r', r'\r') + "---", "Error: Logic access violation for the param:",
              str(parm))
        return False
    return True  # Yea!! respomnce seems ok


def convert_str_to_pressure(buff, in_torr=True):
    if len(buff) == 6 and buff.isdigit:
        p = float((float(buff[:4]) / 1000.0) * float(10 ** (int(buff[-2:]) - 20)))
        if p > 1e-10:
            if in_torr:  ## Return the Pressure in Torr.
                return p * 0.75006  # hPa to Torr
            else:  ## Return in hPa gauge default.
                return p
        else:
            raise ValueError("Convert_Str2Press value of %s below realistic value" % p)
    else:
        raise ValueError("Convert_Str2Press value in: %s" % buff)


def convert_pressure_to_str(pressure, in_torr=True):
    if in_torr:
        pressure = pressure / 0.75006
    b = math.floor(math.log10(pressure))
    if b < -20:  ## coarse minimum power of 10 to -20
        b = -20
    if b > 79:  ## coarse maximum power of 10 to 79
        b = 79
    a = int(1000.0 * (pressure / (10 ** b)))
    return "{:04d}{:02d}".format(a, b + 20)


def send_receive(address, parm=349, data_str=None):
    a = socket(AF_INET, SOCK_DGRAM)
    a.settimeout(5)
    for tries in range(3):
        ip = '192.168.99.124'
        # Changed to localhost for testing
        ip = 'localhost'
        if data_str is None:
            tmp = gen_cmd_read(address, parm).encode()
            print("messing sending: {}".format(tmp))
            a.sendto(tmp, (ip, 1234))
            print("after send")
        else:
            a.sendto(gen_cmd_write(address, parm, data_str).encode(), (ip, 1234))
        time.sleep(0.060 * (tries + 1))
        print("about to wait for reply")
        resp = ""
        try:
            response,_ = a.recvfrom(4092)
            resp = response.decode().strip()
        except timeout:
            pass

        print("reply: \""+resp+"\"")
        if response_good(address, resp, parm):
            break
        print("Try number: " + str(tries))
    else:
        print("No more tries! Something is wrong!")
        resp = "{:*^32}".format('Timeout!')
    return resp[10:-3]


class PfeifferGauge:

    def __init__(self):
        self.a = socket(AF_INET, SOCK_DGRAM)

    # def SendReceive_Xuart(self, Address, Parm=349, dataStr=None):
    #     p_gauge = open('/dev/ttyxuart2', 'r+b', buffering=0)
    #     for tries in range(3):
    #         if dataStr is None:
    #             p_gauge.write(gen_cmd_read(Address, Parm).encode())
    #         else:
    #             p_gauge.write(gen_cmd_write(Address, Parm, dataStr).encode())
    #         time.sleep(0.060 * (tries + 1))
    #         Resp = p_gauge.read(113 * (tries + 1)).decode().strip()
    #         if response_good(Address, Resp, Parm):
    #             break
    #         print("Try number: " + str(tries))
    #     else:
    #         print("No more tries! Something is wrong!")
    #         Resp = "{:*^32}".format('Timeout!')
    #     p_gauge.close()
    #     return Resp[10:-3]

    def GetCCstate(self, Address):  # Is the Cold Cathode Sensor on
        buff = send_receive(Address, 41)
        if buff == '0':
            return False
        elif buff == '1':
            return True
        else:
            raise ValueError("GetCCstate value not 0 or 1: %s" % buff)

    def SetCCstate(self, Address, CC_on):  # Set the Cold Cathode Sensor to on.
        if not CC_on:
            resp = send_receive(Address, 41, '0')
            if resp != '0':
                raise ValueError("SetCCstate value not set to 0: %s" % resp)
        else:
            resp = send_receive(Address, 41, '1')
            if resp != '1':
                raise ValueError("SetCCstate value not set to 1: %s" % resp)

    def GetSwMode(self, Address):  # Get Cold Cathode switching range
        buff = send_receive(Address, 49)
        if buff.isdigit:
            return int(buff)
        else:
            raise ValueError("GetSwMode value not 0 or 1: %s" % buff)

    def SetSwMode(self, Address, CC_on):  # Set the Cold Cathode switching range to trans_LO.
        if CC_on == False:
            resp = send_receive(Address, 49, '000')  # switch
            if resp != '000':
                raise ValueError("GetSwMode value not set to 0: %s" % resp)
        else:
            resp = send_receive(Address, 49, '001')  # trans_LO
            if resp != '001':
                raise ValueError("GetSwMode value not set to 1: %s" % resp)

    def GetError(self, Address):  # Pfeifer returns an error in the gauge
        return send_receive(Address, 303)

    def GetSofwareV(self, Address):  # Returns gauge's software version
        return send_receive(Address, 312)

    def GetModelName(self, Address):  # Returns gauge's model name
        return send_receive(Address, 349)

    def GetSwPressure(self, Address, sw2=False, inTorr=True):
        if sw2:
            return convert_str_to_pressure(send_receive(Address, 732), inTorr)
        else:
            return convert_str_to_pressure(send_receive(Address, 730), inTorr)

    def SetSwPressure(self, Address, Pressure, sw2=False, inTorr=True):
        dataStr = convert_pressure_to_str(Pressure, inTorr)
        if sw2:
            resp = send_receive(Address, 732, dataStr)
        else:
            resp = send_receive(Address, 730, dataStr)
        if dataStr != resp:
            raise  ValueError("Error Setting Switch pressure. sent: '{}'; resp '{}'".format(dataStr,resp))

    def GetPressure(self, Address, inTorr=True):  # Pfeifer gauge returns pressure in hPa or Torr
        return convert_str_to_pressure(send_receive(Address, 740), inTorr)

    def SetPressure(self, Address, Pressure, inTorr=True):  # Set pressure in hPa or Torr for calibration.
        dataStr = convert_pressure_to_str(Pressure, inTorr)
        resp = send_receive(Address, 740, dataStr)
        if dataStr != resp:
            raise  ValueError("Error Setting pressure. Sent: '{}'; Resp: '{}'".format(dataStr,resp))

    def SetPressureSp(self, Address, value):
        if value > 999:
            value = 999
        elif value < 0:
            value = 0
        dataStr = "{:03d}".format(int(value))
        resp = send_receive(Address, 741, dataStr)
        if dataStr != resp:
            raise  ValueError("Error Setting pressure. Sent: '{}'; Resp: '{}'".format(dataStr,resp))

    def GetCorrPir(self, Address):  # Get Pirani Correction Value
        return float(send_receive(Address, 742))

    def SetCorrPir(self, Address, value):  # Setting Pirani Correction Value
        if value > 8.0:
            value = 8.0
        elif value < 0.2:
            value = 0.2
        dataStr = "{:06d}".format(int(value*100))
        resp = send_receive(Address, 742, dataStr)
        if dataStr != resp:
            raise  ValueError("Error Setting Pirani Correction Value. Sent: '{}'; Resp: '{}'".format(dataStr,resp))

    def GetCorrCC(self, Address):  # Get Cold Cathode Correction Value
        return float(send_receive(Address, 742))

    def SetCorrCC(self, Address, value):  # Setting Cold Cathode Correction Value
        if value > 8.0:
            value = 8.0
        elif value < 0.2:
            value = 0.2
        dataStr = "{:06d}".format(int(value*100))
        resp = send_receive(Address, 742, dataStr)
        if dataStr != resp:
            raise  ValueError("Error Setting Cold Cathode Correction Value. Sent: '{}'; Resp: '{}'".format(dataStr,resp))

if __name__ == '__main__':
    import sys

    sys.path.insert(0, '../')
    pg = PfeifferGauge()
    for i in range(1, 3+1):
        print("Addr {:d}, {}, Pressure: {:f} torr.".format(i,
                                                           pg.GetModelName(i),
                                                           pg.GetPressure(i)))
