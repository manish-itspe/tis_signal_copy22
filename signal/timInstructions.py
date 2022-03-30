from __future__ import print_function
import time
from datetime import datetime, date, timedelta
import sys
import MySQLdb
import os
import socket
sys.path.append('/var/www/html/tis')
from background.config import * 
from background.mailer import mailer
from background.client import sendSocketMessage

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

# print(len(sys.argv))
# print("^^len^^")
values = sys.argv[1]
plan_timings = values
start_time = sys.argv[2]
end_time = sys.argv[3]
signal_scn = sys.argv[4]
forcebit = sys.argv[5]
values_inter = sys.argv[6]
currentstage = int(sys.argv[7])
manual = sys.argv[8]
stageSeq = sys.argv[9]

if len(sys.argv) > 10:
	print("Provide All Inputs Required")
	sys.exit(0)
else:
	values = values.split(",")
	print("\n")
	print(values)
	for value in values:
		try:
			int(value)
		except ValueError:
			print("Please Enter Valid Timings")
			sys.exit(0)
	curtime = ""
	try:
		datetime.strptime(start_time, '%H:%M:%S')
	except ValueError:
		print("Please Enter Valid Start Time")
		sys.exit(0)
	try:
		datetime.strptime(end_time, '%H:%M:%S')
	except ValueError:
		print("Please Enter Valid End Time")
		sys.exit(0)
	try:
		int(currentstage)
	except ValueError:
		print("Please Enter Valid Current Stage")
		sys.exit(0)

db = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIS)

c_time = datetime.utcnow()
stagetimings = [int(n) for n in values]
interstagetimings = [int(n) for n in values_inter.split(",")]
stageNumber = [int(n) for n in stageSeq.split(',')]

fb = ''
sb = ''

if forcebit == '0':
	fb = '0'
	sb = '1'
else:
	fb = '1'
	sb = '0'

CycleTime = sum(stagetimings) + sum(interstagetimings)

cur = db.cursor()
# cur.execute("SELECT count(*) as count, group_concat(`ug405_pin`), group_concat(`ug405_reply_pin`) FROM `utmc_traffic_signal_stages` WHERE `SignalSCN`= '"+signal_scn+"' GROUP BY `SignalSCN` ORDER BY `StageOrder` ASC")
# ug405_pin = ''

# try:
# 	stage_info = cur.fetchone()
# 	count = stage_info[0]
# 	ug405_pin = [str(n) for n in stage_info[1].split(",")]
# 	ug405_reply_pin = [str(n) for n in stage_info[2].split(",")]
# 	cur.close()
# 	# if len(stagetimings) != count:
# 	# if len(stagetimings) != len():
# 	# 	print("Signal Stages Configuration error")
# 	# 	sys.exit(0)
# except Exception as e:
# 	print(e)
# 	print("Invalid Signal Stages Configuration")
# 	cur.close()
# 	db.close()
# 	sys.exit(0)

start_time = secondsSinceMidnight(datetime.strptime(start_time, '%H:%M:%S'))
end_time = secondsSinceMidnight(datetime.strptime(end_time, '%H:%M:%S'))
#interval_start_time = secondsSinceMidnight(datetime.strptime(sys.argv[8], '%H:%M:%S'))
limit_time = (end_time - start_time)
cur = db.cursor()
print(signal_scn,'---')
ic = 0 #if currentstage == stageNumber[len(stageNumber)-1] else stageNumber.index(currentstage)  # ic=0 To start from fixed stage after manual mode
# start_time = start_time + timings[i]
# i = i + 1

# #print("oldmode" + str(oldMode))
# pinsarray=["utcControlGO","utcControlFF","utcControlFM","utcControlCP","utcControlEP"]
site_id = ''

cur.execute("SELECT IPAddress,site_id,runPlanClicked, oldPlanId, currentPlan, is_va_active, currentMode, constantStageOrder, ShortDescription, currentStageOrder, is_manual_active FROM `utmc_traffic_signal_static` WHERE `SignalSCN`='"+signal_scn+"'")
signaldata = cur.fetchone()
hostname = signaldata[0]
runPlanClicked = signaldata[2]
oldPlanId = signaldata[3]
newPlanId = signaldata[4]
is_va_active = signaldata[5]
cMode = str(signaldata[6])
constantStageOrder = 0 if signaldata[7] is None else signaldata[7]
signalName = signaldata[8]
currentStageOrder = '00000000000000' +str(format(signaldata[9],'02x').upper())
is_manual_active = str(signaldata[10])

cur.execute("SELECT CriticalSignalSCN, CriticalRoutes, CriticalStage from plans WHERE ID="+str(newPlanId))
plandata = cur.fetchone()

group_site_ids = []

if plandata[1] is None or plandata[1] == '' or plandata[0] == signal_scn:
	CriticalSignalSCN = plandata[0]
	CriticalStage = plandata[2]
    
        cur.execute("SELECT site_id, DefaultOffset from plans INNER JOIN `routes` ON FIND_IN_SET(`routes`.`id`, REPLACE(TRIM(REPLACE(`plans`.`CriticalRoutes`, ';', ' ')), ' ', ',')) INNER JOIN utmc_traffic_signal_static ON utmc_traffic_signal_static.SignalSCN = routes.ToSignalSCN WHERE plans.ID="+str(newPlanId)+" AND FromSignalSCN='"+str(signal_scn)+"'")
	group_site_ids = cur.fetchall()

else:
	cur.execute("SELECT ToApproach from plans INNER JOIN `routes` ON FIND_IN_SET(`routes`.`id`, REPLACE(TRIM(REPLACE(`plans`.`CriticalRoutes`, ';', ' ')), ' ', ',')) WHERE plans.ID="+str(newPlanId)+" AND ToSignalSCN='"+str(signal_scn)+"'")
	CriticalStage = cur.fetchone()
	if CriticalStage is not None:
		CriticalStage = CriticalStage[0]
	else:
		CriticalStage = 3

print(str(CriticalStage)+"criticalstage\n",end='')

cur.execute("SELECT previousMode, previousModeId, newModeId, newMode, changeReason, timestamp FROM `tis_signal_mode_change_log` WHERE `SignalSCN`='"+signal_scn+"' ORDER BY timestamp DESC LIMIT 1")
signalmodedata = cur.fetchone()
previousMode = signalmodedata[0]
previousModeId = str(signalmodedata[1])
currentModeId = str(signalmodedata[2])
newMode = str(signalmodedata[3])
changeReason = signalmodedata[4]
last_mode_timestamp = signalmodedata[5]

# va = 1
# if is_va_active != 0 or cMode == "8":
# 	va = 0



response = os.system("ping -c 1 " + hostname)
try:
	site_id = signaldata[1]
except Exception as e:
	print("Invalid Signal SCN")
	cur.close()
	db.close()
	sys.exit(0)

startDayTime = STARTDAYTIME
endDayTime = ENDDAYTIME

