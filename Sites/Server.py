#!/usr/local/bin/python3.5
import socketserver
import sys

from VerbHandler import VerbHandler
from Collections.ProfileInstance import ProfileInstance
from Collections.HardwareStatusInstance import HardwareStatusInstance
from ThreadControls.ThreadCollectionInstance import ThreadCollectionInstance

from Logging.Logging import Logging

class ReuseAddrTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == '__main__':
    # adding debug info
    if len(sys.argv) > 1:
        for arg in sys.argv:
            if arg.startswith("-v"):
                Logging.verbose = arg.count("v")
    if len(sys.argv) > 2:
        for arg in sys.argv:
            if "--debug" in arg:
                Logging.debug = True
    Logging.logEvent("Debug","Status Update",
        {"message": "Verbos on: Level {}".format(Logging.verbose),
         "level":1})
    PORT = 8000

    Logging.logEvent("Debug","Status Update",
        {"message": "Starting initializing threads and drivers",
         "level":1})

    hardwareStatusInstance = HardwareStatusInstance.getInstance()
    profileInstance = ProfileInstance.getInstance()
    threadInstance = ThreadCollectionInstance.getInstance()

    Logging.logEvent("Event","System booted",
        {"message": "Server is fully booted",
        "ProfileInstance": profileInstance.getInstance()})
    Logging.logEvent("Debug","Status Update",
        {"message": "Finished initializing threads and drivers",
         "level":1})

    httpd = ReuseAddrTCPServer(("", PORT), VerbHandler)

    Logging.logEvent("Debug","Status Update",
        {"message": "Start Up Complete, Server is listening for request...",
         "level":1})

    httpd.serve_forever()
