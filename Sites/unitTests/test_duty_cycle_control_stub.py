from unittest import TestCase
import ThreadControls.controlStubs.HelperFuctions.dutyCycleFunctions as dutyCycleFunctions
from DataContracts.ThermalProfileContract import ThermalProfileContract
from DataContracts.ZoneProfileContract import ZoneProfileContract
from Collections.ProfileInstance import ProfileInstance
from DataContracts.ThermocoupleContract import ThermocoupleContract
from ThreadControls.controlStubs.DutyCycleControlStub import DutyCycleControlStub

# Helper code...shouldn't have to if used functions p=
def set_thermal_profiles(thermal_profiles):
    new_list = []
    for profile in thermal_profiles:
        new_list.append(ThermalProfileContract(profile))
    return new_list


def generate_test_pi(pi):
    pi.zone_dict = {
        "zone1": ZoneProfileContract(name='zone1', lamps=['IR Lamp 1', 'IR Lamp 2'], pi=pi),
        "zone2": ZoneProfileContract(name='zone2', lamps=['IR Lamp 3', 'IR Lamp 4'], pi=pi)
    }
    pi.update_period = 10
    pi.thermal_start_time = 0
    zone_temp = lambda _: 400
    temp_zone = pi.zone_dict['zone1']
    profiles = [
        {
            "thermalsetpoint": 1,
            "tempgoal": 100,
            "soakduration": 30,
            "ramp": 50,
        },
        {
            "thermalsetpoint": 2,
            "tempgoal": 200,
            "soakduration": 70,
            "ramp": 20,
        }
    ]
    set_points = set_thermal_profiles(profiles)
    temp_zone.activeZoneProfile = True
    temp_zone.maxHeatPerMin = 60
    temp_zone.zone = 1
    temp_zone.thermalProfiles = set_points
    temp_zone = pi.zone_dict['zone2']
    profiles = [
        {
            "thermalsetpoint": 1,
            "tempgoal": 100,
            "soakduration": 30,
            "ramp": 50,
        },
        {
            "thermalsetpoint": 2,
            "tempgoal": 200,
            "soakduration": 70,
            "ramp": 20,
        }
    ]
    set_points = set_thermal_profiles(profiles)
    temp_zone.activeZoneProfile = True
    temp_zone.maxHeatPerMin = 60
    temp_zone.zone = 2
    temp_zone.thermalProfiles = set_points
    return zone_temp


