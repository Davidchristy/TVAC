import time

from Hardware_Drivers.tty_reader import TTY_Reader
from Collections.HardwareStatusInstance import HardwareStatusInstance

def append_checksum(cmd):
    return '{:s}${:02X}\r'.format(cmd, 0xff & sum(cmd.encode()))


def check_checksum(resp):
    if resp == append_checksum(resp[:-4]):
        return True, resp[:-4].strip()
    else:
        return False, resp.strip()


class TdkLambdaGenesys:

    def __init__(self):
        self.port = None
        self.port_listener = TTY_Reader(None,name="Tdk_lambda_Genesys_reader")
        self.port_listener.daemon = True
        self.hw = HardwareStatusInstance.getInstance()

    def open_port(self):
        self.port = open('/dev/ttyxuart4', 'r+b', buffering=0)
        self.port_listener.get_fd(self.port)
        try:
            self.port_listener.start()
        except Exception as e:
            pass
        self.port_listener.flush_buffer(1.0)

    def flush_port(self, wait_time = .5):
        self.port_listener.flush_buffer(wait_time)

    def close_port(self):
        if not self.port.closed:
            self.port.close()

    def send_cmd(self, command):
        resp = ""
        for tries in range(1, 4):
            self.port.write(append_checksum(command).encode())
            reply = self.port_listener.read_line(time_out=1.0)
            (resp_good, resp) = check_checksum(reply)
            if resp_good:
                break
            time.sleep(0.15 * tries)
        else:
            raise TimeoutError('TDK Lambda, not replying, or faulty reply. Last reply: "{:s}" is not "OK"'.format(resp))
        return resp

    def set_addr(self, addr):
        resp = self.send_cmd('ADR {:d}'.format(addr))
        if resp != 'OK':
            raise RuntimeError('Addr {:d}; Response: "{:s}" is not "OK"'.format(addr, resp))

    def get_idn(self):
        return {'Model Name': self.send_cmd('IDN?')}

    def get_rev(self):
        return {'Software Vir': self.send_cmd('REV?')}

    def get_sn(self):
        return {'serial number': self.send_cmd('SN?')}

    def get_date(self):
        return {'last test date': self.send_cmd('DATE?')}

    def get_out(self):
        resp = self.send_cmd('OUT?')
        if resp == 'ON':
            return {'output enable': True}
        elif resp == 'OFF':
            return {'output enable': False}
        else:
            raise RuntimeError('OUT? Response: "{:s}" is not "ON" or "OFF"'.format(resp))

    def set_out(self, out_on=False):
        if out_on:
            if self.hw.operational_vacuum and not self.hw.overheated_tc:
                resp = self.send_cmd('OUT 1')
            else:
                raise RuntimeError("System is to hot, shutting down TDK heater.")
        else:
            resp = self.send_cmd('OUT 0')
        if resp != 'OK':
            raise RuntimeError('OUT Response: "{:s}" is not "OK"'.format(resp))
    def set_out_on(self):
        if self.hw.operational_vacuum and not self.hw.overheated_tc:
            resp = self.send_cmd('OUT 1')
        else:
            raise RuntimeError("System is to hot, shutting down TDK heater.")
        if resp != 'OK':
            raise RuntimeError('OUT 1 Response: "{:s}" is not "OK"'.format(resp))
    def set_out_off(self):
        resp = self.send_cmd('OUT 0')
        if resp != 'OK':
            raise RuntimeError('OUT 0 Response: "{:s}" is not "OK"'.format(resp))

    def get_ast(self):
        # gets the auto-restart mode status.
        resp = self.send_cmd('AST?')
        if resp == 'ON':
            return {'auto restart': True}
        elif resp == 'OFF':
            return {'auto restart': False}
        else:
            raise RuntimeError('AST? Response: "{:s}" is not "ON" or "OFF"'.format(resp))

    def get_mode(self):
        return {'control mode': self.send_cmd('MODE?')}

    def get_status(self):
        values = self.send_cmd('STT?').split(',')
        d = {}
        for val in values:
            if val[:2] == 'MV':
                d.update({'voltage measured': float(val[3:-1])})
            elif val[:2] == 'PV':
                d.update({'voltage programmed': float(val[3:-1])})
            elif val[:2] == 'MC':
                d.update({'current measured': float(val[3:-1])})
            elif val[:2] == 'PC':
                d.update({'current programmed': float(val[3:-1])})
            elif val[:2] == 'SR':
                d.update({'status reg': int(val[3:-1])})
            elif val[:2] == 'FR':
                d.update({'fault reg': int(val[3:-1])})
            else:
                raise RuntimeError('STT? resp: "{:s}" is not formatted like: '
                                '"MV(float),PV(float),MC(float),PC(float),SR(hex),FR(hex)"'.format(val))
        return d

    # TODO put coersing limits on program values
    def set_pv(self, volt):
        if volt == 0 or (self.hw.operational_vacuum and not self.hw.overheated_tc):
            resp = self.send_cmd('PV {:0.2f}'.format(volt))
        else:
            self.send_cmd('PV {:0.2f}'.format(0))
            raise RuntimeError("System is too hot or not in vacuum, shutting down TDK heater.")
        if resp != 'OK':
            raise RuntimeError('PV {:0.2f} Response: "{:s}" is not "OK"'.format(volt, resp))

    def set_pc(self, current):
        if current == 0 or (self.hw.operational_vacuum and not self.hw.overheated_tc):
            resp = self.send_cmd('PC {:0.3f}'.format(current))
        else:
            self.send_cmd('PV {:0.2f}'.format(0))
            raise RuntimeError("System is too hot or not in vacuum, shutting down TDK heater.")
        if resp != 'OK':
            raise RuntimeError('Pc {:0.2f} Response: "{:s}" is not "OK"'.format(current, resp))

