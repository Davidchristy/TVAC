from Collections.ProfileInstance import ProfileInstance
from Logging.Logging import insert_into_sql


def release_hold(data=None):
    ProfileInstance.getInstance().in_hold = False
    sql_str = "UPDATE System_Status SET in_hold=0;"
    insert_into_sql(sql_str=sql_str)