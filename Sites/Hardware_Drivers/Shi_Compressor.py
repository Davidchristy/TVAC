import time
from PyCRC_master.PyCRC.CRC16 import CRC16
from Hardware_Drivers.tty_reader import TTY_Reader

class ShiCompressor:

    def __init__(self):
        self.port = None
        self.port_listener = TTY_Reader(None, name="ShiCompressorReader")
        self.port_listener.daemon = True
        self.crc = CRC16(modbus_flag=True).calculate

    def open_port(self):
        self.port = open('/dev/ttyxuart1', 'r+b', buffering=0)
        self.port_listener.get_fd(self.port)
        try:
            self.port_listener.start()
        except RuntimeError:
            pass
        self.port_listener.flush_buffer(1.0)

    def flush_port(self, wait_time = 0.0):
        self.port_listener.flush_buffer(wait_time)

    def close_port(self):
        if not self.port.closed:
            self.port.close()

    def send_compressor_cmd(self, command):
        # Tries and sends the command three times before error-ing out
        for tries in range(1,4):
            msg = "${:s}".format(command)
            msg1 = "{:s}{:04X}\r".format(msg, self.crc(msg))

            # Writes the message to the FIFO file here
            self.port.write(msg1.encode())

            # Holds here for 1 second before calling it a timeout error
            resp = self.port_listener.read_line(1.0)
            resp = resp.strip()

            if self.valid_response(resp, command):
                break
            time.sleep(.1 * tries)
        else:
            raise TimeoutError("Timeout Error: Shi Compressor not replying, last command: {}".format(command))

        # Formatting into string
        data = resp.split(",")
        return data[1:-1]

    def valid_response(self, response, cmd):
        """
        A helper function to test if the reply from the Compressor is valid
        :param response:
        :param cmd:
        :return:
        """
        if len(response) < 4:  # Timeout occurred
            self.port_listener.flush_buffer(2.0)
            print("Compressor: Reply is less than 4 chars in length: '{}'".format(response.replace('\r', r'\r')))
            return False
        if response[0] != '$':
            print("Compressor: '$' is not the first byte!: '{}'".format(response.replace('\r', r'\r')))
            return False
        if not (cmd in response):
            print("Compressor: cmd in response: '{}'".format(response.replace('\r', r'\r')))
            return False
        if response.strip()[-4:] != '{:04X}'.format(self.crc(response[:-4])):
            print("Compressor: Checksum is incorrect. Expected: {:04X}    recieved: {}".format(
                self.crc(response[:-4]), response.strip()[-4:]))
            return False
        data = response.split(',')
        if len(data) < 2:
            print("Compressor: data is not long enough")
            return False
        return True  # Yea!! response seems ok

    def get_temperatures(self):
        # $TEA: Read all temperatures
        # Command with checksum and carriage return = $TEAA4B9<cr>
        # Response: $TEA,T1,T2,T3,T4,<crc-16><cr>
        # Default output is in Celsius - so converted to Kelvin
        resp = self.send_compressor_cmd('TEA')
        return {'Helium Discharge Temperature': int(resp[0])+273,
                'Water Outlet Temperature': int(resp[1])+273,
                'Water Inlet Temperature': int(resp[2])+273,
                }

    def get_pressure(self):
        # $PRn: Read selected pressure (n = 1 or 2)
        # Command with checksum and carriage return = $PR171F6<cr> or $PR270B6<cr>
        # Response: $PRn,Pn,<crc-16><cr>  Pn is the pressure in psig
        resp = self.send_compressor_cmd('PR1')
        return {'Helium Return Pressure': int(resp[0])}

    def get_id(self):
        resp = self.send_compressor_cmd('ID1')
        return {'Firmware Version': resp[0],
                'Operating Hours Elapsed': float(resp[1]),
                }

    def get_status_bits(self):
        resp = int(self.send_compressor_cmd('STA')[0], 16)
        return {'RS-232 Config': 'Read Only' if resp & 0x8000 else 'Command and Read',
                'Solenoid ON':       True if resp & 0x100 else False,
                'Pressure Alarm':    True if resp & 0x80 else False,
                'Oil Level Alarm':   True if resp & 0x40 else False,
                'Water Flow Alarm':  True if resp & 0x20 else False,
                'Water Temp Alarm':  True if resp & 0x10 else False,
                'Helium Temp Alarm': True if resp & 0x8 else False,
                'Phase/Fuse Alarm':  True if resp & 0x4 else False,
                'Motor Temp Alarm': True if resp & 0x2 else False,
                'System ON':         True if resp & 0x1 else False,
                'Op-State':  {0: '0 - Local Off',
                              1: '1 - Local ON',
                              2: '2 - Remote Off',
                              3: '3 - Remote ON',
                              4: '4 - Cold Head Run',
                              5: '5 - Cold Head Pause',
                              6: '6 - Fault Off',
                              7: '7 - Oil Fault Off'}[(resp & 0xe00) >> 9]}

    def set_compressor_on(self):
        resp = self.send_compressor_cmd('ON1')
        return resp

    def set_compressor_off(self):
        resp = self.send_compressor_cmd('OFF')
        return resp

    def set_reset(self):
        resp = self.send_compressor_cmd('RS1')
        return resp