import MySQLdb
from datetime import datetime, date, timedelta
import time
import os
import sys
from warnings import filterwarnings
filterwarnings('ignore', category = MySQLdb.Warning)

site_id = 0
if len(sys.argv) != 3:
        print("Provide All Inputs Required")
        sys.exit(0)
else:
        try:
                int(sys.argv[1])
        except ValueError:
                print("Please Enter Valid Site ID")
                sys.exit(0)
	try:
		datetime.strptime(sys.argv[2], '%Y-%m-%d %H:%M:%S')
	except ValueError:
		print("Please Enter Valid Start Time")
		sys.exit(0)		

site_id = int(sys.argv[1])
vo_timestamp = sys.argv[2]
time.sleep(5)
db = MySQLdb.connect("localhost","root","itspe","tis")
cursor = db.cursor()
cursor.execute("SELECT currentStageOrder, is_active FROM htms.utmc_traffic_signal_static WHERE site_id='"+str(site_id)+"'")
results = cursor.fetchall()
cursor.execute("SELECT * from utcReplyTable where utcReplyRF1=1 and reply_timestamp between (CONVERT_TZ('"+vo_timestamp+"','+00:00','-05:30') - INTERVAL 10 SECOND) and (CONVERT_TZ('"+vo_timestamp+"','+00:00','-05:30') + INTERVAL 10 SECOND) AND site_id='"+str(site_id)+"'")
results2 = cursor.fetchall()
if len(results2) == 1:
        print "Its Fine"
else:
        if str(results[0][1]) == "1":
		#cursor.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,0)")
                #cursor.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`, `origin`) VALUES ("+str(site_id)+",1,0, 'stageOne')")
		print "Ok move to offline"
	else:
		print "Tim Already Offline"
db.commit()
db.close()
