from __future__ import print_function
import time
from datetime import datetime, date, timedelta
import sys
import MySQLdb
import os
import socket
from client import sendSocketMessage

#f = open('/var/log/tisLog/tisdatalog', 'a')
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

db = MySQLdb.connect(host="localhost",user="root",passwd="itspe",db="htms")
cur = db.cursor()

cur.execute("SELECT IPAddress,site_id,SCN,runPlanClicked, oldPlanId, currentPlan FROM `utmc_traffic_signal_static` WHERE `SignalID`='172'")
signaldata = cur.fetchone()
hostname = signaldata[0]
signalscn = signaldata[2]
runPlanClicked = signaldata[3]
oldPlanId = signaldata[4]
newPlanId = signaldata[5]

CycleTime = totalStageTime + totalInterStageTime
timings_to_insert = []
stages_at_insert = []
planStartedTime = secondsSinceMidnight(runPlanClicked)
while(planStartedTime > 0):
	planStartedTime = planStartedTime - (CycleTime)
endPlanTime = 79196
looperTime = planStartedTime
print(str(looperTime)+" loopertime\n", end='')
looper = 0
if end_time == 10:
	end_time = 86410
startIST = secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time)
endIST = secondsSinceMidnightUTCTosecondsSinceMidnightIST(end_time)
if endIST == 10:
	endIST = 86410
while(True):
	if looperTime <= endIST and looperTime >= startIST:
		timings_to_insert.append(secondsSinceMidnightISTTosecondsSinceMidnightUTC(looperTime))
		stages_at_insert.append(looper)
	looperTime = looperTime + timings[looper] + interstagetimings[looper]
	looper = looper + 1 
	looper = 0 if looper == len(timings) else looper
	if looperTime > endPlanTime:
		break
for value in range(0, len(timings_to_insert)):
	if timings_to_insert[value] + 2 > 86400:
		timings_to_insert[value] = timings_to_insert[value] - 2
	if timings_to_insert[value] <= 10 and timings_to_insert[value] >= 0:
		time.sleep(60)
	stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(ug405_pin[int(stages_at_insert[value])])+"`, `"+str(ug405_reply_pin[int(stages_at_insert[value])])+"`"
	for key in pinsarray:
		if key != str(ug405_reply_pin[stages_at_insert[value]]):
			stmt += ", `"+str(key)+"`"
	stmt1 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+","+fb+","+fb+",0,0,0,0,1)"
	cur.execute(stmt1)
	db.commit()
	cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
	db.commit()

	stmt2 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+3)+","+sb+","+sb+",0,0,0,0,0)"
	cur.execute(stmt2)
	db.commit()
	cur.execute(stmt2.replace("utcControlTable","utcControlTable_dummy"))
	db.commit()

	print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
	print("[INFO] ", end='')
	print("[ATCS] ", end='')
	print("[Control] ", end='')
	print("["+str(ug405_reply_pin[stages_at_insert[value]])+" "+str(fb)+"] ", end='')
	print("["+str(site_id)+"] ", end='')
	print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(timings_to_insert[value]))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
	
	print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
	print("[INFO] ", end='')
	print("[ATCS] ", end='')
	print("[Control] ", end='')
	print("["+str(ug405_reply_pin[stages_at_insert[value]])+" "+str(sb)+"] ", end='')
	print("["+str(site_id)+"] ", end='')
	print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(timings_to_insert[value]+1))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')