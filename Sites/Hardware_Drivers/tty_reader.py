#!/usr/bin/env python3.5
import time
from threading import Thread
from threading import Condition


class TTY_Reader(Thread):


    def __init__(self, fd, group=None, target=None, name=None, args=(), kwargs=None):
        Thread.__init__(self, group=group, target=target, name=name)
        self.__lock = Condition()
        self.args = args
        self.kwargs = kwargs
        self.tty_fd = fd
        self.buffer = ['']
        self.last_time_run = time.time()
    def get_fd(self, fd):
        self.tty_fd = fd

    def run(self):
        '''
        '''
        while not self.tty_fd.closed:
            self.last_time_run = time.time()
            time_before_read = time.time()
            buff = self.tty_fd.read(1).decode()
            read_time = time.time() - time_before_read
            #print(read_time)
            #if read_time > 1:
            #    print("{} read time: {}".format(self.name,read_time))
            # print("Gap Between runs: {}".format(self.last_time_run-time.time()))
            # print("Data Read: '{}'".format(buff))
            with self.__lock:
                self.buffer[0] += buff
                if buff == "\r" or len(self.buffer[0]) >= 128:
                    self.buffer.insert(0, "")
                    self.__lock.notify()
                    time.sleep(.1)


    def flush_buffer(self, delay_for_read=0.0):
        if delay_for_read > 0:
            time.sleep(delay_for_read)
        with self.__lock:
            self.buffer = ['']

    def read_line(self, time_out=1.0):
        with self.__lock:
            if len(self.buffer) > 1:
                line = self.buffer.pop()
            else:
                self.__lock.wait(time_out)  # wait for a new line to put onto the buffer
                if len(self.buffer) > 1:
                    line = self.buffer.pop()
                elif len(self.buffer) == 1:
                    line = self.buffer[0]
                    self.buffer[0] = ''
                else:
                    line = ''
                    self.buffer = ['']
        return line

