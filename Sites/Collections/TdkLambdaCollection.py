import threading
from datetime import datetime
import os

from DataContracts.TdkLambdaContract import TdkLambdaContract

from Logging.Logging import Logging


def build_tdk_collection():
    power_supplies = [TdkLambdaContract(1, 'Platen Left'),
                      TdkLambdaContract(2, 'Platen Right'),
                      TdkLambdaContract(3, 'Shroud Left'),
                      TdkLambdaContract(4, 'Shroud Right')]
    return power_supplies


class TdkLambdaCollection:

    __lock = threading.RLock()

    def __init__(self):
        Logging.logEvent("Debug","Status Update",
                {"message": "Creating TDK Lambda DC Power Supplies Collection ",
                 "level": 2})
        self.tdk_lambda_ps = build_tdk_collection()
        self.time = datetime.now()

    def get_platen_left_addr(self):
        return self.tdk_lambda_ps[0].GetAddress()

    def get_platen_right_addr(self):
        return self.tdk_lambda_ps[1].GetAddress()

    def get_shroud_left_addr(self):
        return self.tdk_lambda_ps[2].GetAddress()

    def get_shroud_right_addr(self):
        return self.tdk_lambda_ps[3].GetAddress()

    def get_platen_left(self):
        return self.tdk_lambda_ps[0]

    def get_platen_right(self):
        return self.tdk_lambda_ps[1]

    def get_shroud_left(self):
        return self.tdk_lambda_ps[2]

    def get_shroud_right(self):
        return self.tdk_lambda_ps[3]

    def get_val(self, addr, name):
        return self.get_ps(addr).get_val(name)

    def update_tdk_lambda(self, ps_list):
        self.__lock.acquire()
        self.time = datetime.now()
        self.__lock.release()
        for update_ps in ps_list:
            ps = self.get_ps(update_ps['addr'])
            ps.update(update_ps)

    def get_ps(self, n):
        for ps in self.tdk_lambda_ps:
            if ps.GetAddress() == n:
                return ps
        raise RuntimeError('TDK Lambda Address #: %s is out of range' % n)

    def getJson(self):
        message = []
        self.__lock.acquire()
        message.append('{"time":%s,' % self.time)
        self.__lock.release()
        message.append('PGs:[%s]' %','.join([ps.getJson() for ps in self.tdk_lambda_ps]))
        message.append('}')
        return ''.join(message)
