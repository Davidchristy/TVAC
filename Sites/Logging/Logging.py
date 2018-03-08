from Logging.MySql import MySQlConnect
from datetime import datetime
import time, threading


_mySqlConnect = MySQlConnect()
_sql_lock = threading.Lock()

def insert_into_sql(sql_str):
    with _sql_lock:
        try:
            mysql = _mySqlConnect
            mysql.cur.execute(sql_str)
            mysql.conn.commit()
        except Exception as e:
            raise e

def sql_fetch_one(sql_str):
    with _sql_lock:
        try:
            mysql = _mySqlConnect
            mysql.cur.execute(sql_str)
            mysql.conn.commit()
            result = mysql.cur.fetchone()
        except Exception as e:
            raise e
        return result

def sql_fetch_all(sql_str):
    with _sql_lock:
        try:
            mysql = _mySqlConnect
            mysql.cur.execute(sql_str)
            mysql.conn.commit()
            results = mysql.cur.fetchall()
        except Exception as e:
            raise e
        return results


class Logging(object):
    """
    Logging is a static class that will take and filter every kind of
    output this program does
    """
    verbose = 0
    debug = False

    @staticmethod
    def logEvent(category, logType, data):
        # category can be "Error", or "Event", or "Debug"
        # Type can be different string based on Category
        # Data is a dictionary of different information depending on the category and type
        if category is "Error":
            if "Hardware Interface Thread" in logType:
                # in here check if 'type' is a buffer error, if so suggest checking connection to device
                print("Error: Thread '{}' has had an error of type {}. Restarting thread now...".format(data['thread'],data['type']))
        elif category is "Event":
            # if "Thread Start" in logType:
            currentTime = datetime.now()
            print("Event- {}: {}".format(logType,data.get("message"),currentTime))
            system_status_queue = data["ProfileInstance"].system_status_queue
            eventList = system_status_queue
            eventList.append({"time":str(datetime.now()),
                "category":logType,
                "message":data.get("message")})

            coloums = "( event_type, details )"
            values = "( \"{}\",\"{}\" )".format(category,logType)
            sql_str = "INSERT INTO tvac.Event {} VALUES {};".format(coloums, values)
            insert_into_sql(sql_str=sql_str)
        elif category is "Debug":
            if "Status Update" in logType:
                Logging.debug_print(data["level"], data['message'])
            elif "Data Dump" in logType:
                Logging.debug_print(data["level"], data['message'], data["dict"])

    @staticmethod
    def debug_print(verbosLevel, string, dictionary=None):
        if Logging.verbose >= verbosLevel:
            spacing = "  "*(verbosLevel-1)
            BLUE_START = "\033[94m"
            COLOR_END = "\033[0m"
            prefix = "{}{}debug-{}: {}".format(spacing,BLUE_START,verbosLevel,COLOR_END)
            if dictionary:
                print("{}{}".format(prefix,string))
                for i, entry in enumerate(dictionary):
                    if type(dictionary) == type({}):
                        print("{}  {} --> {}".format(prefix,entry,dictionary[entry]))
                    elif type(dictionary) == type([]):
                        print("{}  {}".format(prefix,entry))
            else:
                coloums = "( message, created )"
                values = "( \"{}\",\"{}\" )".format("{}".format(string),datetime.fromtimestamp(time.time()))

                sql_str = "INSERT INTO tvac.Debug {} VALUES {};".format(coloums, values)

                insert_into_sql(sql_str=sql_str)

                for line in string.split("\n"):
                    print("{}{}".format(prefix,line))
