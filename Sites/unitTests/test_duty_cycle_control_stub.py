from unittest import TestCase
from ThreadControls.controlStubs.DutyCycleControlStub import *
from DataContracts.ThermalProfileContract import ThermalProfileContract

# Helper code...shouldn't have to if used functions p=
def set_thermal_profiles(thermal_profiles):
    new_list = []
    for profile in thermal_profiles:
        new_list.append(ThermalProfileContract(profile))
    return new_list

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
        expected_temp_values = create_expected_temp_values(set_points, interval_time, zone_number, start_time=None,
                                                           get_zone_temp_fun=zone_temp)
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
        expected_temp_values = create_expected_temp_values(set_points, interval_time, zone_number, start_time=None,
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
        expected_temp_values = create_expected_temp_values(set_points, interval_time, zone_number, start_time=None,
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
        expected_temp_values = create_expected_temp_values(set_points, interval_time, zone_number, start_time=None,
                                                           get_zone_temp_fun=zone_temp)
        known_out = [291.6666666666667, 283.3333333333333, 275.0, 266.6666666666667, 258.3333333333333, 250]
        self.assertEqual(expected_temp_values, known_out)
