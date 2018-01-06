import time

def main():
    sleep_time = .1
    duty_cycle_time = 10

    tcs_in_zones = {1: [1],
                    2: [2]}

    while True:
        f_zones = open("hw-files/zones_duty_cycles.txt", "r")
        f_tcs = open("hw-files/thermocouples.txt", "r+")
        tcs = []
        for line in f_tcs:
            tcs.append(line.strip())
        duty_cycles = {}
        for line in f_zones:
            # 0 is zone
            # 1 is current duty cycle
            # 2 is max temp raise per duty cycle
            duty_cycles[int(line.split(",")[0])] = (float(line.split(",")[1].strip()),float(line.split(",")[2].strip()))
        f_zones.close()

        for duty_cycle in duty_cycles:
            for tc in tcs_in_zones.get(duty_cycle,[]):
                duty_cycle_delta = (duty_cycles[duty_cycle][0]*duty_cycles[duty_cycle][1])
                final_delta = duty_cycle_delta * (sleep_time * duty_cycle_time)
                tcs[tc - 1] = float(tcs[tc - 1]) + final_delta

        print(tcs)
        print(duty_cycles)
        f_tcs.seek(0)
        f_tcs.truncate()
        f_tcs.write('\n'.join(map(str, tcs)))
        f_tcs.close()

        time.sleep(sleep_time)
if __name__ == '__main__':
    main()