if response == 0:
	print("######currentMode-"+cMode+"######")
	cur.execute("SELECT * FROM `tis_traffic_signal_fault` WHERE `SystemCodeNumber`='"+signal_scn+"' ORDER BY `LastUpdated` DESC LIMIT 1")
	data = cur.fetchone()
	if data[2] != 1:
		try:
			cur.execute("INSERT INTO `tis_traffic_signal_fault` VALUES('"+signal_scn+"',now(),1, UNIX_TIMESTAMP(now()) - UNIX_TIMESTAMP('"+str(data[1])+"'))")
			db.commit()
		except 	Exception as e:
			cur.execute("INSERT INTO `tis_traffic_signal_fault` VALUES('"+signal_scn+"',now(),1, 0)")
			db.commit()
			print(e)

		cur.execute("SELECT FaultID FROM `utmc_device_fault` WHERE `SystemCodeNumber`='"+signal_scn+"' AND FaultType='5' ORDER BY `CreationDate` DESC LIMIT 1")
		res = cur.fetchone()
		faultid = res[0]

		cur.execute("UPDATE utmc_freeflow_alert_dynamic SET ActionStatus='Closed',`HistoricDate`=NOW() WHERE SystemCodeNumber='"+str(faultid)+"'")
		db.commit()
		cur.execute("UPDATE utmc_device_fault SET `ClearedDate`=NOW() WHERE FaultID='"+str(faultid)+"'")
		db.commit()

		emails = ['mohammed.ahmed@itspe.co.in','naman.gupta@itspe.co.in']
		subject = "Junction Online"
		content = "Junction "+signalName+" has come back Online. Thanks for the support."

		#mailer(to=emails,subject=subject,content=content)

	# print(runPlanClicked)
	# # print("\n")
	# # print(start_time)
	# print("^^^^runPlanClicked^^^^\n\n")
	cur.execute("SELECT group_concat(`signal_timings`.`StageTime` ORDER BY execOrder separator ',') as StageTime,`utmc_traffic_signal_static`.`is_active`,group_concat(`signal_timings`.`InterStageTime` ORDER BY execOrder separator ',') as InterStageTime,group_concat(`utmc_traffic_signal_stages`.`ug405_reply_pin` ORDER BY execOrder separator ',') as ug405_reply_pin,group_concat(`utmc_traffic_signal_stages`.`ug405_pin` ORDER BY execOrder separator ',') as ug405_pin,`utmc_traffic_signal_static`.`ForceBidNextStagePin`,`utmc_traffic_signal_static`.`currentMode`,`plans`.`PlanSCN`,`plans`.`CycleTime`,utmc_traffic_signal_static.`currentPlan`,utmc_traffic_signal_static.`defaultPlan`,group_concat(`signal_timings`.`StageNumber` ORDER BY execOrder separator ',') as StageNumber,utmc_traffic_signal_static.`oldPlanId`, plans.`CriticalStage` FROM `utmc_traffic_signal_static` INNER JOIN `plans` ON `plans`.`ID`=`utmc_traffic_signal_static`.`currentPlan` INNER JOIN `signal_timings` ON `signal_timings`.`SignalSCN`='"+signal_scn+"' AND `signal_timings`.`Plan_SCN`=`plans`.`PlanSCN` AND execOrder <> 0 INNER JOIN `utmc_traffic_signal_stages` ON `utmc_traffic_signal_stages`.`SignalSCN` = `utmc_traffic_signal_static`.`SignalSCN` AND `utmc_traffic_signal_stages`.`SignalSCN`='"+signal_scn+"' AND `utmc_traffic_signal_stages`.`StageOrder`=`signal_timings`.`StageNumber` WHERE `utmc_traffic_signal_static`.`SignalSCN`='"+signal_scn+"'")
	planresult = cur.fetchone()
	defaultPlanId = planresult[10]
	currentPlanId = planresult[9]
	oldPlanId = planresult[12]
	# defplan = map(int,planresult[0].split(","))
	is_active = planresult[1]
	# defplan_inter = map(int,planresult[2].split(","))
	# plan_ug405_reply_pin = planresult[3].split(",")
	# plan_ug405_pin = planresult[4].split(",")
	planforcebit = planresult[5]
	currentMode = planresult[6]
	planscn = planresult[7]
	# stageNumber = map(int,planresult[11].split(","))
	# CriticalStage = planresult[13]

	# if (secondsSinceMidnight(datetime.now()) > startDayTime or secondsSinceMidnight(datetime.now()) < endDayTime) and cMode != '8':
	# 	cur.execute("UPDATE `utmc_traffic_signal_static` SET currentMode='"+str(previousModeId)+"' WHERE SignalSCN='"+signal_scn+"'")
	# 	db.commit()

	if is_active == 0:
		# #print(str(planresult)+"\n")
		print("Came to offline")
		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n", end='')
		#value 25196, 86400
		if secondsSinceMidnight(datetime.now()) < startDayTime + 300 or secondsSinceMidnight(datetime.now()) > endDayTime:
			#change it to auto mode
			if currentMode == "7":
				# cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentMode`='8',currentPlan='"+str(defaultPlanId)+"', oldPlanId='"+str(defaultPlanId)+"' WHERE SignalSCN='"+signal_scn+"'")
				# db.commit()
				cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentMode`='8' WHERE SignalSCN='"+signal_scn+"'")
				db.commit()
				cur.execute("INSERT INTO tis_signal_mode_change_log (SignalSCN, user, previousMode, previousModeId, newMode, newModeId, changeReason) VALUES ('"+str(signal_scn)+"', 'admin', 'manualoperation', '7', 'flash','8', 'Switching to Flash Mode at End Of Day')")
				db.commit()

			cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 1, 0, 0, '0000000000000002') ")
			db.commit()
			cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 1, 0, 0, '0000000000000002') ")
			db.commit()
			cur.execute("UPDATE `utmc_traffic_signal_static` SET `is_active`=0, currentMode='8' WHERE SignalSCN='"+signal_scn+"'")
			db.commit()
			sendSocketMessage(site_id,"Flash,"+signal_scn+"pass")
			cur.close()
			db.close()
			sys.exit(0)
		

		if secondsSinceMidnight(runPlanClicked) > secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time):
			if currentPlanId == oldPlanId:
				start_time = secondsSinceMidnightISTTosecondsSinceMidnightUTC(secondsSinceMidnight(runPlanClicked))
			# else:
			# 	start_time = secondsSinceMidnightISTTosecondsSinceMidnightUTC(secondsSinceMidnight(runPlanClicked))

		# print(runPlanClicked)
		# print(start_time, end=" startime\n")
		# print(end_time, end=" endtime\n")
		# print(CycleTime, end=" cycletime\n")

		cur.execute("UPDATE `utmc_traffic_signal_static` SET `is_active`='1' WHERE SignalSCN='"+signal_scn+"'")
		db.commit()

		sendSocketMessage(site_id,"TimOnline,"+signal_scn+"pass")
		sendSocketMessage("JunctionAlerts","TimOnline,"+signal_scn+"pass")
		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " TIM Online " + signal_scn + "\n", end='')

		if cMode == "8":
			cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ("+str(site_id)+", 1, 1, 0, 0, '0000000000000000', '0000000000000002') ")
			db.commit()
			cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ("+str(site_id)+", 1, 1, 0, 0, '0000000000000000', '0000000000000002') ")
			db.commit()
			sendSocketMessage(site_id,"Flash,"+signal_scn+"pass")
		elif cMode == '15':
			cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 0, 1, '0000000000000000', '0000000000000040') ")
			db.commit()
			cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 0, 1, '0000000000000000', '0000000000000040') ")
			db.commit()
			try:
				sendSocketMessage(site_id,"LampOff,"+signal_scn+"pass")
			except Exception as e:
				print(e)
		elif cMode == "17":
			cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 1, 0, '0000000000000001') ")
			db.commit()
			cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 1, 0, '0000000000000001') ")
			db.commit()
			sendSocketMessage(site_id,"AllRed,"+signal_scn+"pass")
		else:
			pass
			timings_to_insert = []
			stages_at_insert = []
			planStartedTime = secondsSinceMidnight(runPlanClicked)
			
			while(planStartedTime > 0):
				planStartedTime = planStartedTime - (CycleTime)
			endPlanTime = 86400
			looperTime = planStartedTime
			# print(str(looperTime)+" loopertime\n", end='')
			looper = 0
			if end_time == 10:
				end_time = 86410
			# print(str(start_time))
			# print(str(end_time))
			startIST = secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time)
			endIST = secondsSinceMidnightUTCTosecondsSinceMidnightIST(end_time)
			print("++"+str(startIST)+" "+str(endIST)+"++\n")		

			# stagesInHex = ''.join([format(k,'02x').upper() for k in stagetimings])
			# Fn = stagesInHex + ''.join(['0' for k in range(0,16 - len(stagesInHex))])

			if endIST == 10:
				endIST = 86410
			while(True):
				if looperTime < endIST and looperTime >= startIST:
					timings_to_insert.append(secondsSinceMidnightISTTosecondsSinceMidnightUTC(looperTime))
					stages_at_insert.append(stageNumber[looper] - 1)
				looperTime = looperTime + stagetimings[looper] + interstagetimings[looper]
				looper = looper + 1 
				looper = 0 if looper == len(stagetimings) else looper
				if looperTime > endPlanTime:
					break

			numStages = len(stageSeq.split(','))#format(len(stageSeq.split(',')),'02x').upper()
			stageOrderHex = [format(int(n),'02x').upper() for n in stageSeq.split(',')]

			print(stages_at_insert,end="\n")
			for value in range(0, len(timings_to_insert)):			
				if timings_to_insert[value] + 2 > 86400:
					timings_to_insert[value] = timings_to_insert[value] - 2
				if timings_to_insert[value] <= 10 and timings_to_insert[value] >= 0:
					time.sleep(60)
				
				# stageInHex = ''.join([format((int(stages_at_insert[value])+1),'02x').upper()])
				# Fn = ''.join(['0' for k in range(0,16 - len(stageInHex))]) + stageInHex
				
				totalStageTimeList = [x for x, y in zip(stagetimings, interstagetimings)]
				timingsInHex = ''.join([format(x,'02x').upper() for x in totalStageTimeList])

				stageInHex = (format(constantStageOrder,'02x').upper()) + ''.join([format((int(stages_at_insert[value])+1),'02x').upper()])
				# Fn = ''.join(['0' for k in range(0,len(timingsInHex) - len(stageInHex))]) + stageInHex
				Fn = timingsInHex + ''.join(['0' for k in range(0,16 - (len(timingsInHex)+len(stageInHex)))]) + stageInHex

				SFn = str(format(int(CriticalStage),'02x').upper()) + str(numStages) + str(is_va_active) #str(format(int(is_va_active),'02x').upper())
				SFn += ''.join(stageOrderHex)
				SFn += ''.join(['0' for k in range(0,16 - (len(SFn)))])
				
				stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`, `utcControlSFn`, utcControlTO, utcControlLO, utcControlFF)"
				# stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(ug405_pin[int(stages_at_insert[value])])+"`, `"+str(ug405_reply_pin[int(stages_at_insert[value])])+"`"
				# for key in pinsarray:
				# 	if key != str(ug405_reply_pin[stages_at_insert[value]]):
				# 		stmt += ", `"+str(key)+"`"
				stmt1 = stmt + " VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+",'"+Fn+"','"+SFn+"', 1, 0, 0);"
				# stmt1 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+","+fb+","+fb+",0,0,0,0,1);"
				
				# print(stmt1)
				print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
				print("[INFO] ", end='')
				print("[ATCS] ", end='')
				print("[Control] ", end='')
				print("[utcControlFn "+Fn[len(Fn)-1]+"] ", end='')
				print("["+str(site_id)+"] ", end='')
				print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(timings_to_insert[value]))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
				cur.execute(stmt1)
				db.commit()
				cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
				db.commit()

			time.sleep(1)

		#cur.execute("UPDATE utmc_traffic_signal_dynamic SET HistoricDate=NOW() WHERE SystemCodeNumber='"+signal_scn+"' AND HistoricDate IS NULL")
		#db.commit()

		#cur.execute("INSERT INTO `utmc_traffic_signal_dynamic`(`SystemCodeNumber`, `ControlStrategy`, `PlanNumber`, `StageSequence`, `PlanTimings`, `LastUpdated`, `NextStagePin`, `StartScheduled`, `StartManual`, `StartAuto`, `ForceBidNextStagePin`, `ForceBidManual`, `ForceBidAuto`, `ForceBidScheduled`, `Reality`, `HistoricDate`) VALUES ('"+signal_scn+"', '"+str(previousModeId)+"', '"+str(currentPlanId)+"', '"+stageSeq+"', '"+plan_timings+"', NOW(), '0', NULL, '0', '0', 1, 1, 0, 0, 'Real', NULL)")
		#db.commit()
				
	elif manual == "1":
		print("Came to manual operation")
		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n", end='')
		stagesInHex = ''.join([format(k,'02x').upper() for k in stagetimings])
		Fn = stagesInHex + ''.join(['0' for k in range(0,16 - len(stagesInHex))])

		numStages = len(stageSeq.split(','))#format(len(stageSeq.split(',')),'02x').upper()
		stageOrderHex = [format(int(n),'02x').upper() for n in stageSeq.split(',')]

		while(True):
			stmt  = ""
			stmt1 = ""
			stmt2 = ""
			if start_time <= end_time:
				# stageInHex = ''.join([format((int(i)+1),'02x').upper()])
				# Fn = ''.join(['0' for k in range(0,16 - len(stageInHex))]) + stageInHex
				
				totalStageTimeList = [x for x, y in zip(stagetimings, interstagetimings)]
				timingsInHex = ''.join([format(x,'02x').upper() for x in totalStageTimeList])

				# stageInHex = ''.join([format((int(ic)+1),'02x').upper()])
				stageInHex = (format(constantStageOrder,'02x').upper()) + ''.join([format((int(stageNumber[ic])),'02x').upper()])

				# Fn = ''.join(['0' for k in range(0,len(timingsInHex) - len(stageInHex))]) + stageInHex
				Fn = timingsInHex + ''.join(['0' for k in range(0,16 - (len(timingsInHex)+len(stageInHex)))]) + stageInHex
				
				SFn = str(format(int(CriticalStage),'02x').upper()) + str(numStages) + str(is_va_active) #str(format(int(is_va_active),'02x').upper())
				SFn += ''.join(stageOrderHex)
				SFn += ''.join(['0' for k in range(0,16 - (len(SFn)))])

				stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`, `utcControlSFn`, utcControlTO, utcControlLO, utcControlFF)"
				# stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(ug405_pin[i])+"`, `"+str(ug405_reply_pin[i])+"`"
				# for key in pinsarray:
				# 	if key != str(ug405_reply_pin[i]):
				# 		stmt += ", `"+str(key)+"`"
				stmt1 = stmt + " VALUES ("+str(site_id)+","+str(int(start_time)+2)+",'"+Fn+"','"+SFn+"', 1, 0, 0)"
				#print(stmt1 + " \n")
				cur.execute(stmt1)
				db.commit()
				cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
				db.commit()

				# stmt2 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(int(start_time)+3)+","+sb+","+sb+",0,0,0,0,0)"
				# #print(stmt2 + " \n\n")
				# cur.execute(stmt2)
				# db.commit()
				# cur.execute(stmt2.replace("utcControlTable","utcControlTable_dummy"))
				# db.commit()
				print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
				print("[INFO] ", end='')
				print("[ATCS] ", end='')
				print("[Control] ", end='')
				print("[utcControlFn "+Fn[len(Fn)-1]+"] ", end='')
				print("["+str(site_id)+"] ", end='')
				print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
				
				# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
				# print("[INFO] ", end='')
				# print("[ATCS] ", end='')
				# print("[Control] ", end='')
				# print("["+str(ug405_reply_pin[i])+" "+str(sb)+"] ", end='')
				# print("["+str(site_id)+"] ", end='')
				# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time+1))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
				start_time = start_time + stagetimings[ic] + interstagetimings[ic]
				ic = ic + 1
				ic = 0 if ic == len(stagetimings) else ic
				db.commit()
			else:
				ic = ic-1
				ic = len(stagetimings)-1 if ic < 0 else ic
				start_time = start_time - stagetimings[ic] - interstagetimings[ic]
				break
		# cur.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+","+str(int(end_time)+10)+",0)")
		# db.commit()
		# cur.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+","+str(int(end_time)+10)+",0)")
		# db.commit()

		# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ")
		# print("[INFO] ")
		# print("[ATCS] ")
		# print("[Control] ")
		# print("[utcControlHI 0] ")
		# print("["+str(site_id)+"] ")
		# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(int(end_time)+10)).strftime("%Y-%m-%d %H:%M:%S"))+"]\n")
		# cur.execute("INSERT INTO tis_signal_mode_change_log (SignalSCN,user,previousMode,newMode) VALUES ('"+str(signal_scn)+"','admin','manualplan','manualplan')")
		# db.commit()
		# cur.close()
		# db.close()
	elif cMode == "7":
		print("Came to Only Manual")
		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n", end='')


                cur.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`, utcControlTO, utcControlFF, utcControlLO, utcControlSFn, utcControlDn) VALUES ('"+str(site_id)+"',1,'"+currentStageOrder+"',1,0,0, '0000000000000000', '0000000000000100')")
		db.commit()

		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
		print("[INFO] ", end='')
		print("[ATCS] ", end='')
		print("[Control] ", end='')
		print("[utcControlFn "+currentStageOrder+"] ", end='')
		print("["+str(site_id)+"] ", end='')
		print("[utcControlTimestamp: 1", end='')


		if secondsSinceMidnight(datetime.now()) < startDayTime + 300 or secondsSinceMidnight(datetime.now()) > endDayTime:
			# cur.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,0)")
			# db.commit()
			# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
			# print("[INFO] ", end='')
			# print("[ATCS] ", end='')
			# print("[Control] ", end='')
			# print("[utcControlHI 0] ", end='')
			# print("["+str(site_id)+"] ", end='')
			# print("[utcControlTimestamp: "+(datetime.now()).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
			# cur.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,0)")
			# db.commit()
			cur.execute("UPDATE `utmc_traffic_signal_static` SET lastStageChanged='now()',`runPlanClicked`='"+datetime.now().strftime("%Y-%m-%d")+" 06:59:56', `is_active`=0 WHERE SignalSCN='"+signal_scn+"'")
			db.commit()
			sendSocketMessage(site_id,"Flash,"+signal_scn+"pass")
			cur.close()
			db.close()
			sys.exit(0)
	elif (cMode == "8" or cMode == "15" or cMode == "17") and is_manual_active == '0':
		print("Came to flash")
		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n", end='')
		#if is_manual_active == '1':
		#	print('manual control')
		#	sys.exit(0)

		if secondsSinceMidnight(datetime.now()) < startDayTime + 300 or secondsSinceMidnight(datetime.now()) > endDayTime:
			#change it to auto mode
			if currentMode == "7":
				# cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentMode`='8',currentPlan='"+str(defaultPlanId)+"', oldPlanId='"+str(defaultPlanId)+"' WHERE SignalSCN='"+signal_scn+"'")
				# db.commit()
				cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentMode`='8' WHERE SignalSCN='"+signal_scn+"'")
				db.commit()
				cur.execute("INSERT INTO tis_signal_mode_change_log (SignalSCN, user, previousMode, previousModeId, newMode, newModeId, changeReason) VALUES ('"+str(signal_scn)+"', 'admin', 'manualoperation', '7', 'flash','8', 'Switching to Flash Mode at End Of Day')")
				db.commit()

			cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn, utcControlDn) VALUES ('"+str(site_id)+"', 1, 1, 0, 0, '0000000000000002', '0000000000000000') ")
			db.commit()
			cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn, utcControlDn) VALUES ('"+str(site_id)+"', 1, 1, 0, 0, '0000000000000002', '0000000000000000') ")
			db.commit()
			cur.execute("UPDATE `utmc_traffic_signal_static` SET `is_active`=1, currentMode='8' WHERE SignalSCN='"+signal_scn+"'")
			db.commit()
			if changeReason != 'Switching to Flash Mode at End Of Day':
				cur.execute("INSERT INTO tis_signal_mode_change_log (SignalSCN, user, previousMode, previousModeId, newMode, newModeId, changeReason) VALUES ('"+str(signal_scn)+"', 'admin', '"+newMode+"', '"+str(currentModeId)+"', 'flash','8', 'Switching to Flash Mode at End Of Day')")
				db.commit()
			sendSocketMessage(site_id,"Flash,"+signal_scn+"pass")
			cur.close()
			db.close()
			sys.exit(0)

		#if (secondsSinceMidnight(datetime.now()) > startDayTime + 300 or secondsSinceMidnight(datetime.now()) < endDayTime) and (currentModeId != '8' and currentModeId != '15' and currentModeId != '17'):
		if secondsSinceMidnight(datetime.now()) > startDayTime + 300 or secondsSinceMidnight(datetime.now()) < endDayTime:
			print("Starting day routine")

			if changeReason != 'Switching to Flash Mode at End Of Day':
				if cMode == "8":
					cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ("+str(site_id)+", 1, 1, 0, 0, '0000000000000000', '0000000000000002') ")
					db.commit()
					cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ("+str(site_id)+", 1, 1, 0, 0, '0000000000000000', '0000000000000002') ")
					db.commit()
					sendSocketMessage(site_id,"Flash,"+signal_scn+"pass")
				elif cMode == '15':
					cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 0, 1, '0000000000000000', '0000000000000040') ")
					db.commit()
					cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 0, 1, '0000000000000000', '0000000000000040') ")
					db.commit()
					try:
						sendSocketMessage(site_id,"LampOff,"+signal_scn+"pass")
					except Exception as e:
						print(e)
				elif cMode == "17":
					cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 1, 0, '0000000000000001') ")
					db.commit()
					cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 1, 0, '0000000000000001') ")
					db.commit()
					sendSocketMessage(site_id,"AllRed,"+signal_scn+"pass")

				sys.exit(0)

			if previousModeId == "8":
				cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ("+str(site_id)+", 1, 1, 0, 0, '0000000000000000', '0000000000000002') ")
				db.commit()
				cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ("+str(site_id)+", 1, 1, 0, 0, '0000000000000000', '0000000000000002') ")
				db.commit()
				sendSocketMessage(site_id,"Flash,"+signal_scn+"pass")
			elif previousModeId == '15':
				cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 0, 1, '0000000000000000', '0000000000000040') ")
				db.commit()
				cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 0, 1, '0000000000000000', '0000000000000040') ")
				db.commit()
				try:
					sendSocketMessage(site_id,"LampOff,"+signal_scn+"pass")
				except Exception as e:
					print(e)
			elif previousModeId == "17":
				cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 1, 0, '0000000000000001') ")
				db.commit()
				cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 1, 0, '0000000000000001') ")
				db.commit()
				sendSocketMessage(site_id,"AllRed,"+signal_scn+"pass")
			else:

				stagesInHex = ''.join([format(k,'02x').upper() for k in stagetimings])
				Fn = stagesInHex + ''.join(['0' for k in range(0,16 - len(stagesInHex))])

				numStages = len(stageSeq.split(','))#format(len(stageSeq.split(',')),'02x').upper()
				stageOrderHex = [format(int(n),'02x').upper() for n in stageSeq.split(',')]

				runPlanClicked = (secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time))).strftime("%Y-%m-%d %H:%M:%S")
				st = 0
				while(True):
					stmt  = ""
					stmt1 = ""
					stmt2 = ""
					if start_time <= end_time:
						# stageInHex = ''.join([format((int(i)+1),'02x').upper()])
						# Fn = ''.join(['0' for k in range(0,16 - len(stageInHex))]) + stageInHex
						
						totalStageTimeList = [x for x, y in zip(stagetimings, interstagetimings)]
						timingsInHex = ''.join([format(x,'02x').upper() for x in totalStageTimeList])

						# stageInHex = ''.join([format((int(ic)+1),'02x').upper()])
						stageInHex = (format(constantStageOrder,'02x').upper()) + ''.join([format((int(stageNumber[ic])),'02x').upper()])

						# Fn = ''.join(['0' for k in range(0,len(timingsInHex) - len(stageInHex))]) + stageInHex
						Fn = timingsInHex + ''.join(['0' for k in range(0,16 - (len(timingsInHex)+len(stageInHex)))]) + stageInHex
						
						SFn = str(format(int(CriticalStage),'02x').upper()) + str(numStages) + str(is_va_active) #str(format(int(is_va_active),'02x').upper())
						SFn += ''.join(stageOrderHex)
						SFn += ''.join(['0' for k in range(0,16 - (len(SFn)))])

						stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`, `utcControlSFn`, utcControlTO, utcControlLO, utcControlFF)"
						# stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(ug405_pin[i])+"`, `"+str(ug405_reply_pin[i])+"`"
						# for key in pinsarray:
						# 	if key != str(ug405_reply_pin[i]):
						# 		stmt += ", `"+str(key)+"`"
						if st == 0:
							stmt1 = stmt + " VALUES ("+str(site_id)+",'1','"+Fn+"','"+SFn+"', 1, 0, 0)"
						else:
							stmt1 = stmt + " VALUES ("+str(site_id)+","+str(int(start_time)+2)+",'"+Fn+"','"+SFn+"', 1, 0, 0)"
						#print(stmt1 + " \n")
						cur.execute(stmt1)
						db.commit()
						cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
						db.commit()

						# stmt2 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(int(start_time)+3)+","+sb+","+sb+",0,0,0,0,0)"
						# #print(stmt2 + " \n\n")
						# cur.execute(stmt2)
						# db.commit()
						# cur.execute(stmt2.replace("utcControlTable","utcControlTable_dummy"))
						# db.commit()
						print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
						print("[INFO] ", end='')
						print("[ATCS] ", end='')
						print("[Control] ", end='')
						print("[utcControlFn "+Fn[len(Fn)-1]+"] ", end='')
						print("["+str(site_id)+"] ", end='')
						print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
						
						# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
						# print("[INFO] ", end='')
						# print("[ATCS] ", end='')
						# print("[Control] ", end='')
						# print("["+str(ug405_reply_pin[i])+" "+str(sb)+"] ", end='')
						# print("["+str(site_id)+"] ", end='')
						# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time+1))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
						start_time = start_time + stagetimings[ic] + interstagetimings[ic]
						ic = ic + 1
						ic = 0 if ic == len(stagetimings) else ic
						db.commit()
					else:
						ic = ic-1
						ic = len(stagetimings)-1 if ic < 0 else ic
						start_time = start_time - stagetimings[ic] - interstagetimings[ic]
						break

			if previousModeId == '16':
				cur.execute("SELECT previousMode, previousModeId, newModeId, newMode, changeReason, timestamp FROM `tis_signal_mode_change_log` WHERE `SignalSCN`='"+signal_scn+"' AND timestamp < '"+str(last_mode_timestamp)+"' ORDER BY timestamp DESC LIMIT 1")
				last_signalmodedata = cur.fetchone()
				previousMode = last_signalmodedata[0]
				previousModeId = str(last_signalmodedata[1])
				currentModeId = str(last_signalmodedata[2])
				newMode = str(last_signalmodedata[3])

			cur.execute("UPDATE `utmc_traffic_signal_static` SET `runPlanClicked`='"+str(runPlanClicked)+"',`oldPlanClicked`='"+str(runPlanClicked)+"', `is_active`='1',oldPlanId='"+str(currentPlanId)+"',currentPlan='"+str(currentPlanId)+"', currentMode='"+str(previousModeId)+"' WHERE SignalSCN='"+signal_scn+"'")
			db.commit()
			
			cur.execute("INSERT INTO tis_signal_mode_change_log (SignalSCN, user, previousMode, newMode, previousModeId, newModeId, changeReason) VALUES ('"+str(signal_scn)+"', 'admin', 'flash', '"+str(previousMode)+"', '8', '"+str(previousModeId)+"', 'Starting the day with the last running Mode.')")
			db.commit()
			
			cur.execute("UPDATE utmc_traffic_signal_dynamic SET HistoricDate=NOW() WHERE SystemCodeNumber='"+signal_scn+"' AND HistoricDate IS NULL")
			db.commit()

			cur.execute("INSERT INTO `utmc_traffic_signal_dynamic`(`SystemCodeNumber`, `ControlStrategy`, `PlanNumber`, `StageSequence`, `PlanTimings`, `LastUpdated`, `NextStagePin`, `StartScheduled`, `StartManual`, `StartAuto`, `ForceBidNextStagePin`, `ForceBidManual`, `ForceBidAuto`, `ForceBidScheduled`, `Reality`, `HistoricDate`) VALUES ('"+signal_scn+"', '"+str(previousModeId)+"', '"+str(currentPlanId)+"', '"+stageSeq+"', '"+plan_timings+"', NOW(), '0', NULL, '0', '0', 1, 1, 0, 0, 'Real', NULL)")
			db.commit()
			
			sendSocketMessage(site_id,"TimOnline,"+signal_scn+"pass")
			sendSocketMessage("JunctionAlerts","TimOnline,"+signal_scn+"pass")
			print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " TimOnline "+signal_scn+"\n", end='')

			# plan_data = {}
			# i = 0
			# cur.execute("SELECT group_concat(`signal_timings`.`StageTime` ORDER BY execOrder separator ',') as StageTime,`utmc_traffic_signal_static`.`is_active`,group_concat(`signal_timings`.`InterStageTime` ORDER BY execOrder separator ',') as InterStageTime,group_concat(`utmc_traffic_signal_stages`.`ug405_reply_pin` ORDER BY execOrder separator ',') as ug405_reply_pin,group_concat(`utmc_traffic_signal_stages`.`ug405_pin` ORDER BY execOrder separator ',') as ug405_pin,`utmc_traffic_signal_static`.`ForceBidNextStagePin`,`utmc_traffic_signal_static`.`currentMode`,`plans`.`PlanSCN`,`plans`.`CycleTime`,utmc_traffic_signal_static.`currentPlan`,utmc_traffic_signal_static.`defaultPlan`, group_concat(`signal_timings`.`StageNumber` ORDER BY execOrder separator ',') as StageNumber, plans.`CriticalStage` FROM `utmc_traffic_signal_static` INNER JOIN `plans` ON `plans`.`ID`=`utmc_traffic_signal_static`.`currentPlan` INNER JOIN `signal_timings` ON `signal_timings`.`SignalSCN`='"+signal_scn+"' AND `signal_timings`.`Plan_SCN`=`plans`.`PlanSCN` AND execOrder <> 0 INNER JOIN `utmc_traffic_signal_stages` ON `utmc_traffic_signal_stages`.`SignalSCN` = `utmc_traffic_signal_static`.`SignalSCN` AND `utmc_traffic_signal_stages`.`SignalSCN`='"+signal_scn+"' AND `utmc_traffic_signal_stages`.`StageOrder`=`signal_timings`.`StageNumber` WHERE `utmc_traffic_signal_static`.`SignalSCN`='"+signal_scn+"'")
			# planresult_offline = cur.fetchone()
			# defplan_offline = map(int,planresult_offline[0].split(","))
			# nStages_offline = len(defplan_offline)
			# defplan_inter_offline = map(int,planresult_offline[2].split(","))
			# defplan_stagenumber = map(int,planresult_offline[11].split(","))
			# CriticalStage = planresult_offline[12]

			# while(startDayTime < endDayTime):
			# 	plan_data[i] = []
			# 	for nStages_offline in range(0, len(defplan_offline)):
			# 		plan_data[i].append((startDayTime, startDayTime+defplan_offline[nStages_offline]+defplan_inter_offline[nStages_offline]))
			# 		startDayTime = startDayTime + defplan_offline[nStages_offline] + defplan_inter_offline[nStages_offline]
			# 	i = i+1
			# istCurrentTime = secondsSinceMidnight(datetime.now())
			# currentCycleNumber = 0
			# for key in plan_data:
			# 	if istCurrentTime >= plan_data[key][0][0] and istCurrentTime < plan_data[key][len(plan_data[key])-1][1]:
			# 		currentCycleNumber = key
			# 		break
			# cycleRunTimeRequired = 0
			# startAdding = 0
			# currentStageRunning = 0
			# for interval in plan_data[currentCycleNumber]:
			# 	if istCurrentTime > interval[0] and istCurrentTime < interval[1] and startAdding == 0:
			# 		for checker in range(0,len(plan_data[currentCycleNumber])):
			# 			if interval[0] == plan_data[currentCycleNumber][checker][0]:
			# 				currentStageRunning = checker + 1
			# 		startAdding = 1
			# 	if startAdding == 1:
			# 		cycleRunTimeRequired = min((interval[1]-interval[0]), interval[1]-istCurrentTime)
			# 		break
			# endTimeFixedMode = plan_data[currentCycleNumber][len(plan_data[currentCycleNumber])-1][1]
			# cycleRunTimeRequired = endTimeFixedMode - istCurrentTime
			# if cycleRunTimeRequired > 60:
			# 	cur.close()
			# 	db.close()
			# 	sys.exit(0)
			# else:
			# 	endTimeFixedMode = plan_data[currentCycleNumber][len(plan_data[currentCycleNumber])-1][1]
				
			# 	istCurrentTime = secondsSinceMidnight(datetime.now())
			# 	print(" "+str(endTimeFixedMode - istCurrentTime)+" ")
			# 	time.sleep(endTimeFixedMode - istCurrentTime)
			# 	cur.execute("UPDATE `utmc_traffic_signal_static` SET `runPlanClicked`='"+secondsSinceMidnightToIST(endTimeFixedMode).strftime("%Y-%m-%d %H:%M:%S")+"',`oldPlanClicked`='"+secondsSinceMidnightToIST(endTimeFixedMode).strftime("%Y-%m-%d %H:%M:%S")+"', `is_active`='1',oldPlanId='"+str(currentPlanId)+"',currentPlan='"+str(currentPlanId)+"', currentMode='"+str(currentModeId)+"' WHERE SignalSCN='"+signal_scn+"'")
			# 	db.commit()
				
			# 	cur.execute("INSERT INTO tis_signal_mode_change_log (SignalSCN, user, previousMode, newMode, previousModeId, newModeId, changeReason) VALUES ('"+str(signal_scn)+"', 'admin', '"+("flash" if cMode == "8" else "lampoff")+"', '"+str(newMode)+"', '"+str(cMode)+"', '"+str(currentModeId)+"', 'Starting the day with the Mode running last night.')")
			# 	db.commit()
			# 	sendSocketMessage(site_id,"TimOnline,"+signal_scn+"pass")
			# 	sendSocketMessage("JunctionAlerts","TimOnline,"+signal_scn+"pass")
			# 	print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " TimOnline "+signal_scn+"\n", end='')
			# 	start_time = endTimeFixedMode
			# 	end_time = secondsSinceMidnight(datetime.now().replace(second=0, microsecond=0)) + 70
			# 	timings_to_insert = []
			# 	stages_at_insert = []
			# 	planStartedTime = start_time
			# 	endPlanTime = 86400
			# 	looperTime = planStartedTime
			# 	looper = 0
			# 	while(True):
			# 		if looperTime <= end_time and looperTime >= start_time:
			# 			timings_to_insert.append(secondsSinceMidnightISTTosecondsSinceMidnightUTC(looperTime))
			# 			stages_at_insert.append(defplan_stagenumber[looper] - 1)
			# 		looperTime = looperTime + stagetimings[looper] + interstagetimings[looper]
			# 		looper = looper + 1 
			# 		looper = 0 if looper == len(stagetimings) else looper
			# 		if looperTime > endPlanTime:
			# 			break
			# 	check_first = 0
			# 	for value in range(0, len(timings_to_insert)):
			# 		totalStageTimeList = [x + y for x, y in zip(defplan_offline, defplan_inter_offline)]
			# 		timingsInHex = ''.join([format(x,'02x').upper() for x in totalStageTimeList])

			# 		stageInHex = ''.join([format((int(stages_at_insert[value])+1),'02x').upper()])
					
			# 		Fn = timingsInHex + ''.join(['0' for k in range(0,16 - (len(timingsInHex)+len(stageInHex)))]) + stageInHex
					
			# 		SFn = str(format(int(CriticalStage),'02x').upper()) + '0' + str(is_va_active) #str(format(int(is_va_active),'02x').upper())
			# 		SFn += ''.join(['0' for k in range(0,16 - (len(SFn)))])

			# 		stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`, `utcControlSFn`, utcControlTO, utcControlLO, utcControlFF)"

			# 		stmt1 = ""
			# 		if check_first == 0:
			# 			stmt1 = stmt + " VALUES ("+str(site_id)+",1,'"+Fn+"','"+SFn+"', 1, 0, 0)"
			# 		else:
			# 			stmt1 = stmt + " VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+",'"+SFn+"', 1, 0, 0)"
			# 		cur.execute(stmt1)
			# 		db.commit()
			# 		cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
			# 		db.commit()

			# 		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
			# 		print("[INFO] ", end='')
			# 		print("[ATCS] ", end='')
			# 		print("[Control] ", end='')
			# 		# print("[utcControlFn "+str(Fn).replace('0','')+"] ", end='')
			# 		print("[utcControlFn "+Fn[len(Fn)-1]+"] ", end='')
			# 		print("["+str(site_id)+"] ", end='')
			# 		print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(timings_to_insert[value]))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')

			cur.close()
			db.close()
			sys.exit(0)
		'''
		if cMode == "8":
			cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn) VALUES ("+str(site_id)+", 1, 1, 0, 0, '0000000000000000') ")
			db.commit()
			cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn) VALUES ("+str(site_id)+", 1, 1, 0, 0, '0000000000000000') ")
			db.commit()
			sendSocketMessage(site_id,"Flash,"+signal_scn+"pass")
		elif cMode == '15':
			cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn) VALUES ('"+str(site_id)+"', 1, 0, 0, 1, '0000000000000000') ")
			db.commit()
			cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn) VALUES ('"+str(site_id)+"', 1, 0, 0, 1, '0000000000000000') ")
			db.commit()
			try:
				sendSocketMessage(site_id,"LampOff,"+signal_scn+"pass")
			except Exception as e:
				print(e)
		elif cMode == "17":
			cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 1, 0, '0000000000000001') ")
			db.commit()
			cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 0, 1, 0, '0000000000000001') ")
			db.commit()
			sendSocketMessage(site_id,"AllRed,"+signal_scn+"pass")
		'''
		# else:
		# 	cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO) VALUES ('"+str(site_id)+"', 1, 0, 0, 1) ")
		# 	db.commit()
		# 	cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO) VALUES ('"+str(site_id)+"', 1, 0, 0, 1) ")
		# 	db.commit()
		# 	sendSocketMessage(site_id,"LampOff,"+signal_scn+"pass")

		cur.close()
		db.close()
		sys.exit(0)
	else:
		print("Came to else")
		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n", end='')
		# print(signal_scn,end=" scn\n")
		print(runPlanClicked,end=" runplan\n")
		# print(currentPlanId,end=" currentplan\n")
		# print(start_time, end=" startime\n")
		if secondsSinceMidnight(datetime.now()) < startDayTime + 300 or secondsSinceMidnight(datetime.now()) > endDayTime:
			if secondsSinceMidnight(datetime.now()) > startDayTime + 60:
				plan_data = {}
				i = 0

				cur.execute("SELECT group_concat(`signal_timings`.`StageTime` ORDER BY execOrder separator ',') as StageTime,`utmc_traffic_signal_static`.`is_active`,group_concat(`signal_timings`.`InterStageTime` ORDER BY execOrder separator ',') as InterStageTime,group_concat(`utmc_traffic_signal_stages`.`ug405_reply_pin` ORDER BY execOrder separator ',') as ug405_reply_pin,group_concat(`utmc_traffic_signal_stages`.`ug405_pin` ORDER BY execOrder separator ',') as ug405_pin,`utmc_traffic_signal_static`.`ForceBidNextStagePin`,`utmc_traffic_signal_static`.`currentMode`,`plans`.`PlanSCN`,`plans`.`CycleTime`,utmc_traffic_signal_static.`currentPlan`,utmc_traffic_signal_static.`defaultPlan`,group_concat(`signal_timings`.`StageNumber` ORDER BY execOrder separator ',') as StageNumber, plans.`CriticalStage` FROM `utmc_traffic_signal_static` INNER JOIN `plans` ON `plans`.`ID`=`utmc_traffic_signal_static`.`currentPlan` INNER JOIN `signal_timings` ON `signal_timings`.`SignalSCN`='"+signal_scn+"' AND `signal_timings`.`Plan_SCN`=`plans`.`PlanSCN` AND execOrder <> 0 INNER JOIN `utmc_traffic_signal_stages` ON `utmc_traffic_signal_stages`.`SignalSCN` = `utmc_traffic_signal_static`.`SignalSCN` AND `utmc_traffic_signal_stages`.`SignalSCN`='"+signal_scn+"' AND `utmc_traffic_signal_stages`.`StageOrder`=`signal_timings`.`StageNumber` WHERE `utmc_traffic_signal_static`.`SignalSCN`='"+signal_scn+"'")
				planresult = cur.fetchone()
				defaultPlanId = planresult[10]
				currentPlanId = planresult[9]
				defplan = map(int,planresult[0].split(","))
				is_active = planresult[1]
				defplan_inter = map(int,planresult[2].split(","))
				# plan_ug405_reply_pin = planresult[3].split(",")
				# plan_ug405_pin = planresult[4].split(",")
				planforcebit = planresult[5]
				currentMode = planresult[6]
				planscn = planresult[7]
				stageNumber = map(int,planresult[11].split(","))
				# CriticalStage = planresult[12]
				stageOrderHex = [format(int(n),'02x').upper() for n in planresult[11].split(',')]

				if secondsSinceMidnight(datetime.now()) < startDayTime or secondsSinceMidnight(datetime.now()) > endDayTime:
					cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ('"+str(site_id)+"', 1, 1, 0, 0, '0000000000000000', '0000000000000002') ")
					db.commit()
					cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlDn, utcControlFn) VALUES ('"+str(site_id)+"', 1, 1, 0, 0, '0000000000000000', '0000000000000002') ")
					db.commit()
					cur.execute("UPDATE `utmc_traffic_signal_static` SET currentMode='8' WHERE SignalSCN='"+signal_scn+"'")
					db.commit()
					sendSocketMessage(site_id,"Flash,"+signal_scn+"pass")
					cur.close()
					db.close()
					sys.exit(0)
				while(startDayTime < endDayTime):
					plan_data[i] = []
					for nStages in range(0, len(defplan)):
						plan_data[i].append((startDayTime, startDayTime+defplan[nStages]+defplan_inter[nStages]))
						startDayTime = startDayTime + defplan[nStages] + defplan_inter[nStages]
					i = i+1
				istCurrentTime = secondsSinceMidnight(datetime.now())
				currentCycleNumber = 0
				for key in plan_data:
					if istCurrentTime > plan_data[key][0][0] and istCurrentTime < plan_data[key][len(plan_data[key])-1][1]:
						currentCycleNumber = key
						break
				cycleRunTimeRequired = 0
				startAdding = 0
				currentStageRunning = 0 #-> first stage/index
				for interval in plan_data[currentCycleNumber]:
					if istCurrentTime >= interval[0] and istCurrentTime < interval[1] and startAdding == 0:
						for checker in range(0,len(plan_data[currentCycleNumber])):
							if interval[0] == plan_data[currentCycleNumber][checker][0]:
								currentStageRunning = checker+1
						startAdding = 1
					if startAdding == 1:
						cycleRunTimeRequired = min((interval[1]-interval[0]), interval[1]-istCurrentTime)
				if cycleRunTimeRequired > 60:
					cur.close()
					db.close()
					sys.exit(0)
				else:
					#print("currs "+str(currentStageRunning)+"\n")
					stmt  = ""
					stmt1 = ""
					stmt2 = ""
					pinIndex = currentStageRunning

					numStages = len(stageOrderHex)#format(len(stageOrderHex),'02x').upper()

					if pinIndex == len(defplan): # pinIndex==len(defplan): -> last stage/index
						pinIndex = 0 #-> first stage/index
						currentCycleNumber = currentCycleNumber + 1
					# currentReplyPin = plan_ug405_reply_pin[pinIndex]
					# currentPin = plan_ug405_pin[pinIndex]

					# stageInHex = ''.join([format((int(pinIndex)+1),'02x').upper()])
					# Fn = ''.join(['0' for k in range(0,16 - len(stageInHex))]) + stageInHex

					totalStageTimeList = [x for x, y in zip(defplan, defplan_inter)]
					timingsInHex = ''.join([format(x,'02x').upper() for x in totalStageTimeList])

					# stageInHex = ''.join([format((int(pinIndex)+1),'02x').upper()])
					stageInHex = (format(constantStageOrder,'02x').upper()) + ''.join([format((int(stageNumber[pinIndex])),'02x').upper()])

					# Fn = ''.join(['0' for k in range(0,len(timingsInHex) - len(stageInHex))]) + stageInHex
					Fn = timingsInHex + ''.join(['0' for k in range(0,16 - (len(timingsInHex)+len(stageInHex)))]) + stageInHex

					SFn = str(format(int(CriticalStage),'02x').upper()) + str(numStages) + str(is_va_active) #str(format(int(is_va_active),'02x').upper())
					SFn += ''.join(stageOrderHex)
					SFn += ''.join(['0' for k in range(0,16 - (len(SFn)))])

					stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`, `utcControlSFn`, utcControlTO, utcControlLO, utcControlFF)"
					# stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(currentPin)+"`, `"+str(currentReplyPin)+"`"
					# for key in pinsarray:
					# 	if key != str(currentReplyPin):
					# 		stmt += ", `"+str(key)+"`"
					stmt1 = stmt + " VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][pinIndex][0])+2)+",'"+Fn+"','"+SFn+"', 1, 0, 0)"
					# stmt2 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][pinIndex][0])+4)+","+psb+","+psb+",0,0,0,0)"
					#print("s1 "+stmt1 + " " + str(datetime.now())+" \n")
					#print("s2 "+stmt2 + " \n\n")
					cur.execute(stmt1)
					db.commit()
					# cur.execute(stmt2)
					# db.commit()
					cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
					db.commit()
					# cur.execute(stmt2.replace("utcControlTable","utcControlTable_dummy"))
					# db.commit()
					print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
					print("[INFO] ", end='')
					print("[ATCS] ", end='')
					print("[Control] ", end='')
					print("[utcControlFn "+Fn[len(Fn)-1]+"] ", end='')
					print("["+str(site_id)+"] ", end='')
					print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(plan_data[currentCycleNumber][pinIndex][0]))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')

					# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
					# print("[INFO] ", end='')
					# print("[ATCS] ", end='')
					# print("[Control] ", end='')
					# print("["+str(currentReplyPin)+" "+str(psb)+"] ", end='')
					# print("["+str(site_id)+"] ", end='')
					# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(plan_data[currentCycleNumber][pinIndex][0]+1))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
					sleepInterval = 0
					if pinIndex == len(defplan)-1: # pinIndex==len(defplan)-1
						pinIndex = -1
						currentCycleNumber = currentCycleNumber + 1

					numStages = len(stageOrderHex) #format(len(stageOrderHex),'02x').upper()

					for stagePin in range(pinIndex+1,len(defplan)): #indexes

						if stagePin == (len(defplan) - 1):
							sleepInterval = plan_data[currentCycleNumber][stagePin][1] - secondsSinceMidnight(datetime.now())

						# currentReplyPin = plan_ug405_reply_pin[stagePin]
						# currentPin = plan_ug405_pin[stagePin]
						stmt  = ""
						stmt1 = ""
						stmt2 = ""

						# stageInHex = ''.join([format((int(stagePin)+1),'02x').upper()])
						# Fn = ''.join(['0' for k in range(0,16 - len(stageInHex))]) + stageInHex

						totalStageTimeList = [x for x, y in zip(defplan, defplan_inter)]
						timingsInHex = ''.join([format(x,'02x').upper() for x in totalStageTimeList])

						stageInHex = (format(constantStageOrder,'02x').upper()) + ''.join([format((int(stageNumber[stagePin])),'02x').upper()])
						# Fn = ''.join(['0' for k in range(0,len(timingsInHex) - len(stageInHex))]) + stageInHex
						Fn = timingsInHex + ''.join(['0' for k in range(0,16 - (len(timingsInHex)+len(stageInHex)))]) + stageInHex

						SFn = str(format(int(CriticalStage),'02x').upper()) + str(numStages) + str(is_va_active) #str(format(int(is_va_active),'02x').upper())
						SFn += ''.join(stageOrderHex)
						SFn += ''.join(['0' for k in range(0,16 - (len(SFn)))])
						stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`, `utcControlSFn`, utcControlTO, utcControlLO, utcControlFF)"

						# stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(currentPin)+"`, `"+str(currentReplyPin)+"`"
						# for key in pinsarray:
						# 	if key != str(currentReplyPin):
						# 		stmt += ", `"+str(key)+"`"
						stmt1 = stmt + " VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][stagePin][0])+2)+",'"+Fn+"','"+SFn+"', 1, 0, 0)"
						# stmt2 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][stagePin][0])+4)+","+psb+","+psb+",0,0,0,0)"
						cur.execute(stmt1)
						db.commit()
						# cur.execute(stmt2)
						# db.commit()
						cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
						db.commit()
						# cur.execute(stmt2.replace("utcControlTable","utcControlTable_dummy"))
						# db.commit()
						print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
						print("[INFO] ", end='')
						print("[ATCS] ", end='')
						print("[Control] ", end='')
						print("[utcControlFn "+Fn[len(Fn)-1]+"] ", end='')
						print("["+str(site_id)+"] ", end='')
						print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(plan_data[currentCycleNumber][stagePin][0]))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')

						# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
						# print("[INFO] ", end='')
						# print("[ATCS] ", end='')
						# print("[Control] ", end='')
						# print("["+str(currentReplyPin)+" "+str(psb)+"] ", end='')
						# print("["+str(site_id)+"] ", end='')
						# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(plan_data[currentCycleNumber][stagePin][0]+1))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')

					if currentStageRunning == 1:
						currentCycleNumber = currentCycleNumber + 1
						# currentReplyPin = plan_ug405_reply_pin[0]
						# currentPin = plan_ug405_pin[0]
						stmt  = ""
						stmt1 = ""
						stmt2 = ""

						# stageInHex = ''.join([format((0+1),'02x').upper()])
						# Fn = ''.join(['0' for k in range(0,16 - len(stageInHex))]) + stageInHex
						
						totalStageTimeList = [x for x, y in zip(defplan, defplan_inter)]
						timingsInHex = ''.join([format(x,'02x').upper() for x in totalStageTimeList])

						stageInHex = (format(constantStageOrder,'02x').upper()) + ''.join([format((stageNumber[0]),'02x').upper()])
						# Fn = ''.join(['0' for k in range(0,len(timingsInHex) - len(stageInHex))]) + stageInHex
						Fn = timingsInHex + ''.join(['0' for k in range(0,16 - (len(timingsInHex)+len(stageInHex)))]) + stageInHex

						SFn = str(format(int(CriticalStage),'02x').upper()) + str(numStages) + str(is_va_active) #str(format(int(is_va_active),'02x').upper())
						SFn += ''.join(stageOrderHex)
						SFn += ''.join(['0' for k in range(0,16 - (len(SFn)))])

						stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`, `utcControlSFn`, utcControlTO, utcControlLO, utcControlFF)"

						# stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(currentPin)+"`, `"+str(currentReplyPin)+"`"
						# for key in pinsarray:
						# 	if key != str(currentReplyPin):
						# 		stmt += ", `"+str(key)+"`"
						stmt1 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][0][0])+2)+","+Fn+",'"+SFn+"', 1, 0, 0)"
						# stmt2 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][0][0])+4)+","+psb+","+psb+",0,0,0,0)"
						#print("if21 "+stmt1 + " " + str(datetime.now()) + " \n")
						#print("if22 "+stmt2 + " \n\n")
						cur.execute(stmt1)
						db.commit()
						# cur.execute(stmt2)
						# db.commit()
						cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
						db.commit()
						# cur.execute(stmt2.replace("utcControlTable","utcControlTable_dummy"))
						# db.commit()		
						print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
						print("[INFO] ", end='')
						print("[ATCS] ", end='')
						print("[Control] ", end='')
						print("[utcControlFn "+Fn[len(Fn)-1]+"] ", end='')
						print("["+str(site_id)+"] ", end='')
						print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(plan_data[currentCycleNumber][0][0]))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
						
						# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
						# print("[INFO] ", end='')
						# print("[ATCS] ", end='')
						# print("[Control] ", end='')
						# print("["+str(currentReplyPin)+" "+str(psb)+"] ", end='')
						# print("["+str(site_id)+"] ", end='')
						# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(plan_data[currentCycleNumber][0][0]+1))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')	
					cur.close()
					db.close()
					
			cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 1, 0, 0, '0000000000000002') ")
			db.commit()
			cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimeStamp, utcControlFF, utcControlTO, utcControlLO, utcControlFn) VALUES ('"+str(site_id)+"', 1, 1, 0, 0, '0000000000000002') ")
			db.commit()
			cur.execute("UPDATE `utmc_traffic_signal_static` SET `runPlanClicked`='"+datetime.now().strftime("%Y-%m-%d")+" 06:59:56', currentMode='8', `is_active`=0 WHERE SignalSCN='"+signal_scn+"'")
			db.commit()
			cur.execute("INSERT INTO tis_signal_mode_change_log (SignalSCN, user, previousMode, previousModeId, newMode, newModeId, changeReason) VALUES ('"+str(signal_scn)+"', 'admin', '"+newMode+"', '"+str(currentModeId)+"', 'flash','8', 'Switching to Flash Mode at End Of Day')")
			db.commit()
			cur.close()
			sendSocketMessage(site_id,"Flash,"+signal_scn+"pass")
			db.close()
			sys.exit(0)

		# print(str(secondsSinceMidnight(runPlanClicked))+ " "+str(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time)) )
		if secondsSinceMidnight(runPlanClicked) > secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time):
			if currentPlanId == oldPlanId:
				start_time = secondsSinceMidnightISTTosecondsSinceMidnightUTC(secondsSinceMidnight(runPlanClicked))
			# else:
			# 	start_time = secondsSinceMidnightISTTosecondsSinceMidnightUTC(secondsSinceMidnight(runPlanClicked))

		# print(runPlanClicked)
		# print(start_time, end=" startime\n")
		# print(end_time, end=" endtime\n")
		# print(CycleTime, end=" cycletime\n")

		timings_to_insert = []
		stages_at_insert = []
		planStartedTime = secondsSinceMidnight(runPlanClicked)
		
		while(planStartedTime > 0):
			planStartedTime = planStartedTime - (CycleTime)
		endPlanTime = 86400
		looperTime = planStartedTime
		# print(str(looperTime)+" loopertime\n", end='')
		looper = 0
		if end_time == 10:
			end_time = 86410
		# print(str(start_time))
		# print(str(end_time))
		startIST = secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time)
		endIST = secondsSinceMidnightUTCTosecondsSinceMidnightIST(end_time)
		print("++"+str(startIST)+" "+str(endIST)+"++\n")

		# stagesInHex = ''.join([format(k,'02x').upper() for k in stagetimings])
		# Fn = stagesInHex + ''.join(['0' for k in range(0,16 - len(stagesInHex))])

		numStages = len(stageSeq.split(','))#format(len(stageSeq.split(',')),'02x').upper()
		stageOrderHex = [format(int(n),'02x').upper() for n in stageSeq.split(',')]

		if endIST == 10:
			endIST = 86410
		while(True):
			if looperTime < endIST and looperTime >= startIST:
				timings_to_insert.append(secondsSinceMidnightISTTosecondsSinceMidnightUTC(looperTime))
				stages_at_insert.append(stageNumber[looper] - 1)
			looperTime = looperTime + stagetimings[looper] + interstagetimings[looper]
			looper = looper + 1 
			looper = 0 if looper == len(stagetimings) else looper
			if looperTime > endPlanTime:
				break

		print(stages_at_insert,end="\n")
		for value in range(0, len(timings_to_insert)):			
			if timings_to_insert[value] + 2 > 86400:
				timings_to_insert[value] = timings_to_insert[value] - 2
			if timings_to_insert[value] <= 10 and timings_to_insert[value] >= 0:
				time.sleep(60)
			
			# stageInHex = ''.join([format((int(stages_at_insert[value])+1),'02x').upper()])
			# Fn = ''.join(['0' for k in range(0,16 - len(stageInHex))]) + stageInHex
			
			totalStageTimeList = [x for x, y in zip(stagetimings, interstagetimings)]
			timingsInHex = ''.join([format(x,'02x').upper() for x in totalStageTimeList])

			stageInHex = (format(constantStageOrder,'02x').upper()) + ''.join([format((int(stages_at_insert[value])+1),'02x').upper()])
			# Fn = ''.join(['0' for k in range(0,len(timingsInHex) - len(stageInHex))]) + stageInHex
			Fn = timingsInHex + ''.join(['0' for k in range(0,16 - (len(timingsInHex)+len(stageInHex)))]) + stageInHex

			SFn = str(format(int(CriticalStage),'02x').upper()) + str(numStages) + str(is_va_active) #str(format(int(is_va_active),'02x').upper())
			SFn += ''.join(stageOrderHex)
			SFn += ''.join(['0' for k in range(0,16 - (len(SFn)))])
			
			pv = '1' if (len(group_site_ids) != 0 and str(CriticalStage) == str(int(stages_at_insert[value])+1) and CriticalSignalSCN == signal_scn) else '0'
			stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlFn`, `utcControlSFn`, utcControlTO, utcControlLO, utcControlFF, utcControlPV)"
			# stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(ug405_pin[int(stages_at_insert[value])])+"`, `"+str(ug405_reply_pin[int(stages_at_insert[value])])+"`"
			# for key in pinsarray:
			# 	if key != str(ug405_reply_pin[stages_at_insert[value]]):
			# 		stmt += ", `"+str(key)+"`"

			stmt1 = stmt + " VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+",'"+Fn+"','"+SFn+"', 1, 0, 0, "+pv+");"
			#stmt1 = stmt + " VALUES ("+str(site_id)+",1,'"+Fn+"','"+SFn+"', 1, 0, 0, "+pv+");"

			# stmt1 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+","+fb+","+fb+",0,0,0,0,1);"
			
			#print(stmt1, end='\n')
			print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
			print("[INFO] ", end='')
			print("[ATCS] ", end='')
			print("[Control] ", end='')
			print("[utcControlFn "+Fn[len(Fn)-1]+"] ", end='')
			print("["+str(site_id)+"] ", end='')
			print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(timings_to_insert[value]))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
			cur.execute(stmt1)
			db.commit()
			cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
			db.commit()

			if len(group_site_ids) != 0 and str(CriticalStage) == str(int(stages_at_insert[value])+1):
				# print(group_site_ids)
				for site in group_site_ids:
					# print(site)
					sid = str(site[0])
					offset = int(site[1])

					offset_exectime = str(timings_to_insert[value] + 2 + offset)
					offset_exectime_off = str(timings_to_insert[value] + 2 + offset + 1)

					cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimestamp, utcControlPV) VALUES ('"+sid+"', '"+offset_exectime+"', 1)")
					db.commit()
					cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimestamp, utcControlPV) VALUES ('"+sid+"', '"+offset_exectime+"', 1)")
					db.commit()

					print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
					print("[INFO] ", end='')
					print("[ATCS] ", end='')
					print("[Control] ", end='')
					print("[utcControlPV 1] ", end='')
					print("["+str(sid)+"] ", end='')
					print(offset_exectime, end='')
					#print((secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(offset_exectime))).strftime("%Y-%m-%d %H:%M:%S"), end='')
					print("\n")

					cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimestamp, utcControlPV) VALUES ('"+sid+"', '"+offset_exectime_off+"', 0)")
					db.commit()
					cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimestamp, utcControlPV) VALUES ('"+sid+"', '"+offset_exectime_off+"', 0)")
					db.commit()

					print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
					print("[INFO] ", end='')
					print("[ATCS] ", end='')
					print("[Control] ", end='')
					print("[utcControlPV 0] ", end='')
					print("["+str(sid)+"] ", end='')
					#print((secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(offset_exectime_off))).strftime("%Y-%m-%d %H:%M:%S"), end='')
					print("\n")

				offset_exectime = str(timings_to_insert[value] + 2)
				offset_exectime_off = str(timings_to_insert[value] + 2 + 1)

				cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimestamp, utcControlPV) VALUES ('"+str(site_id)+"', '"+offset_exectime+"', 1)")
				db.commit()
				cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimestamp, utcControlPV) VALUES ('"+str(site_id)+"', '"+offset_exectime+"', 1)")
				db.commit()

				print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
				print("[INFO] ", end='')
				print("[ATCS] ", end='')
				print("[Control] ", end='')
				print("[utcControlPV 1] ", end='')
				print("["+str(str(site_id))+"] ", end='')
				#print((secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(offset_exectime))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
				print(offset_exectime)
				print("\n")

				cur.execute("INSERT INTO tis.utcControlTable (site_id, utcControlTimestamp, utcControlPV) VALUES ('"+str(site_id)+"', '"+offset_exectime_off+"', 0)")
				db.commit()
				cur.execute("INSERT INTO tis.utcControlTable_dummy (site_id, utcControlTimestamp, utcControlPV) VALUES ('"+str(site_id)+"', '"+offset_exectime_off+"', 0)")
				db.commit()

				print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
				print("[INFO] ", end='')
				print("[ATCS] ", end='')
				print("[Control] ", end='')
				print("[utcControlPV 0] ", end='')
				print("["+str(str(site_id))+"] ", end='')
				#print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(offset_exectime_off))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
				print(offset_exectime_off)
				print("\n")
		time.sleep(1)
		# os.system("python /home/itspe/Desktop/heurflo/controlSUMOUG405/getDataFromControlTable.py &")