class TestDuty_cycle_control(TestCase):

    def test_create_expected_temp_values(self):
        interval_time = 10
        zone_number = 1
        zone_temp = lambda _: 0
        profiles = [
            {
                "thermalsetpoint": 1,
                "tempgoal": 100,
                "soakduration": 30,
                "ramp": 50,
            }
        ]
        set_points = set_thermal_profiles(profiles)
        expected_temp_values = dutyCycleFunctions.create_expected_temp_values(set_points, interval_time, zone_number, start_time=None,get_zone_temp_fun=zone_temp)
        known_out = [20.0, 40.0, 60.0, 80.0, 100, 100, 100]
        self.assertEqual(expected_temp_values, known_out)

        interval_time = 5
        zone_number = 1
        zone_temp = lambda _: 0
        profiles = [
            {
                "thermalsetpoint": 1,
                "tempgoal": 100,
                "soakduration": 30,
                "ramp": 50,
            }
        ]
        set_points = set_thermal_profiles(profiles)
        expected_temp_values = dutyCycleFunctions.create_expected_temp_values(set_points, interval_time, zone_number, start_time=None,
                                                           get_zone_temp_fun=zone_temp)
        known_out = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100, 100, 100, 100, 100, 100]
        self.assertEqual(expected_temp_values, known_out)

        interval_time = 10
        zone_number = 1
        zone_temp = lambda _: 300
        profiles = [
            {
                "thermalsetpoint": 1,
                "tempgoal": 350,
                "soakduration": 10,
                "ramp": 60,
            }
        ]
        set_points = set_thermal_profiles(profiles)
        expected_temp_values = dutyCycleFunctions.create_expected_temp_values(set_points, interval_time, zone_number, start_time=None,
                                                           get_zone_temp_fun=zone_temp)
        known_out = [308.3333333333333, 316.6666666666667, 325.0, 333.3333333333333, 341.6666666666667, 350]
        self.assertEqual(expected_temp_values, known_out)

        interval_time = 10
        zone_number = 1
        zone_temp = lambda _: 300
        profiles = [
            {
                "thermalsetpoint": 1,
                "tempgoal": 250,
                "soakduration": 10,
                "ramp": 60,
            }
        ]
        set_points = set_thermal_profiles(profiles)
        expected_temp_values = dutyCycleFunctions.create_expected_temp_values(set_points, interval_time, zone_number, start_time=None,
                                                           get_zone_temp_fun=zone_temp)
        known_out = [291.6666666666667, 283.3333333333333, 275.0, 266.6666666666667, 258.3333333333333, 250]
        self.assertEqual(expected_temp_values, known_out)

    def test_create_expected_time_values(self):
        interval_time = 10
        current_time = lambda : 0
        profiles = [
            {
                "thermalsetpoint": 1,
                "tempgoal": 100,
                "soakduration": 30,
                "ramp": 50,
            }
        ]
        set_points = set_thermal_profiles(profiles)
        expected_time_values = dutyCycleFunctions.create_expected_time_values(set_points,
                                                                              interval_time,
                                                                              start_time=None,
                                                                              time_func=current_time)

        known_out = [10, 20, 30, 40, 50, 60, 70]
        self.assertEqual(expected_time_values, known_out)

    def test_create_expected_set_start_times(self):
        current_time = lambda: 0
        profiles = [
            {
                "thermalsetpoint": 1,
                "tempgoal": 100,
                "soakduration": 30,
                "ramp": 50,
            },
            {
                "thermalsetpoint": 2,
                "tempgoal": 100,
                "soakduration": 40,
                "ramp": 50,
            }
        ]
        set_points = set_thermal_profiles(profiles)
        expected_set_start_times = dutyCycleFunctions.create_expected_set_start_times(set_points,
                                                                              start_time=None,
                                                                              time_func=current_time)

        known_out = [[0, 50], [80, 130]]
        self.assertEqual(expected_set_start_times, known_out)

    def test_create_expected_values(self):
        pi = ProfileInstance.getInstance()
        zone_temp = generate_test_pi(pi)
        current_time = lambda :10

        dutyCycleFunctions.create_expected_values(pi, zone_temp, time_func = current_time)

        self.assertEqual(pi.zone_dict["zone2"].max_temp_rise_per_update, 10)
        known_temp_values = dutyCycleFunctions.create_expected_temp_values(pi.zone_dict["zone2"].thermalProfiles,
                                                                           pi.update_period,
                                                                           pi.zone_dict["zone2"].zone,
                                                                           start_time=None,
                                                                           get_zone_temp_fun=zone_temp)
        self.assertEqual(pi.zone_dict["zone2"].expected_temp_values,known_temp_values)

        known_time_values = dutyCycleFunctions.create_expected_time_values(pi.zone_dict["zone2"].thermalProfiles,
                                                                           pi.update_period,
                                                                           start_time=None,
                                                                           time_func=current_time)
        self.assertEqual(pi.expected_time_values,known_time_values)

    def test_calculate_duty_cycle(self):
        pi = ProfileInstance.getInstance()
        pi.update_period = 10
        zone = ZoneProfileContract(name='zone1', lamps=['IR Lamp 1', 'IR Lamp 2'],pi=pi)
        zone.maxHeatPerMin = 60
        zone.average = "Average"
        zone.thermocouples = [1]
        zone.temp_temperature = 100

        tcs = [ThermocoupleContract(1),
               ThermocoupleContract(2)]
        tcs[0].temp = 100
        tcs[1].temp = float("NaN")

        zone.thermocouples = tcs


        zone.calculate_duty_cycle(pi)

        self.assertEqual(zone.duty_cycle, .5)

    def test_check_hold(self):
        pi = ProfileInstance.getInstance()
        current_time = lambda :0
        hold_func = lambda _=0:10
        zone_temp_func = lambda _: 0

        pi.in_hold = True
        pi.thermal_start_time = 0

        zone_temp = generate_test_pi(pi)

        dutyCycleFunctions.create_expected_values(pi, zone_temp, time_func = current_time)

        known_out = [10, 20, 30, 40, 50, 60, 70]
        self.assertEqual(pi.expected_time_values, known_out)

        dutyCycleFunctions.check_hold(pi=pi,
                                      time_func=current_time,
                                      hold_func=hold_func,
                                      zone_temp_func=zone_temp_func)

        known_out = [20, 30, 40, 50, 60, 70, 80]
        self.assertEqual(pi.expected_time_values, known_out)

    def test_find_num_of_updates_passed(self):
        expected_time_values = [10, 20, 30, 40, 50, 60, 70]
        current_time =11
        updates = dutyCycleFunctions.find_num_of_updates_passed(expected_time_values,current_time)
        self.assertEqual(updates, 3)

    def test_update_current_temp_value(self):
        pi = ProfileInstance.getInstance()
        current_time = 31
        zone_temp = generate_test_pi(pi)
        current_time_func = lambda :10

        dutyCycleFunctions.create_expected_values(pi, zone_temp, time_func = current_time_func)

        updates = dutyCycleFunctions.find_num_of_updates_passed(pi.expected_time_values,current_time)


        pi.zone_dict["zone1"].expected_temp_values
        dutyCycleFunctions.update_current_temp_value(pi, updates)
        pi.zone_dict["zone1"].expected_temp_values

    def test_find_current_set_point(self):
        pi = ProfileInstance.getInstance()
        zone_temp = generate_test_pi(pi)
        current_time_func = lambda :0
        current_time = 81

        dutyCycleFunctions.create_expected_values(pi, zone_temp, time_func = current_time_func)
        known_out = [[0, 50], [80, 100]]
        self.assertEqual(pi.set_points_start_time, known_out)
        setpoint = dutyCycleFunctions.find_current_set_point(pi.set_points_start_time, current_time)
        self.assertEqual(1, setpoint)