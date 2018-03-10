import time
from Collections.HardwareStatusInstance import HardwareStatusInstance
from Logging.Logging import Logging
from ThreadControls.SafetyCheckHelperFunctions import log_hw_error
from Collections.ProfileInstance import ProfileInstance




def initialize_shi_compressor(compressor):
    hw = HardwareStatusInstance.getInstance()
    pi = ProfileInstance.getInstance()
    # Thread "Start up" stuff goes here
    Logging.logEvent("Debug", "Status Update",
                     {"message": "Power on the Shi Compressor",
                      "level": 3})

    try:
        # This starts the helper thread for reading the fifo file
        compressor.open_port()

        # Waiting until the system is reading the power of the Cryo Pump
        while hw.pc_104.digital_out.getVal('CryoP Pwr Relay 1') is None:
            time.sleep(1)

        # Checks if the power is power is on or not
        currently_powered = hw.pc_104.digital_out.getVal('CryoP Pwr Relay 1')

        # If it's not powered, ask system to turn it on and wait 5 seconds
        # TODO: It might be better to have a loop here, checking until it's on.
        hw.pc_104.digital_out.update({'CryoP Pwr Relay 1': True})
        if not currently_powered:
            print("initialize_shi_compressor: Waiting on currently_powered")
            time.sleep(5)
        print("initialize_shi_compressor: done waiting")


        # This is here to clear any old data that might be in the port, waiting for .2 seconds to allow for HW to reply
        compressor.flush_port(.2)


    except RuntimeError as e:
        item = "Shi Compressor"
        error_details = "ERROR: {}: There has been an error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
        error = True
    except TimeoutError as e:
        HardwareStatusInstance.getInstance().shi_compressor_power = False
        item = "Shi Compressor"
        error_details = "ERROR: {}: There has been a Timeout error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
        error = True
    else:
        HardwareStatusInstance.getInstance().shi_compressor_power = True
        error = False

    comp_next_uptime_read = time.time()
    comp_next_status_read = time.time()

    return error, comp_next_uptime_read, comp_next_status_read


def shi_compressor_update(compressor, comp_next_uptime_read,
                          comp_uptime_period, comp_next_status_read, comp_status_period):
    hw = HardwareStatusInstance.getInstance()
    pi = ProfileInstance.getInstance()
    Logging.logEvent("Debug", "Status Update",
                     {"message": "Reading and writing with ShiCompressorUpdater.",
                      "level": 4})
    try:
        # Check to see if enough time has passed
        if time.time() > comp_next_status_read:
            # Update the next read time
            comp_next_status_read += comp_status_period
            # Create and fill a temp dictionary
            val = {}
            val.update(compressor.get_temperatures())
            val.update(compressor.get_pressure())
            val.update(compressor.get_status_bits())
            if time.time() > comp_next_uptime_read:
                val.update(compressor.get_id())
                comp_next_uptime_read += comp_uptime_period

            # Update "real" version
            hw.shi_cryopump.update_shi_cryopump({'Compressor': val})

        while len(hw.shi_compressor_cmds):
            cmd = hw.shi_compressor_cmds.pop()
            process_compressor_cmd(cmd, compressor)
            # end if/else
        # end while
    except RuntimeError as e:
        item = "Shi Compressor"
        error_details = "ERROR: {}: There has been an error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
        error = True
    except TimeoutError as e:
        HardwareStatusInstance.getInstance().shi_compressor_power = False
        item = "Shi Compressor"
        error_details = "ERROR: {}: There has been a Timeout error with the {} ({})".format(item, item, e)
        log_hw_error(pi=pi, item=item, error_details=error_details)
        error = True
    else:
        HardwareStatusInstance.getInstance().shi_compressor_power = True
        error = False

    return error, comp_next_uptime_read, comp_next_status_read

def process_compressor_cmd(cmd, compressor):
    if 'on' == cmd:
        compressor.set_compressor_on()
    elif 'off' == cmd:
        compressor.set_compressor_off()
    elif 'reset' == cmd:
        compressor.set_reset()
    else:
        raise RuntimeError("Compressor: The given command: ({}) is not in the list of known tdk commands".format(cmd[0]))