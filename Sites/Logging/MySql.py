import time
import os
import pymysql

from warnings import filterwarnings

class MySQlConnect:


    def __init__(self):
        if os.name == "posix":
            userName = os.environ['LOGNAME']
        else:
            userName = "user"
        if "root" in userName:
            user = "TVAC_Admin"
            host = "192.168.99.10"
            password = "People 2 Space"
        else:
            user = "tvac_user"
            host = "localhost"
            password = "Go2Mars!"
        database = "tvac"
        
        filterwarnings('ignore', category = pymysql.Warning)
        self.conn = pymysql.connect(host=host, user=user, passwd=password, db=database)
        self.cur = self.conn.cursor(pymysql.cursors.DictCursor)

