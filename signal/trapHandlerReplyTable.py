import MySQLdb
from datetime import datetime, date, timedelta
import time
import os
import sys
from config import *

pid = str(os.getpid())
pidfile = "/tmp/trap_reply_table.pid"
if os.path.isfile(pidfile):
	sys.exit()
file(pidfile, 'w').write(pid)

def secondsSinceMidnight(c_time):
	return int((c_time - c_time.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())
#input in seconds since midnight in IST
def secondsSinceMidnightToIST(seconds):
	return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(milliseconds = (seconds*1000))
#input in seconds since midnight in IST
def secondsSinceMidnightToUTC(seconds):
	return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(milliseconds = (seconds*1000 - 19800000))
def secondsSinceMidnightISTTosecondsSinceMidnightUTC(seconds):
	return secondsSinceMidnight(secondsSinceMidnightToUTC(seconds))
def secondsSinceMidnightUTCTosecondsSinceMidnightIST(seconds):
	value = seconds + 19800
	if value >= 86400:
		value = value - 86400
	return value

try:
	while(1):
		db = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIM)
		tisdb = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIS)
		cursor = db.cursor()
		tiscursor = tisdb.cursor()
		cursor.execute("SELECT trap_triggers.*,sites.site_ref FROM trap_triggers INNER JOIN sites ON trap_triggers.site_id=sites.id")
		results = cursor.fetchall()
		for result in results:
			site_id = result[0]
			bit = result[1]
			value = result[2]
			if value == 1:
				value = "true"
			else:
				value = "false"
			Gn = result[3]
			stageNumber = 0
			stageTime = 0
			
			if bit == "utcReplyGn":
				stageNumber = 3 if Gn is None else int(Gn[-2:],16)
				tiscursor.execute("SELECT GROUP_CONCAT(StageNumber ORDER BY execOrder SEPARATOR ',') FROM signal_timings INNER JOIN plans ON plans.PlanSCN = signal_timings.Plan_SCN INNER JOIN utmc_traffic_signal_static ON utmc_traffic_signal_static.currentPlan = plans.ID AND utmc_traffic_signal_static.site_id="+str(site_id)+" AND signal_timings.SignalSCN = utmc_traffic_signal_static.SignalSCN WHERE execOrder <> 0 GROUP BY Plan_SCN")
				s = tiscursor.fetchone()
				stages = s[0].split(',')
				stages = [int(x) for x in stages]
				sTimeIndex = 0
				try:
					sTimeIndex = stages.index(stageNumber)
				except Exception as e:
					print e

				if stageNumber != 0:
					stageTime = int(Gn[(2*(sTimeIndex)):(2*(sTimeIndex))+2],16)
			elif bit == "utcReplyLFn":
				stageNumber = Gn
			


			# tiscursor.execute("SELECT GROUP_CONCAT(StageNumber ORDER BY execOrder SEPARATOR ',') FROM signal_timings INNER JOIN plans ON plans.PlanSCN = signal_timings.Plan_SCN INNER JOIN utmc_traffic_signal_static ON utmc_traffic_signal_static.currentPlan = plans.ID AND utmc_traffic_signal_static.site_id="+str(site_id)+" AND signal_timings.SignalSCN = utmc_traffic_signal_static.SignalSCN WHERE execOrder <> 0 GROUP BY Plan_SCN")
			# s = tiscursor.fetchone()
			# stages = s[0].split(',')
			# stages = [int(x) for x in stages]
			# sTimeIndex = 0
			# try:
			# 	sTimeIndex = stages.index(stageNumber)
			# except Exception as e:
			# 	print e

			# if bit == "utcReplyGn" and stageNumber != 0:
			# 	stageTime = int(Gn[(2*(sTimeIndex)):(2*(sTimeIndex))+2],16)
			timestamp = secondsSinceMidnight(result[4])
			site_id = result[5]
			#print site_id, bit, value, timestamp
			# print "php "+PATH+"/gui/utils/add_tim_data.php "+str(site_id)+" "+str(timestamp)+" "+str(bit)+" "+str(value)+" "+str(stageNumber)+" "+((">> "+LOGPATH_TIMInstructions+" 2>&1") if DEBUG == True else "")+" &"
			os.system("php "+PATH+"/gui/utils/add_tim_data.php "+str(site_id)+" "+str(timestamp)+" "+str(bit)+" "+str(value)+" "+str(stageNumber)+" "+str(stageTime)+" "+((">> "+LOGPATH_TIMInstructions+" 2>&1") if DEBUG == True else "")+" &")
		cursor.execute("DELETE from trap_triggers WHERE 1")
		db.commit()
		cursor.close()
		tiscursor.close()
		tisdb.close()
		db.close()
		time.sleep(1)
finally:
	os.unlink(pidfile)
