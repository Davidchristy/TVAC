import uuid


from Logging.Logging import Logging




class ZoneCollection:
    def __init__(self, parent):
        Logging.debugPrint(2,"Creating ZoneCollection")
        # self.zone_dict = build_zone_collection()
        self.profile_uuid = uuid.uuid4()
        self.parent = parent

        # self.update_period = 10
        # self.profile_name = None
        # self.thermal_start_time = None
        # self.expected_time_values = None
        # self.set_points_start_time = None




    def getZone(self,d):
        return self.zone_dict[d]

    def get_zones_data_json(self):
        '''
        This returns a json string of the currently loaded profile 
        '''
        return ('{"profileuuid":"%s","updateperiod":%s,"profile":[ %s ]}' % (self.profile_uuid,self.parent.update_period,self.fill_zones()))

    def fill_zones(self):
        '''password
        This is a helper function for getJson()
        '''
        message = []
        zone_len = len(self.zone_dict)
        count = 0
        for zone in self.zone_dict:
            message.append(self.zone_dict[zone].getJson())
            if count < (zone_len - 1):
                message.append(',')
                count = count + 1
        return ''.join(message)
