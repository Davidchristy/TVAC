import uuid, time, datetime
from DataContracts.ZoneProfileContract import ZoneProfileContract
from Logging.Logging import Logging, insert_into_sql, sql_fetch_one, sql_fetch_all

import Collections.ProfileHelperFunctions as ProfileHelperFunctions

class ProfileInstance:
    # Here will be the instance stored.
    __instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if not ProfileInstance.__instance:
            ProfileInstance()
        return ProfileInstance.__instance

    def __init__(self):
        if ProfileInstance.__instance:
            raise Exception("This class is a singleton!")
        else:
            Logging.logEvent("Debug","Status Update", 
                {"message": "Creating ProfileInstance",
                 "level":2})
            self.zone_dict = self.build_zone_collection()

            self.record_data = False
            self.active_profile = False
            self.vacuum_wanted = False
            self.vacuum_obtained = False

            self.profile_name = None
            self.profile_uuid = None
            self.current_setpoint = None
            self.in_ramp = False
            self.in_hold = False
            self.update_period = 10

            self.profile_start_time = None
            self.thermal_start_time = None
            self.expected_time_values = None
            self.set_points_start_time = None


            self.get_status_from_db()

            # This holds the event list
            self.system_status_queue = []
            self.error_list = []
            
            ProfileInstance.__instance = self

    def get_status_from_db(self):
        sql_str = "SELECT * FROM tvac.System_Status;"
        result = sql_fetch_one(sql_str=sql_str)

        self.in_hold = True if result["in_hold"] else False
        self.in_ramp = True if result["in_ramp"] else False
        self.record_data = True if result["record_data"] else False
        self.vacuum_wanted = True if result["vacuum_wanted"] else False
        self.current_setpoint = result["setpoint"]

    def rebuild_zones(self):
        self.zone_dict = self.build_zone_collection()

    def build_zone_collection(self):
        return {"zone1": ZoneProfileContract(name='zone1', lamps=['IR Lamp 1', 'IR Lamp 2'],   pi=self),
                "zone2": ZoneProfileContract(name='zone2', lamps=['IR Lamp 3', 'IR Lamp 4'],   pi=self),
                "zone3": ZoneProfileContract(name='zone3', lamps=['IR Lamp 6', 'IR Lamp 5'],   pi=self),
                "zone4": ZoneProfileContract(name='zone4', lamps=['IR Lamp 7', 'IR Lamp 8'],   pi=self),
                "zone5": ZoneProfileContract(name='zone5', lamps=['IR Lamp 9', 'IR Lamp 10'],  pi=self),
                "zone6": ZoneProfileContract(name='zone6', lamps=['IR Lamp 12', 'IR Lamp 11'], pi=self),
                "zone7": ZoneProfileContract(name='zone7', lamps=['IR Lamp 13', 'IR Lamp 14'], pi=self),
                "zone8": ZoneProfileContract(name='zone8', lamps=['IR Lamp 15', 'IR Lamp 16'], pi=self),
                "zone9": ZoneProfileContract(name='zone9', lamps=None, pi=self)}

    def load_profile(self, profile_name, profile_start_time=None, thermal_start_time=None):
        """
        This will take a profile loaded in the DB and put it in RAM
        If this is a pre existing profile we are loading after reboot, a startTime will be given
        this is the startTime of the profileInstance that was/will be ran by the ThreadCollection
        """
        if thermal_start_time:
            Logging.debug_print(2, "Loading profile {}:\tpst: {}\ttst: {}".format(profile_name,
                                                                                  profile_start_time,
                                                                                  time.mktime(
                                                                                               thermal_start_time.timetuple()
                                                                                           )))
        else:
            Logging.debug_print(2, "No thermalStartTime")
        try:
            sql_str = "SELECT zone, average, min_heat_error, max_heat_error, max_heat_per_min " \
                  "FROM tvac.Thermal_Zone_Profile WHERE profile_name=\"{}\";".format(
                    profile_name)
            results = sql_fetch_all(sql_str=sql_str)
            if not results:
                return "{'Error':'No profile loaded under that name.'}"

            self.profile_uuid = uuid.uuid4()
            self.profile_name = profile_name
            self.profile_start_time = profile_start_time
            self.thermal_start_time = thermal_start_time

            Logging.debug_print(2, "Loaded profile: {}".format(profile_name))
            # flush all old data, to fill it with new data

            for result in results:
                zone_profile = ProfileHelperFunctions.transform_sql_data_to_zone_profile(profile_name, result, self.profile_uuid)
                zone_name = "zone" + str(result['zone'])
                self.zone_dict[zone_name].update(zone_profile)
                self.zone_dict[zone_name].active_zone_profile = True

            print("Profile Name: {}".format(self.profile_name))
            for zone in self.zone_dict:
                zone = self.zone_dict[zone]
                if zone.active_zone_profile:
                    print("{}: Active".format(zone.name))
                    print("{}: Average: {}".format(zone.name, zone.average))
                    print("{}: Thermocouples: {}".format(zone.name, zone.thermocouples))
                    print("{}: ThermalProfiles:".format(zone.name))
                    if zone.thermalProfiles:
                        for tp in zone.thermalProfiles:
                            print("\t{}: set point: {}".format(zone.name, tp.thermalsetpoint))
                            print("\t{}: temp goal: {}".format(tp.thermalsetpoint, tp.tempGoal))
                            print("\t{}: soak duration: {}".format(tp.thermalsetpoint, tp.soakduration))
                            print("\t{}: ramp: {}".format(tp.thermalsetpoint, tp.ramp))
                    print("{}: maxHeatError: {}".format(zone.name, zone.maxHeatError))
                    print("{}: minHeatError: {}".format(zone.name, zone.minHeatError))
                    print("{}: maxHeatPerMin: {}".format(zone.name, zone.maxHeatPerMin))
                    print("")

                else:
                    print("{}: Inactive".format(zone.name))
                    print("{}: Average: {}".format(zone.name, zone.average))
                    print("{}: Thermocouples: {}".format(zone.name, zone.thermocouples))
                    print("{}: ThermalProfiles:".format(zone.name))
                    if zone.thermalProfiles:
                        for tp in zone.thermalProfiles:
                            print("\t{}: set point: {}".format(zone.name, tp.thermalsetpoint))
                            print("\t{}: temp goal: {}".format(tp.thermalsetpoint, tp.tempGoal))
                            print("\t{}: soak duration: {}".format(tp.thermalsetpoint, tp.soakduration))
                            print("\t{}: ramp: {}".format(tp.thermalsetpoint, tp.ramp))
                    print("{}: maxHeatError: {}".format(zone.name, zone.maxHeatError))
                    print("{}: minHeatError: {}".format(zone.name, zone.minHeatError))
                    print("{}: maxHeatPerMin: {}".format(zone.name, zone.maxHeatPerMin))
                    print("")

            return "{'result':'success'}"
        except Exception as e:
            return {'result': '{}'.format(str(e))}

    def update_thermal_start_time(self, thermal_start_time):
        """
        This is a helper function that is called either when a profile begins the
        thermal section (when it is in a vacuum) or when the the server is restarted.
        """
        current_temps_str = ProfileHelperFunctions.find_current_temps(self.zone_dict)

        # Since the input for the Profile_Instance is happening in a different thread,
        # There is no guarantee it will be there when this is called, thus, put a loop and wait for it to be there.
        # There will only ever be one or None Profile_Instance with an endtime of Null,
        # and it must be 1 when this is called
        while True:
            sql_str = "SELECT * FROM tvac.Profile_Instance WHERE endTime IS NULL;"
            result = sql_fetch_one(sql_str=sql_str)
            if result:
                break

        sql_str = "UPDATE tvac.Profile_Instance set thermal_Start_Time=\"{}\",{} where thermal_Start_Time is null;".format(
            datetime.datetime.fromtimestamp(thermal_start_time), current_temps_str)

        insert_into_sql(sql_str)

        self.thermal_start_time = thermal_start_time