else:
	print("else active")
	print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n", end='')
	sendSocketMessage(site_id,"TimOffline,"+signal_scn+"pass")

	cur.execute("UPDATE `utmc_traffic_signal_static` SET `is_active`='0' WHERE `SignalSCN`='"+signal_scn+"'")
	db.commit()
	cur.execute("SELECT online, LastUpdated FROM `tis_traffic_signal_fault` WHERE `SystemCodeNumber`='"+signal_scn+"' ORDER BY `LastUpdated` DESC LIMIT 1")
	data = cur.fetchone()
	
	if data[0] != 0:
		try:
			cur.execute("INSERT INTO `tis_traffic_signal_fault` VALUES('"+signal_scn+"',now(),0, UNIX_TIMESTAMP(now()) - UNIX_TIMESTAMP('"+str(data[1])+"'))")
			db.commit()
		except Exception as e:
			cur.execute("INSERT INTO `tis_traffic_signal_fault` VALUES('"+signal_scn+"',now(),0, 0)")
			db.commit()
			print(e)

		FaultID = 1

		cur.execute("SELECT id,FaultID from `utmc_device_fault` ORDER BY CreationDate DESC LIMIT 1")
		res = cur.fetchone()
		try:
			FaultID = int(res[0]) #int((res[0])[1:]) + 1
		except Exception as e:
			print(e)
		appendString = '0'

		if FaultID > 0:
			appendString = '0000000'
			if FaultID > 9:
				appendString = '000000'
				if FaultID > 99:
					appendString = '00000'
					if FaultID > 999:
						appendString = '0000'
						if FaultID > 9999:
							appendString = '000'
							if FaultID > 99999:
								appendString = '00'
								if FaultID > 999999:
									appendString = '0'
									if FaultID > 9999999:
										appendString = ''

		FaultID = 'F' + appendString + str(FaultID)

		cur.execute("SELECT count(*) FROM utmc_device_fault INNER JOIN utmc_freeflow_alert_dynamic ON utmc_freeflow_alert_dynamic.SystemCodeNumber = utmc_device_fault.FaultID WHERE utmc_freeflow_alert_dynamic.ActionStatus = 'Open' AND utmc_device_fault.SystemCodeNumber='"+signal_scn+"' AND FaultType='5' AND CommunicationsFault='Y'")
		res = cur.fetchone()

		if res[0] < 1:
			cur.execute("INSERT INTO `utmc_device_fault`(`FaultID`, DeviceType, `SystemCodeNumber`, `FaultType`, `SubSystemTypeID`, `DataSource_TypeID`, `CreationDate`, `EquipmentFault`, `CommunicationsFault`, `Description`) VALUES('"+FaultID+"', 9, '"+signal_scn+"', 5, 1, 1, NOW(), 'N', 'Y', 'Connection Lost with Junction: "+str(signalName)+"')")
			db.commit()
			cur.execute("INSERT INTO `utmc_freeflow_alert_dynamic`(`SystemCodeNumber`,ObjectReferenceType_ID) VALUES('"+FaultID+"',9)")
			db.commit()
			sendSocketMessage("JunctionAlerts","TimOffline,"+signal_scn+"pass")

			emails = ['mohammed.ahmed@itspe.co.in','naman.gupta@itspe.co.in']
			subject = "Junction Offline"
			content = "Junction "+signalName+" has gone offline.Please get it checked."

			#mailer(to=emails,subject=subject,content=content)

	cur.close()
	db.close()
	sys.exit(0)

cur.close()
db.close()
