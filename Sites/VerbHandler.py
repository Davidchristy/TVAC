import http.server
import json
import sys
import os
import socket

from Controllers import PostControl
from Controllers import GetControl
from ThreadControls.ThreadCollectionInstance import ThreadCollectionInstance

from Logging.Logging import Logging

class VerbHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        """Respond to a GET request."""
        Logging.logEvent("Debug","Status Update", 
            {"message": "Received GET Request",
             "level":1})
        path="NULL"
        try:
            path = self.path

            Logging.logEvent("Debug","Status Update", 
                {"message": "GET Request Path: {}".format(path),
                 "level":2})

            # Based on the path we are given, do different functions
            result = {
                '/runProfile': GetControl.run_profile,
                '/getAllThermoCoupleData': GetControl.get_all_thermocouple_data,
                '/getAllZoneData': GetControl.get_all_zone_data,
                '/getShiTemps': GetControl.get_shi_temps,
                '/getCryoPump_Status': GetControl.get_cryopump_status,
                '/getCryoPump_Params': GetControl.get_cryopump_params,
                '/getCryoPump_plots': GetControl.get_cryopump_plots,
                '/getPC104_Digital': GetControl.get_pc104_digital,
                '/getPC104_Switches': GetControl.get_pc104_switches,
                '/getPC104_Analog': GetControl.get_pc104_analog,
                '/getPressureGauges': GetControl.get_pressure_gauges,
                '/getZoneTemps': GetControl.get_zone_temps,
                '/getLastErr' : GetControl.get_last_error,
                '/putUnderVacuum': GetControl.put_under_vacuum,
                '/VacuumNotNeeded':GetControl.vacuum_not_needed,
                '/StopCryoPumpingChamber':GetControl.stop_cryopumping_chamber,
                '/StopCryoPump':GetControl.stop_cryopump,
                '/StopRoughingPump':GetControl.stop_roughing_pump,
                '/getEventList':GetControl.get_event_list,
                '/hardStop':GetControl.hard_stop,
                '/hold':GetControl.hold_all_zones,
                '/pause':GetControl.pause_all_zones,
                '/resume':GetControl.resume_all_zones,
                '/unHold':GetControl.un_hold_all_zones,
                '/getVacuumState': GetControl.get_vacuum_state,
                '/doRegen': GetControl.do_regen_cycle,
                '/abortRegen': GetControl.abort_regen_cycle,
                '/getTvacStatus': GetControl.get_tvac_status,
                '/StoprecordData': GetControl.stop_recording_data,
                '/recordData': GetControl.record_data,
                '/chamberDoorStatus':GetControl.chamber_door_status,
                "/getInterlockStatus":GetControl.get_interlock_status,
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
        except socket.error:
            pass
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
            # control = PostControl
            result = {
                '/saveProfile': PostControl.save_profile,
                '/loadProfile' : PostControl.load_profile,
                '/pauseZone': PostControl.pause_single_thread,
                '/pauseRemoveZone': PostControl.remove_pause_single_thread,
                '/holdZone': PostControl.hold_single_thread,
                '/releaseHoldZone': PostControl.release_hold_single_thread,
                '/SendHwCmd': PostControl.send_hw_cmd,
                '/setPC104Digital': PostControl.set_pc_104_digital,
                '/setPC104Analog': PostControl.set_pc_104_analog,
                '/heatUpPlaten': PostControl.heat_up_platen,
                '/heatUpShroud': PostControl.heat_up_shroud,
            }[path](contractObj)

            Logging.logEvent("Debug","Status Update", 
                {"message": "Sending POST Results",
                 "level":1})
            Logging.logEvent("Debug","Status Update", 
                {"message": "POST Results: {}".format(str(result).replace("\"","'").encode()),
                 "level":2})

            self.setHeader()
            self.wfile.write(str(result).encode())
        except socket.error:
            pass
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
