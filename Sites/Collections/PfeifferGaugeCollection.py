import threading
from datetime import datetime
import os

from DataContracts.PfeifferGaugeContract import PfeifferGaugeContract

from Logging.Logging import Logging


class PfeifferGaugeCollection:

    __lock = threading.RLock()

    def __init__(self):
        Logging.logEvent("Debug","Status Update",
                {"message": "Creating PfeifferGaugeCollection",
                 "level": 2})
        self.pfGuageList = self.buildCollection()
        self.time = datetime.now()


    def buildCollection(self):
        guages = [PfeifferGaugeContract(1, 'Chamber'),
                  PfeifferGaugeContract(2, 'Cryopump'),
                  PfeifferGaugeContract(3, 'Roughing Pump')]
        return guages

    def get_pressure_chamber(self):
        return self.pfGuageList[0].getPressure()

    def get_pressure_cryopump(self):
        return self.pfGuageList[1].getPressure()

    def get_pressure_roughpump(self):
        return self.pfGuageList[2].getPressure()

    def update(self, pgList):
        self.__lock.acquire()
        self.time = datetime.now()
        self.__lock.release()
        for updatePG in pgList:
            # Why is this tc? should this be Guage?
            tc = self.getPG(updatePG['addr'])
            tc.update(updatePG)

    def getPG(self, n):
        for pg in self.pfGuageList:
            if pg.GetAddress() == n:
                return pg
        raise RuntimeError('Pfeiffer gauge #: %s is out of range' % n)

    def getJson(self):
        message = []
        self.__lock.acquire()
        message.append('{"time":%s,' % self.time)
        self.__lock.release()
        message.append('PGs:[%s]' %','.join([pg.getJson() for pg in self.pfGuageList]))
        message.append('}')
        return ''.join(message)
