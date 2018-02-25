#!/bin/bash

sudo socat -d -d pty,raw,echo=0,link=/home/vagrant/mcc pty,raw,echo=0,link=/dev/ttyxuart0 &
sudo socat -d -d pty,raw,echo=0,link=/home/vagrant/compressor pty,raw,echo=0,link=/dev/ttyxuart1 &
sudo socat -d -d pty,raw,echo=0,link=/home/vagrant/tdk pty,raw,echo=0,link=/dev/ttyxuart4 &

sudo chown vagrant /home/vagrant/mcc
sudo chown vagrant /home/vagrant/compressor
sudo chown vagrant /home/vagrant/tdk

sudo chown vagrant /dev/ttyxuart0
sudo chown vagrant /dev/ttyxuart1
sudo chown vagrant /dev/ttyxuart4