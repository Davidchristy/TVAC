from keysight import Keysight
from mcc import Mcc
def main():
    keysight = Keysight()
    keysight.daemon = True
    keysight.start()

    mcc=Mcc()
    mcc.daemon = True
    mcc.start()

    while True:
        pass

if __name__ == '__main__':
    main()