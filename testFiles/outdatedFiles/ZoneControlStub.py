import math, datetime, time

from PID.PID import PID
from Collections.ProfileInstance import ProfileInstance
from Logging.Logging import Logging
from Collections.HardwareStatusInstance import HardwareStatusInstance





class ZoneControlStub:
    def __init__(self, name, lamps=None, parent=None):
        Logging.logEvent("Debug","Status Update",
        {"message": "Creating ZoneControlStub: {}".format(name),
         "level":3})

        self.zone_profile = ProfileInstance.getInstance().zoneProfiles.getZone(name)
        self.duty_cycle = None

        self.lamps = lamps
        self.name = name
        self.parent = parent
        self.temp_temperature = None

        self.pid = PID()
        if lamps:
            # These are the PID settings for the lamps
            proportional_gain = .2
            integral_gain = 0
            derivative_gain = 0
        else:
            # These are the PID settings for the heaters in the platen
            proportional_gain = .4
            integral_gain = 0
            derivative_gain = 0

        self.pid.setKp(proportional_gain)
        self.pid.setKi(integral_gain)
        self.pid.setKd(derivative_gain)
    # end init

