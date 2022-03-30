from __future__ import print_function
import time
from datetime import datetime, date, timedelta
import sys
import MySQLdb
import os
import socket
from client import sendSocketMessage

# f = open('/var/log/tisLog/tisdatalog', 'a')
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


if len(sys.argv) != 7:
	print("Provide All Inputs Required")
	sys.exit(0)
else:
	values = sys.argv[1].split(",")
	print(values)
	for value in values:
		try:
			int(value)
		except ValueError:
			print("Please Enter Valid Timings")
			sys.exit(0)
	curtime = ""
	try:
		datetime.strptime(sys.argv[3], '%H:%M:%S')
	except ValueError:
		print("Please Enter Valid Start Time")
		sys.exit(0)
	try:
		datetime.strptime(sys.argv[4], '%H:%M:%S')
	except ValueError:
		print("Please Enter Valid End Time")
		sys.exit(0)

#argument parameters | python timDataPass.py "20,30,40" "4,4,4" "14:54:01" "14:55:01" "1" "1"
timings = [int(n) for n in sys.argv[1].split(",")]
interstagetimings = [int(n) for n in sys.argv[2].split(",")]
start_time = secondsSinceMidnight(datetime.strptime(sys.argv[3], '%H:%M:%S'))
end_time = secondsSinceMidnight(datetime.strptime(sys.argv[4], '%H:%M:%S'))
site_id = sys.argv[5]
forcebit = sys.argv[6]

totalStageTime = sum(timings)
totalInterStageTime = sum(interstagetimings)

fb = ''
sb = ''

if forcebit == '0':
	fb = '0'
	sb = '1'
else:
	fb = '1'
	sb = '0'

db = MySQLdb.connect(host="localhost",user="root",passwd="itspe",db="htms")

ug405_pin = ["utcControlTO","utcControlTO","utcControlTO"]
pinsarray = ["utcControlGO","utcControlFF","utcControlFM","utcControlCP","utcControlEP"]
ug405_reply_pin = ["utcControlGO","utcControlFF","utcControlCP"]

cur = db.cursor()
cur.execute("SELECT IPAddress,site_id,SCN,runPlanClicked FROM `utmc_traffic_signal_static` WHERE `site_id`='"+site_id+"'")
signaldata = cur.fetchone()
hostname = signaldata[0]
signalscn = signaldata[2]
runPlanClicked = signaldata[3]
# response = os.system("ping -c 1 " + hostname)
response = 0
if response == 0:
	CycleTime = totalStageTime + totalInterStageTime
	if secondsSinceMidnight(runPlanClicked) > secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time):
		start_time = secondsSinceMidnightISTTosecondsSinceMidnightUTC(secondsSinceMidnight(runPlanClicked))

	timings_to_insert = []
	stages_at_insert = []
	planStartedTime = secondsSinceMidnight(runPlanClicked)
	while(planStartedTime > 0):
		planStartedTime = planStartedTime - (CycleTime)
	endPlanTime = 84600
	looperTime = planStartedTime
	print(str(looperTime)+" loopertime\n", end='')
	looper = 0
	if end_time == 10:
		end_time = 86410
	startIST = secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time)
	endIST = secondsSinceMidnightUTCTosecondsSinceMidnightIST(end_time)
	print("++"+str(startIST)+" "+str(endIST)+"++\n")
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
	
	print(stages_at_insert) #[0,1,2]
	print(timings_to_insert)
	
	for value in range(0, len(timings_to_insert)):
		if timings_to_insert[value] + 2 > 86400:
			timings_to_insert[value] = timings_to_insert[value] - 2
		if timings_to_insert[value] <= 10 and timings_to_insert[value] >= 0:
			time.sleep(60)
		# stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(ug405_pin[int(stages_at_insert[value])])+"`, `"+str(ug405_reply_pin[int(stages_at_insert[value])])+"`"
		# for key in pinsarray:
		# 	if key != str(ug405_reply_pin[stages_at_insert[value]]):
		# 		stmt += ", `"+str(key)+"`"
		# stmt1 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+","+fb+","+fb+",0,0,0,0,1)"
		stageNumber = int(stages_at_insert[value]) + 1
		stagesInHex = format(stageNumber,'02x').upper()
		Fn = stagesInHex #+ ''.join(['0' for i in range(0,16 - len(stagesInHex))])
		
		stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+",'"+Fn+"')"
		print(stmt)
		cur.execute(stmt)
		db.commit()
		cur.execute(stmt.replace("utcControlTable","utcControlTable_dummy"))
		db.commit()

		# stmt2 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+3)+","+sb+","+sb+",0,0,0,0,0)"
		# cur.execute(stmt2)
		# db.commit()
		# cur.execute(stmt2.replace("utcControlTable","utcControlTable_dummy"))
		# db.commit()

		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
		print("[INFO] ", end='')
		print("[ATCS] ", end='')
		print("[Control] ", end='')
		print("["+str(ug405_reply_pin[stages_at_insert[value]])+" "+str(fb)+"] ", end='')
		print("["+str(site_id)+"] ", end='')
		print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(timings_to_insert[value]))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
else:
	print("else active")
	cur.execute("UPDATE `utmc_traffic_signal_static` SET `is_active`='0' WHERE `site_id`='"+site_id+"'")
	db.commit()
	cur.execute("SELECT * FROM `tis_traffic_signal_fault` WHERE `SystemCodeNumber`='"+signalscn+"' ORDER BY `LastUpdated` DESC LIMIT 1")
	data = cur.fetchone()
	if data[2] != 0:
		cur.execute("INSERT INTO `tis_traffic_signal_fault` VALUES('"+signalscn+"','"+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"',0, UNIX_TIMESTAMP(now()) - UNIX_TIMESTAMP('"+str(data[1])+"'))")
		db.commit()
	sendSocketMessage("TimOffline,"+signalscn+"pass")
	db.close()
	sys.exit(0)
			
