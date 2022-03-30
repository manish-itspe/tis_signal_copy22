import MySQLdb
from datetime import datetime, date, timedelta
import time
import os
import sys
from warnings import filterwarnings
from config import *

filterwarnings('ignore', category = MySQLdb.Warning)

site_id = 0
if len(sys.argv) != 2:
        print("Provide All Inputs Required")
        sys.exit(0)
else:
        try:
                int(sys.argv[1])
        except ValueError:
                print("Please Enter Valid Site ID")
                sys.exit(0)

site_id = int(sys.argv[1])
time.sleep(10)
db = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIM)
cursor = db.cursor()
cursor.execute("SELECT currentStageOrder, is_active FROM htms.utmc_traffic_signal_static WHERE site_id='"+str(site_id)+"'")
results = cursor.fetchall()
cursor.execute("SELECT * from utcReplyTable where utcReplyGn='0000000000000001' and reply_timestamp between ((SELECT MAX(reply_timestamp) FROM utcReplyTable  WHERE utcReplyVO=1 and site_id='"+str(site_id)+"') - INTERVAL 20 SECOND) and ((SELECT MAX(reply_timestamp) FROM utcReplyTable WHERE utcReplyVO=1 and site_id='"+str(site_id)+"') + INTERVAL 4 SECOND) AND site_id='"+str(site_id)+"'")
results2 = cursor.fetchall()
if len(results2) == 1 or str(results[0][0]) == "1":
        print "Its Fine"
else:
        if str(results[0][1]) == "1":
		cursor.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,0)")
                cursor.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`, `origin`) VALUES ("+str(site_id)+",1,0, 'stageOne')")
		print "Ok move to offline"
	else:
		print "Tim Already Offline"
db.commit()
cursor.close()
db.close()
