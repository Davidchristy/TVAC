import unittest
from Controllers import PostControl

class MyTestCase(unittest.TestCase):
    def test_load_profile(self):
        print("test_get_tvac_status")
        data = {"profile_name": "test"}
        results = PostControl.load_profile(data)
        print(results)

    def test_save_profile(self):
        print("save_profile")
        data = {"Test": "data"}
        results = PostControl.save_profile(data)
        print(results)

    # def test_run_single_profile(self):
    #     print("run_single_profile")
    #     data = {"Test": "data"}
    #     results = PostControl.run_single_profile(data)
    #     print(results)

    def test_pause_single_thread(self):
        print("pause_single_thread")
        data = {"Test": "data"}
        results = PostControl.pause_single_thread(data)
        print(results)

    def test_remove_pause_single_thread(self):
        print("remove_pause_single_thread")
        data = {"Test": "data"}
        results = PostControl.remove_pause_single_thread(data)
        print(results)

    def test_hold_single_thread(self):
        print("hold_single_thread")
        data = {"Test": "data"}
        results = PostControl.hold_single_thread(data)
        print(results)

    def test_release_hold_single_thread(self):
        print("release_hold_single_thread")
        data = {"Test": "data"}
        results = PostControl.release_hold_single_thread(data)
        print(results)

    # def test_abort_single_thread(self):
    #     print("abort_single_thread")
    #     data = {"Test": "data"}
    #     results = PostControl.abort_single_thread(data)
    #     print(results)

    # def test_calculate_ramp(self):
    #     print("calculate_ramp")
    #     data = {"Test": "data"}
    #     results = PostControl.calculate_ramp(data)
    #     print(results)

    def test_send_hw_cmd(self):
        print("send_hw_cmd")
        data = {"Test": "data"}
        results = PostControl.send_hw_cmd(data)
        print(results)

    def test_set_pc_104_digital(self):
        print("set_pc_104_digital")
        data = {"Test": "data"}
        results = PostControl.set_pc_104_digital(data)
        print(results)

    def test_set_pc_104_analog(self):
        print("set_pc_104_analog")
        data = {"Test": "data"}
        results = PostControl.set_pc_104_analog(data)
        print(results)

    def test_heat_up_shroud(self):
        print("heat_up_shroud")
        data = {"dutyCycle": "0"}
        results = PostControl.heat_up_shroud(data)
        print(results)

    def test_heat_up_platen(self):
        print("heat_up_platen")
        data = {"dutyCycle": "0"}
        results = PostControl.heat_up_platen(data)
        print(results)

if __name__ == '__main__':
    unittest.main()
