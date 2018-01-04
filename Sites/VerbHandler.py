import http.server
import json
import sys
import os

from Controllers.PostControl import PostControl
from Controllers.GetControl import GetControl
from ThreadControls.ThreadCollectionInstance import ThreadCollectionInstance

from Logging.Logging import Logging

class VerbHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        """Respond to a GET request."""
        Logging.logEvent("Debug","Status Update", 
            {"message": "Received GET Request",
             "level":1})
        try:
            path = self.path

            Logging.logEvent("Debug","Status Update", 
                {"message": "GET Request Path: {}".format(path),
                 "level":2})

            # Based on the path we are given, do different functions
            control = GetControl()
            result = {
                '/runProfile': control.run_profile,
                '/checkZoneStatus': control.check_tread_status,
                '/getAllThermoCoupleData': control.get_all_thermocouple_data,
                '/getAllZoneData': control.get_all_zone_data,
                '/getShiTemps': control.get_shi_temps,
                '/getCryoPump_Status': control.get_cryopump_status,
                '/getCryoPump_Params': control.get_cryopump_params,
                '/getCryoPump_plots': control.get_cryopump_plots,
                '/getPC104_Digital': control.get_pc104_digital,
                '/getPC104_Switches': control.get_pc104_switches,
                '/getPC104_Analog': control.get_pc104_analog,
                '/getPressureGauges': control.get_pressure_gauges,
                '/getZoneTemps': control.get_zone_temps,
                '/getLastErr' : control.get_last_error,
                '/putUnderVacuum': put_under_vacuum,
                '/VacuumNotNeeded':control.vacuum_not_needed,
                '/StopCryoPumpingChamber':control.stop_cryopumping_chamber,
                '/StopCryoPump':control.stop_cryopump,
                '/StopRoughingPump':control.stop_roughing_pump,
                '/getEventList':control.get_event_list,
                '/hardStop':control.hard_stop,
                '/hold':control.hold_all_zones,
                '/pause':control.pause_all_zones,
                '/resume':control.resume_all_zones,
                '/unHold':control.un_hold_all_zones,
                '/getVacuumState': control.get_vacuum_state,
                '/doRegen': control.do_regen_cycle,
                '/abortRegen': control.abort_regen_cycle,
                '/getTvacStatus': control.get_tvac_status,
                '/StoprecordData': control.stop_recording_data,
                '/recordData': control.record_data,
                }[path]()

            Logging.logEvent("Debug","Status Update",
                {"message": "Sending GET Results",
                 "level":1})
            Logging.logEvent("Debug","Status Update", 
                {"message": "GET Results: {}".format(str(result).encode()),
                 "level": 5})

            # Out the results back to the server
            self.setHeader()
            self.wfile.write(str(result).encode())
        except Exception as e:
            # print("There has been an error").
            # FileCreation.pushFile("Error","Get",'{"errorMessage":"%s"}\n'%(e))

            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            Logging.logEvent("Error","GET Handler", 
                {"type": exc_type,
                 "filename": fname,
                 "line": exc_tb.tb_lineno,
                 "thread": "Verb Handler",
                 "ThreadCollection":ThreadCollectionInstance.getInstance().threadCollection,
                 "item":"Server",
                 "itemID":-1,
                 "details":"PATH: {} is not recognized".format(path)
                })
            Logging.logEvent("Debug","Status Update", 
                {"message": "There was a {} error in Server (GET Handler). File: {}:{}".format(exc_type,fname,exc_tb.tb_lineno),
                 "level":1})

            self.setHeader()
            output = '{"Error":"%s"}\n'%(e)
            self.wfile.write(output.encode())
            raise e

    def do_POST(self):
        """Respond to a POST request."""
        try:
            Logging.logEvent("Debug","Status Update", 
                {"message": "Received Post Request",
                 "level":1})
            body = self.getBody()
            path = self.path
            
            Logging.logEvent("Debug","Status Update", 
                {"message": "POST Request Path: {}".format(path),
                 "level":2})

            # You might need to decode the results
            if type(body) == type(b'a'):
                body = body.decode("utf-8")
            contractObj = json.loads(body)

            # Based on the path we are given, do different functions
            control = PostControl()
            result = {
                '/saveProfile': control.saveProfile,
                '/loadProfile' : control.loadProfile,
                '/runSingleProfile': control.runSingleProfile,
                '/pauseZone': control.pauseSingleThread,
                '/pauseRemoveZone': control.removePauseSingleThread,
                '/holdZone': control.holdSingleThread,
                '/releaseHoldZone': control.releaseHoldSingleThread,
                '/abortZone': control.abortSingleThread,
                '/calculateRamp': control.calculateRamp,
                '/SendHwCmd': control.SendHwCmd,
                '/setPC104Digital': control.setPC104_Digital,
                '/setPC104Analog': control.setPC104_Analog,
                '/heatUpPlaten':control.heatUpPlaten,
                '/heatUpShroud':control.heatUpShroud,

            }[path](contractObj)

            Logging.logEvent("Debug","Status Update", 
                {"message": "Sending POST Results",
                 "level":1})
            Logging.logEvent("Debug","Status Update", 
                {"message": "POST Results: {}".format(str(result).replace("\"","'").encode()),
                 "level":2})

            self.setHeader()
            self.wfile.write(str(result).encode())
        except Exception as e:

            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            Logging.logEvent("Error","POST Handler", 
                {"type": exc_type,
                 "filename": fname,
                 "line": exc_tb.tb_lineno,
                 "thread": "Verb Handler"
                })
            Logging.logEvent("Debug","Status Update", 
                {"message": "There was a {} error in Server (POST Handler). File: {}:{}".format(exc_type,fname,exc_tb.tb_lineno),
                 "level":1})

            self.setHeader()
            output = '{"Error":"%s"}\n'%(e)
            self.wfile.write(output.encode())
            raise(e)



    def getBody(self):
        content_len = int(self.headers['content-length'])
        tempStr = self.rfile.read(content_len)
        return tempStr

    def setHeader(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json".encode())
        self.end_headers()

    # def displayZones(self):
    #     profileInstance = ProfileInstance.getInstance()
    #     self.wfile.write(profileInstance.zoneProfiles.getJson().encode())
