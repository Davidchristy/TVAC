import unittest
from Controllers import GetControl

class MyTestCase(unittest.TestCase):
    def test_get_tvac_status(self):
        print("test_get_tvac_status")
        results = GetControl.get_tvac_status()
        print(results)

    def test_get_vacuum_state(self):
        results = GetControl.get_vacuum_state()
        # print(results)

    def test_abort_regen_cycle(self):
        results = GetControl.abort_regen_cycle()
        # print(results)

    def test_stop_recording_data(self):
        results = GetControl.stop_recording_data()
        # print(results)

    def test_record_data(self):
        results = GetControl.record_data()
        # print(results)

    def test_run_profile(self):
        results = GetControl.run_profile()
        # print(results)

    def test_get_zone_temps(self):
        results = GetControl.get_zone_temps()
        # print(results)

    def test_get_pressure_gauges(self):
        results = GetControl.get_pressure_gauges()
        # print(results)

    def test_get_pc104_analog(self):
        results = GetControl.get_pc104_analog()
        # print(results)

    def test_get_pc104_switches(self):
        results = GetControl.get_pc104_switches()
        # print(results)

    def test_get_pc104_digital(self):
        results = GetControl.get_pc104_digital()
        # print(results)

    def test_get_cryopump_plots(self):
        results = GetControl.get_cryopump_plots()
        # print(results)

    def test_get_cryopump_params(self):
        results = GetControl.get_cryopump_params()
        # print(results)

    def test_get_cryopump_status(self):
        results = GetControl.get_cryopump_status()
        # print(results)

    def test_get_event_list(self):
        results = GetControl.get_event_list()
        # print(results)

    def test_get_shi_temps(self):
        results = GetControl.get_shi_temps()
        # print(results)

    def test_hard_stop(self):
        results = GetControl.hard_stop()
        # print(results)

    def test_get_last_error(self):
        results = GetControl.get_last_error()
        # print(results)

    def test_get_all_zone_data(self):
        results = GetControl.get_all_zone_data()
        # print(results)

    def test_stop_roughing_pump(self):
        results = GetControl.stop_roughing_pump()
        # print(results)

    def test_stop_cryopump(self):
        results = GetControl.stop_cryopump()
        # print(results)

    def test_stop_cryopumping_chamber(self):
        results = GetControl.stop_cryopumping_chamber()
        # print(results)

    def test_vacuum_not_needed(self):
        results = GetControl.vacuum_not_needed()
        # print(results)

    def test_un_hold_all_zones(self):
        results = GetControl.un_hold_all_zones()
        # print(results)

    def test_resume_all_zones(self):
        results = GetControl.resume_all_zones()
        # print(results)

    def test_pause_all_zones(self):
        results = GetControl.pause_all_zones()
        # print(results)

    def test_hold_all_zones(self):
        results = GetControl.hold_all_zones()
        # print(results)

    def test_get_all_thermocouple_data(self):
        results = GetControl.get_all_thermocouple_data()
        print(results)

    def test_put_under_vacuum(self):
        results = GetControl.put_under_vacuum()
        print(results)

    # def test_check_tread_status(self):
    #     results = GetControl.check_tread_status()
    #     print(results)

    def test_chamber_door_status(self):
        results = GetControl.chamber_door_status()
        print(results)

if __name__ == '__main__':
    unittest.main()
