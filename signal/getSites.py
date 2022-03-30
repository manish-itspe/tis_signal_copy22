import MySQLdb
import os
from config import *
import time

db = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIS)
cursor = db.cursor()

cursor.execute("SELECT count(*) from utmc_traffic_signal_static WHERE Group_SCN <> ''") # where SignalSCN IN ('J003','J002','J008')")
total_count = cursor.fetchone()

if total_count is not None:
	count = int(total_count[0])
	i=0
	while i < count:
                cursor.execute("SELECT site_id, SignalSCN from utmc_traffic_signal_static ORDER BY site_id ASC LIMIT "+str(i)+",10")
                results = cursor.fetchall()
                for result in results:
            	        os.system("python "+PATH+"/background/signal/detectorDynamic.py "+str(result[0])+" "+str(result[1])+" &")

                time.sleep(20)
                i=i+10
		#break
cursor.close()
db.close()
