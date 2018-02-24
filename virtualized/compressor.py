import time

def main():
    '''
    This is a tester program that will fake a shi_compressor attached to the other side
    :return:
    '''
    port = open('/home/vagrant/compressor', 'r+b', buffering=0)
    buffer = ['']
    print("About to start loop")
    while not port.closed:
        print("Holding for reading")
        buff = port.read(1).decode()
        print("Byte found: {}\ncurrent buffer: {}".format(buff, buffer))
        buffer[0] += buff
        if buff == "\r" or len(buffer[0]) >= 128:
            buffer.insert(0, "")
            time.sleep(.1)

if "__main__" == __name__:
    main()