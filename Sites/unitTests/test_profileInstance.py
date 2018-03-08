from unittest import TestCase
import Collections.ProfileHelperFunctions as ProfileHelperFunctions
from Collections.ProfileInstance import ProfileInstance
from decimal import *
from uuid import UUID

class TestProfileInstance(TestCase):
    def test_load_profile(self):
        pi = ProfileInstance.getInstance()
        pi.load_profile(profile_name="newProfileLayout")

        self.assertEqual(pi.profile_name, "newProfileLayout")
        self.assertEqual(pi.profile_start_time, None)

        # Changed data:
            # self.profile_name = profile_name
            # self.profile_start_time = profileStartTime
            # self.thermal_start_time
            # self.vacuum_wanted
            # self.active_profile

            # All zones edited
            # self.zone_dict[zone_name]

    def test_transform_sql_data_to_zone_profile(self):
        profile_name = "Test001"
        test_result = {
            'zone': 1,
            'average': 'Max',
            'max_heat_error': Decimal('350.0000'),
            'max_heat_per_min': Decimal('6.4000'),
            'min_heat_error': Decimal('10.0000')
        }
        zone_profile = ProfileHelperFunctions.transform_sql_data_to_zone_profile(profile_name, test_result)
        expected_result = {
            'thermalprofiles': [],
            'profileuuid': None,
            'min_heat_error': Decimal('10.0000'),
            'thermocouples': [],
            'average': 'Max',
            'max_heat_per_min': Decimal('6.4000'),
            'zoneuuid': UUID('189f6194-f943-4310-b13c-e2a7950a196e'),
            'zone': 1,
            'max_heat_error': Decimal('350.0000')
        }

        self.assertEqual(zone_profile["average"], expected_result["average"])
        self.assertEqual(zone_profile["max_heat_per_min"], expected_result["max_heat_per_min"])
        self.assertEqual(zone_profile["min_heat_error"], expected_result["min_heat_error"])
        self.assertEqual(zone_profile["zone"], expected_result["zone"])
        self.assertEqual(zone_profile["max_heat_error"], expected_result["max_heat_error"])


test_thermal_profile_sql_result = [
    {
        'zone': 1,
        'average': 'Max',
        'max_heat_error': Decimal('350.0000'),
        'max_heat_per_min': Decimal('6.4000'),
        'min_heat_error': Decimal('10.0000')
    }
]

test_zone_profile_sql_data = [
    {
        'zone': 1,
        'ramp_time': 30,
        'profile_name': 'newProfileLayout',
        'soak_time': 30,
        'set_point': 0,
        'temp_goal': Decimal('10.0000')
     },
     {
         'zone': 1,
         'ramp_time': 300,
         'profile_name': 'newProfileLayout',
         'soak_time': 300,
         'set_point': 1,
         'temp_goal': Decimal('20.0000')
     }, {
        'zone': 1,
        'ramp_time': 300,
        'profile_name': 'newProfileLayout',
        'soak_time': 300,
        'set_point': 2,
        'temp_goal': Decimal('30.0000')
    }, {
        'zone': 1,
        'ramp_time': 300,
        'profile_name': 'newProfileLayout',
        'soak_time': 300,
        'set_point': 3,
        'temp_goal': Decimal('22.0000')
    }, {
        'zone': 1,
        'ramp_time': 30,
        'profile_name': 'newProfileLayout',
        'soak_time': 30,
        'set_point': 4,
        'temp_goal': Decimal('22.0000')
    }
]



test_thermal_profiles = [
    {
        'thermalsetpoint': 0,
        'ramp': 30,
        'tempgoal': 10.0,
        'soakduration': 30
    }, {
        'thermalsetpoint': 1,
        'ramp': 300,
        'tempgoal': 20.0,
        'soakduration': 300
    }, {
        'thermalsetpoint': 2,
        'ramp': 300,
        'tempgoal': 30.0,
        'soakduration': 300
    }, {
        'thermalsetpoint': 3,
        'ramp': 300,
        'tempgoal': 22.0,
        'soakduration': 300
    }, {
        'thermalsetpoint': 4,
        'ramp': 30,
        'tempgoal': 22.0,
        'soakduration': 30
    }
]

test_tc_profile_sql_result =  [
    {'profile_name': 'newProfileLayout',
     'zone': 1,
     'thermocouple': 1}
]

test_zone_profile = {
    'thermocouples': [1],
    'zoneuuid': UUID('3abbc1a6-26a1-40ac-80d8-8704d788ed20'),
    'min_heat_error': Decimal('10.0000'),
    'max_heat_error': Decimal('350.0000'),
    'average': 'Max',
    'profileuuid': UUID('3ac61d8c-bd43-4220-9e22-1f2dfb31fdd2'),
    'max_heat_per_min': Decimal('6.4000'),
    'zone': 1,
    'thermalprofiles': [
        {
            'ramp': 30,
            'soakduration': 30,
            'thermalsetpoint': 0,
            'tempgoal': 10.0
         }, {
            'ramp': 300,
            'soakduration': 300,
            'thermalsetpoint': 1,
            'tempgoal': 20.0
        }, {
            'ramp': 300,
            'soakduration': 300,
            'thermalsetpoint': 2,
            'tempgoal': 30.0
        }, {
            'ramp': 300,
            'soakduration': 300,
            'thermalsetpoint': 3,
            'tempgoal': 22.0
        }, {
            'ramp': 30,
            'soakduration': 30,
            'thermalsetpoint': 4,
            'tempgoal': 22.0
        }
    ]
}