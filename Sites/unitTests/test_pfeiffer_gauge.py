import unittest
from Hardware_Drivers.PfeifferGauge import *

class MyTestCase(unittest.TestCase):
    def test_send_receive(self):
        address = 1
        real_value = send_receive(address, parm=349, data_str=None)
        expected_value = ""
        self.assertEqual(expected_value, real_value)



if __name__ == '__main__':
    unittest.main()
