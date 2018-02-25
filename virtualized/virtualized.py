from keysight import Keysight
from mcc import Mcc
from tdk import Tdk
from compressor import Compressor

def main():
    keysight = Keysight(.1)
    keysight.daemon = True
    keysight.start()

    mcc=Mcc(.1)
    mcc.daemon = True
    mcc.start()

    tdk = Tdk(.1)
    tdk.daemon = True
    tdk.start()

    compressor = Compressor(.1)
    compressor.daemon = True
    compressor.start()

    while True:
        pass

if __name__ == '__main__':
    main()