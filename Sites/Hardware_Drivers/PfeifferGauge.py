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
    return True  # Yea!! response seems ok


def convert_str_to_pressure(buff, in_torr=True):
    if len(buff) == 6 and buff.isdigit():
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


def send_receive(pi_socket, address, parm=349, data_str=None):
    ip = '192.168.99.124'
    pi_socket = socket(AF_INET, SOCK_DGRAM)
    # TODO Research this timeout time
    pi_socket.settimeout(5)

    if data_str is None:
        str_to_send = gen_cmd_read(address, parm).encode()
    else:
        str_to_send = gen_cmd_write(address, parm, data_str).encode()

    for tries in range(1, 4):

        pi_socket.sendto(str_to_send, (ip, 1234))

        # TODO: Look up response time from socket (and pi)
        # After sending the data, wait a tiny amount of time for gauge to reply
        time.sleep(0.060 * tries)
        try:
            response_raw,_ = pi_socket.recvfrom(4092)
            response = response_raw.decode().strip()
        except timeout:
            # TODO: I really don't think it should work like this...
            # Sleep to give time for wires to sort themselves out
            time.sleep(.5)
        else:
            if response_good(address, response, parm):
                break
    else:
        raise TimeoutError("Pfeiffer Gauge Not Replying.")
    return response[10:-3]


class PfeifferGauge:

    def __init__(self):
        self.pi_socket = socket(AF_INET, SOCK_DGRAM)
        # TODO Research this timeout time
        self.pi_socket.settimeout(5)


    # TODO: Why is this not used on pressure gauge 3
    def GetCorrCC(self, address):  # Get Cold Cathode Correction Value
        return float(send_receive(pi_socket=self.pi_socket, address=address, parm=742))

    # TODO: Why is this not used on pressure gauge 3
    def GetCCstate(self, address):  # Is the Cold Cathode Sensor on
        buff = send_receive(pi_socket=self.pi_socket, address=address, parm=41)
        if buff == '0':
            return False
        elif buff == '1':
            return True
        else:
            raise ValueError("GetCCstate value not 0 or 1: %s" % buff)


    # TODO: Why is this not used on pressure gauge 3
    def GetSwMode(self, address):  # Get Cold Cathode switching range
        buff = send_receive(pi_socket=self.pi_socket, address=address, parm=49)
        if buff.isdigit():
            return int(buff)
        else:
            raise ValueError("GetSwMode value not 0 or 1: %s" % buff)


    def GetCorrPir(self, address):  # Get Pirani Correction Value
        return float(send_receive(pi_socket=self.pi_socket, address=address, parm=742))


    def GetError(self, address):  # Pfeifer returns an error in the gauge
        return send_receive(pi_socket=self.pi_socket, address=address, parm=303)


    def GetSofwareV(self, address):  # Returns gauge's software version
        return send_receive(pi_socket=self.pi_socket, address=address, parm=312)


    def GetModelName(self, address):  # Returns gauge's model name
        return send_receive(pi_socket=self.pi_socket, address=address, parm=349)


    def GetSwPressure(self, address, sw2=False, in_torr=True):
        if sw2:
            return convert_str_to_pressure(send_receive(pi_socket=self.pi_socket, address=address, parm=732), in_torr)
        else:
            return convert_str_to_pressure(send_receive(pi_socket=self.pi_socket, address=address, parm=730), in_torr)



    def GetPressure(self, address, in_torr=True):  # Pfeifer gauge returns pressure in hPa or Torr
        return convert_str_to_pressure(send_receive(pi_socket=self.pi_socket, address=address, parm=740), in_torr)


    # Never used
    def set_sw_pressure(self, address, pressure, sw2=False, in_torr=True):
        data_str = convert_pressure_to_str(pressure, in_torr)
        if sw2:
            resp = send_receive(pi_socket=self.pi_socket, address=address, parm=732, data_str=data_str)
        else:
            resp = send_receive(pi_socket=self.pi_socket, address=address, parm=730, data_str=data_str)
        if data_str != resp:
            raise  ValueError("Error Setting Switch pressure. sent: '{}'; resp '{}'".format(data_str,resp))


    # Never used
    def set_pressure(self, address, pressure, in_torr=True):  # Set pressure in hPa or Torr for calibration.
        data_str = convert_pressure_to_str(pressure, in_torr)
        resp = send_receive(pi_socket=self.pi_socket, address=address, parm=740, data_str=data_str)
        if data_str != resp:
            raise  ValueError("Error Setting pressure. Sent: '{}'; Resp: '{}'".format(data_str,resp))


    # Never used
    def set_pressure_sp(self, address, value):
        if value > 999:
            value = 999
        elif value < 0:
            value = 0
        data_str = "{:03d}".format(int(value))
        resp = send_receive(pi_socket=self.pi_socket, address=address, parm=741, data_str=data_str)
        if data_str != resp:
            raise  ValueError("Error Setting pressure. Sent: '{}'; Resp: '{}'".format(data_str,resp))


    # Never used
    def set_corr_pir(self, address, value):  # Setting Pirani Correction Value
        if value > 8.0:
            value = 8.0
        elif value < 0.2:
            value = 0.2
        data_str = "{:06d}".format(int(value*100))
        resp = send_receive(pi_socket=self.pi_socket, address=address, parm=742, data_str=data_str)
        if data_str != resp:
            raise  ValueError("Error Setting Pirani Correction Value. Sent: '{}'; Resp: '{}'".format(data_str,resp))


    # Never used
    def set_corr_cc(self, address, value):  # Setting Cold Cathode Correction Value
        if value > 8.0:
            value = 8.0
        elif value < 0.2:
            value = 0.2
        data_str = "{:06d}".format(int(value*100))
        resp = send_receive(pi_socket=self.pi_socket, address=address, parm=742, data_str=data_str)
        if data_str != resp:
            raise  ValueError("Error Setting Cold Cathode Correction Value. Sent: '{}'; Resp: '{}'".format(data_str,resp))


    # Never used
    def set_cc_state(self, address, cc_on):  # Set the Cold Cathode Sensor to on.
        if not cc_on:
            resp = send_receive(pi_socket=self.pi_socket, address=address, parm=41, data_str='0')
            if resp != '0':
                raise ValueError("SetCCstate value not set to 0: %s" % resp)
        else:
            resp = send_receive(pi_socket=self.pi_socket, address=address, parm=41, data_str='1')
            if resp != '1':
                raise ValueError("SetCCstate value not set to 1: %s" % resp)


    # Never used
    def set_sw_mode(self, address, cc_on):  # Set the Cold Cathode switching range to trans_LO.
        if not cc_on:
            resp = send_receive(pi_socket=self.pi_socket, address=address, parm=49, data_str='000')  # switch
            if resp != '000':
                raise ValueError("GetSwMode value not set to 0: %s" % resp)
        else:
            resp = send_receive(pi_socket=self.pi_socket, address=address, parm=49, data_str='001')  # trans_LO
            if resp != '001':
                raise ValueError("GetSwMode value not set to 1: %s" % resp)
