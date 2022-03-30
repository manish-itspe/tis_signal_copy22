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


if len(sys.argv) != 8:
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
		datetime.strptime(sys.argv[2], '%H:%M:%S')
	except ValueError:
		print("Please Enter Valid Start Time")
		sys.exit(0)
	try:
		datetime.strptime(sys.argv[3], '%H:%M:%S')
	except ValueError:
		print("Please Enter Valid End Time")
		sys.exit(0)
	try:
		int(sys.argv[7])
	except ValueError:
		print("Please Enter Valid Current Stage")
		sys.exit(0)

signal_id = sys.argv[4]
forcebit = sys.argv[5]
currentstage = int(sys.argv[7])
currentstage = 0 if currentstage == len(values) else (currentstage)
# interstage = sys.argv[6]

fb = ''
sb = ''

if forcebit == '0':
	fb = '0'
	sb = '1'
else:
	fb = '1'
	sb = '0'

db = MySQLdb.connect(host="localhost",user="root",passwd="itspe",db="htms")
c_time = datetime.utcnow()
timings = [int(n) for n in sys.argv[1].split(",")]
reverseStageTimings = map(int,(sys.argv[1].split(","))[::-1])
totalStageTime = sum(reverseStageTimings)

interstagetimings = [int(n) for n in sys.argv[6].split(",")]
reverseInterStageTimings = map(int,(sys.argv[6].split(","))[::-1])
totalInterStageTime = sum(reverseInterStageTimings)

cur = db.cursor()
cur.execute("SELECT count(*) as count, group_concat(`ug405_pin`), group_concat(`ug405_reply_pin`) FROM `utmc_traffic_signal_stages` WHERE `SignalID`= '"+signal_id+"' GROUP BY `SignalID` ORDER BY `StageOrder` ASC")
ug405_pin = ''
try:
	stage_info = cur.fetchone()
	count = stage_info[0]
	ug405_pin = [str(n) for n in stage_info[1].split(",")]
	ug405_reply_pin = [str(n) for n in stage_info[2].split(",")]
	cur.close()
	if len(timings) != count:
		print("Signal Stages Configuration error")
		sys.exit(0)
except Exception as e:
	print(e)
	print("Invalid Signal Stages Configuration")
	sys.exit(0)

print("-----"+str(signal_id)+"-\n")
print(sys.argv[2])
print(sys.argv[3])
print("---\n")
start_time = secondsSinceMidnight(datetime.strptime(sys.argv[2], '%H:%M:%S'))
end_time = secondsSinceMidnight(datetime.strptime(sys.argv[3], '%H:%M:%S'))
#interval_start_time = secondsSinceMidnight(datetime.strptime(sys.argv[8], '%H:%M:%S'))
limit_time = (end_time - start_time)
cur = db.cursor()

i = currentstage
# start_time = start_time + timings[i]
# i = i + 1

#1,2,1,2,3,3,3    
cur.execute("SELECT previousMode FROM `tis_signal_mode_change_log` WHERE `signalId`='"+signal_id+"' ORDER BY timestamp DESC LIMIT 1")
signalmodedata = cur.fetchone()
oldMode = signalmodedata[0]
# #print("oldmode" + str(oldMode))
pinsarray=["utcControlGO","utcControlFF","utcControlFM","utcControlCP","utcControlEP"]
site_id = ''
cur.execute("SELECT IPAddress,site_id,SCN,runPlanClicked, oldPlanId, currentPlan,is_va_active,is_hflo_active,is_atcs_active,currentMode FROM `utmc_traffic_signal_static` WHERE `SignalID`='"+signal_id+"'")
signaldata = cur.fetchone()
hostname = signaldata[0]
signalscn = signaldata[2]
runPlanClicked = signaldata[3]
oldPlanId = signaldata[4]
newPlanId = signaldata[5]
is_va_active = signaldata[6]
is_hflo_active = signaldata[7]
is_atcs_active = signaldata[8]
cMode = signaldata[9]

va = 1
if is_va_active == 1 or is_hflo_active == 1 or is_atcs_active == 1 or cMode == "flash":
	va = 0

response = os.system("ping -c 1 " + hostname)
try:
	site_id = signaldata[1]
except Exception as e:
	print("Invalid Signal SCN")
	sys.exit(0)
if response == 0:
	cur.execute("SELECT * FROM `tis_traffic_signal_fault` WHERE `SystemCodeNumber`='"+signalscn+"' ORDER BY `LastUpdated` DESC LIMIT 1")
	data = cur.fetchone()
	if data[2] != 1:
		cur.execute("INSERT INTO `tis_traffic_signal_fault` VALUES('"+signalscn+"','"+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"',1, UNIX_TIMESTAMP(now()) - UNIX_TIMESTAMP('"+str(data[1])+"'))")
		db.commit()
	cur.execute("SELECT group_concat(`signal_timings`.`StageTime` ORDER BY StageNumber separator ',') as StageTime,`utmc_traffic_signal_static`.`is_active`,group_concat(`signal_timings`.`InterStageTime` ORDER BY StageNumber separator ',') as InterStageTime,group_concat(`utmc_traffic_signal_stages`.`ug405_reply_pin` ORDER BY StageNumber separator ',') as ug405_reply_pin,group_concat(`utmc_traffic_signal_stages`.`ug405_pin` ORDER BY StageNumber separator ',') as ug405_pin,`utmc_traffic_signal_static`.`ForceBidNextStagePin`,`utmc_traffic_signal_static`.`currentMode`,`plans`.`PlanSCN`,`plans`.`CycleTime`,utmc_traffic_signal_static.`currentPlan`,utmc_traffic_signal_static.`defaultPlan` FROM `utmc_traffic_signal_static` INNER JOIN `plans` ON `plans`.`ID`=`utmc_traffic_signal_static`.`currentPlan` INNER JOIN `signal_timings` ON `signal_timings`.`SignalID`='"+signal_id+"' AND `signal_timings`.`Plan_SCN`=`plans`.`PlanSCN` INNER JOIN `utmc_traffic_signal_stages` ON `utmc_traffic_signal_stages`.`SignalID` = `utmc_traffic_signal_static`.`SignalID` AND `utmc_traffic_signal_stages`.`SignalID`='"+signal_id+"' AND `utmc_traffic_signal_stages`.`StageOrder`=`signal_timings`.`StageNumber` WHERE `utmc_traffic_signal_static`.`SignalID`='"+signal_id+"'")
	planresult = cur.fetchone()
	defaultPlanId = planresult[10]
	currentPlanId = planresult[9]
	defplan = map(int,planresult[0].split(","))
	is_active = planresult[1]
	defplan_inter = map(int,planresult[2].split(","))
	plan_ug405_reply_pin = planresult[3].split(",")
	plan_ug405_pin = planresult[4].split(",")
	planforcebit = planresult[5]
	currentMode = planresult[6]
	planscn = planresult[7]
	pfb = ''
	psb = ''
	if planforcebit == 1:
		pfb = '1'
		psb = '0'
	else:
		pfb = '0'
		psb = '1'
	if is_active == 0:
		# #print(str(planresult)+"\n")
		startDayTime = 23394
		endDayTime = 84600
		#value 25196, 84600
		if secondsSinceMidnight(datetime.now()) < startDayTime + 300 or secondsSinceMidnight(datetime.now()) > endDayTime:
			#change it to auto mode
			if currentMode == "manual":
				cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentMode`='manualplan',currentPlan='"+str(defaultPlanId)+"', oldPlanId='"+str(defaultPlanId)+"' WHERE SignalID='"+signal_id+"'")
				db.commit()
				cur.execute("INSERT INTO tis_signal_mode_change_log (signalId,user,previousMode,newMode) VALUES ('"+str(signal_id)+"','admin','manual','manualplan')")
				db.commit()
				cur.execute("INSERT INTO tis_signal_mode_change_log (signalId,user,previousMode,newMode, `timestamp`) VALUES ('"+str(signal_id)+"','admin','manualplan','manualplan', NOW() + INTERVAL 1 SECOND)")
				db.commit()	
			cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentStageOrder`='0',lastStageChanged='"+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"', `is_active`=0 WHERE SignalID='"+signal_id+"'")
			db.commit()
			sendSocketMessage("Flash,"+signal_id+"pass")
			db.close()
			sys.exit(0)
		plan_data = {}
		i = 0
		cur.execute("SELECT group_concat(`signal_timings`.`StageTime` ORDER BY StageNumber separator ',') as StageTime,`utmc_traffic_signal_static`.`is_active`,group_concat(`signal_timings`.`InterStageTime` ORDER BY StageNumber separator ',') as InterStageTime,group_concat(`utmc_traffic_signal_stages`.`ug405_reply_pin` ORDER BY StageNumber separator ',') as ug405_reply_pin,group_concat(`utmc_traffic_signal_stages`.`ug405_pin` ORDER BY StageNumber separator ',') as ug405_pin,`utmc_traffic_signal_static`.`ForceBidNextStagePin`,`utmc_traffic_signal_static`.`currentMode`,`plans`.`PlanSCN`,`plans`.`CycleTime`,utmc_traffic_signal_static.`currentPlan`,utmc_traffic_signal_static.`defaultPlan` FROM `utmc_traffic_signal_static` INNER JOIN `plans` ON `plans`.`ID`=`utmc_traffic_signal_static`.`defaultPlan` INNER JOIN `signal_timings` ON `signal_timings`.`SignalID`='"+signal_id+"' AND `signal_timings`.`Plan_SCN`=`plans`.`PlanSCN` INNER JOIN `utmc_traffic_signal_stages` ON `utmc_traffic_signal_stages`.`SignalID` = `utmc_traffic_signal_static`.`SignalID` AND `utmc_traffic_signal_stages`.`SignalID`='"+signal_id+"' AND `utmc_traffic_signal_stages`.`StageOrder`=`signal_timings`.`StageNumber` WHERE `utmc_traffic_signal_static`.`SignalID`='"+signal_id+"'")
		planresult_offline = cur.fetchone()
		defplan_offline = map(int,planresult_offline[0].split(","))
		nStages_offline = len(defplan_offline)
		defplan_inter_offline = map(int,planresult_offline[2].split(","))
		while(startDayTime < endDayTime):
			plan_data[i] = []
			for nStages_offline in range(0, len(defplan_offline)):
				plan_data[i].append((startDayTime, startDayTime+defplan_offline[nStages_offline]+defplan_inter_offline[nStages_offline]))
				startDayTime = startDayTime + defplan_offline[nStages_offline] + defplan_inter_offline[nStages_offline]
			i = i+1
		istCurrentTime = secondsSinceMidnight(datetime.now())
		currentCycleNumber = 0
		for key in plan_data:
			if istCurrentTime >= plan_data[key][0][0] and istCurrentTime < plan_data[key][len(plan_data[key])-1][1]:
				currentCycleNumber = key
				break
		cycleRunTimeRequired = 0
		startAdding = 0
		# #print("plan "+str(istCurrentTime)+"\n")
		# ##print(str(plan_data[key]))
		# ##print("\nplan\n")
		currentStageRunning = 0
		for interval in plan_data[currentCycleNumber]:
			if istCurrentTime > interval[0] and istCurrentTime < interval[1] and startAdding == 0:
				for checker in range(0,len(plan_data[currentCycleNumber])):
					if interval[0] == plan_data[currentCycleNumber][checker][0]:
						currentStageRunning = checker+1
				startAdding = 1
			if startAdding == 1:
				cycleRunTimeRequired = min((interval[1]-interval[0]), interval[1]-istCurrentTime)
				break
		endTimeFixedMode = plan_data[currentCycleNumber][len(plan_data[currentCycleNumber])-1][1]
		cycleRunTimeRequired = endTimeFixedMode - istCurrentTime
		if cycleRunTimeRequired > 60:
			sys.exit(0)
		else:
			#print("offcurr "+str(currentStageRunning)+"\n")
			#print(str(istCurrentTime) + " " + str(plan_data[currentCycleNumber]))
			endTimeFixedMode = plan_data[currentCycleNumber][len(plan_data[currentCycleNumber])-1][1]
			#print(" "+str(endTimeFixedMode - istCurrentTime)+" ")
			istCurrentTime = secondsSinceMidnight(datetime.now())
			time.sleep(endTimeFixedMode - istCurrentTime)
			#update the runPlanClicked with endTimeFixedMode, is_active to 1
			cur.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,1)")
			db.commit()
			print("runPlanClicked ---"+secondsSinceMidnightToIST(endTimeFixedMode).strftime("%Y-%m-%d %H:%M:%S") + " ----- endTimeFixedMode" + str(endTimeFixedMode) + " ---- istCurrentTime" + str(istCurrentTime))
			cur.execute("UPDATE `utmc_traffic_signal_static` SET `runPlanClicked`='"+secondsSinceMidnightToIST(endTimeFixedMode).strftime("%Y-%m-%d %H:%M:%S")+"',`oldPlanClicked`='"+secondsSinceMidnightToIST(endTimeFixedMode).strftime("%Y-%m-%d %H:%M:%S")+"', `is_active`='1',oldPlanId='"+str(currentPlanId)+"',currentPlan='"+str(currentPlanId)+"',currentMode='manualplan',`currentStageOrder`=1 WHERE SignalID='"+signal_id+"'")
			# print(UPDATE `utmc_traffic_signal_static` SET `runPlanClicked`='"+secondsSinceMidnightToIST(endTimeFixedMode).strftime("%Y-%m-%d %H:%M:%S")+"',`oldPlanClicked`='"+secondsSinceMidnightToIST(endTimeFixedMode).strftime("%Y-%m-%d %H:%M:%S")+"', `is_active`='1',oldPlanId='"+str(currentPlanId)+"',currentPlan='"+str(currentPlanId)+"' WHERE SignalID='"+signal_id+"')
			db.commit()
			cur.execute("INSERT INTO tis_signal_mode_change_log (signalId,user,previousMode,newMode) VALUES ('"+str(signal_id)+"','admin','manual','manualplan')")
			db.commit()
			cur.execute("INSERT INTO tis_signal_mode_change_log (signalId,user,previousMode,newMode,`timestamp`) VALUES ('"+str(signal_id)+"','admin','manualplan','manualplan', NOW()+INTERVAL 1 SECOND)")
			db.commit()
			cur.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,1)")
			db.commit()
			sendSocketMessage("TimOnline,"+signal_id+"pass")
			print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
			print("[INFO] ", end='')
			print("[ATCS] ", end='')
			print("[Control] ", end='')
			print("["+"utcControlHI 1] ", end='')
			print("["+str(site_id)+"] ", end='')
			print("[utcControlTimestamp: "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')

			#from endTimeFixedMode to ceil function time we have run the code in manual block
			# print("Updated Data :" + str(endTimeFixedMode))
			start_time = endTimeFixedMode
			end_time = secondsSinceMidnight(datetime.now().replace(second=0, microsecond=0)) + 70
			#print("startend "+str(start_time)+ " "+str(end_time)+"\n")

			# stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(ug405_pin[0])+"`, `"+str(ug405_reply_pin[0])+"`"
			# for key in pinsarray:
			# 	if key != str(ug405_reply_pin[0]):
			# 		stmt += ", `"+str(key)+"`"
			# stmt1 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+",1,"+fb+","+fb+",0,0,0,0,1)"
			# stmt2 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+",1,"+sb+","+sb+",0,0,0,0,0)"
			# #print("oneloop "+stmt1+"\n")
			# #print("oneloop "+stmt2+"\n\n")
			# cur.execute(stmt1)
			# db.commit()
			# cur.execute(stmt2)
			# db.commit()
			# sendSocketMessage("Signal Stage Update"+','+signal_id+",1,"+planscn+"pass")
			currentMode = "manualplan"
			if currentMode == "manualplan":
				timings_to_insert = []
				stages_at_insert = []
				planStartedTime = start_time
				endPlanTime = 84600
				looperTime = planStartedTime
				looper = 0
				while(True):
					if looperTime <= end_time and looperTime >= start_time:
						timings_to_insert.append(secondsSinceMidnightISTTosecondsSinceMidnightUTC(looperTime))
						stages_at_insert.append(looper)
					looperTime = looperTime + timings[looper] + interstagetimings[looper]
					looper = looper + 1 
					looper = 0 if looper == len(timings) else looper
					if looperTime > endPlanTime:
						break
				check_first = 0
				for value in range(0, len(timings_to_insert)):
					stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(ug405_pin[int(stages_at_insert[value])])+"`, `"+str(ug405_reply_pin[int(stages_at_insert[value])])+"`"
					for key in pinsarray:
						if key != str(ug405_reply_pin[stages_at_insert[value]]):
							stmt += ", `"+str(key)+"`"
					stmt1 = ""
					if check_first == 0:
						stmt1 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+",1,"+fb+","+fb+",0,0,0,0,1)"
					else:
						stmt1 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+","+fb+","+fb+",0,0,0,0,1)"
					cur.execute(stmt1)
					db.commit()
					cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
					db.commit()
					# if check_first == 0:
					# 	time.sleep(1)
					# 	stmt2 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+",1,"+sb+","+sb+",0,0,0,0,0)"
					# 	check_first = 1
					# else:
					# 	stmt2 = stmt + ",`utcControlMO`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+3)+","+sb+","+sb+",0,0,0,0,0)"
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
					
					# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
					# print("[INFO] ", end='')
					# print("[ATCS] ", end='')
					# print("[Control] ", end='')
					# print("["+str(ug405_reply_pin[stages_at_insert[value]])+" "+str(sb)+"] ", end='')
					# print("["+str(site_id)+"] ", end='')
					# print("[utcControlTimestamp: "+secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(timings_to_insert[value]+1)).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')


					#print("offloop "+stmt1+"\n")
					#print("offloop "+stmt2+"\n\n")
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
				# print("[utcControlTimestamp: "+secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(int(end_time)+10)).strftime("%Y-%m-%d %H:%M:%S")+"]\n")
			cur.close()
			db.close()
	elif currentMode == "scheduled" and is_active == 1:
		print("Came to Scheduled")
		# ##print(str(planresult)+"\n")
		startDayTime = 23394
		endDayTime = 84600
		plan_data = {}
		i = 0
		if secondsSinceMidnight(datetime.now()) < startDayTime or secondsSinceMidnight(datetime.now()) > endDayTime:
			cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentStageOrder`='0',lastStageChanged='' WHERE SignalID='"+signal_id+"'")
			db.commit()
			sendSocketMessage("Flash,"+signal_id+"pass")
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
		currentStageRunning = 0
		for interval in plan_data[currentCycleNumber]:
			if istCurrentTime >= interval[0] and istCurrentTime < interval[1] and startAdding == 0:
				for checker in range(0,len(plan_data[currentCycleNumber])):
					if interval[0] == plan_data[currentCycleNumber][checker][0]:
						currentStageRunning = checker+1
				startAdding = 1
			if startAdding == 1:
				cycleRunTimeRequired = min((interval[1]-interval[0]), interval[1]-istCurrentTime)
		if cycleRunTimeRequired > 60:
			sys.exit(0)
		else:
			##print("currs "+str(currentStageRunning)+"\n")
			stmt  = ""
			stmt1 = ""
			stmt2 = ""
			pinIndex=currentStageRunning
			if pinIndex == len(defplan):
				pinIndex = 0
				currentCycleNumber = currentCycleNumber + 1
			currentReplyPin = plan_ug405_reply_pin[pinIndex]
			currentPin = plan_ug405_pin[pinIndex]
			stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(currentPin)+"`, `"+str(currentReplyPin)+"`"
			for key in pinsarray:
				if key != str(currentReplyPin):
					stmt += ", `"+str(key)+"`"
			stmt1 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][pinIndex][0])+2)+","+pfb+","+pfb+",0,0,0,0)"
			# stmt2 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][pinIndex][0])+4)+","+psb+","+psb+",0,0,0,0)"
			##print("s1 "+stmt1 + " " + str(datetime.now())+" \n")
			##print("s2 "+stmt2 + " \n\n")
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
			print("["+str(currentReplyPin)+" "+str(pfb)+"] ", end='')
			print("["+str(site_id)+"] ", end='')
			print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(plan_data[currentCycleNumber][pinIndex][0])).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
			
			# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
			# print("[INFO] ", end='')
			# print("[ATCS] ", end='')
			# print("[Control] ", end='')
			# print("["+str(currentReplyPin)+" "+str(psb)+"] ", end='')
			# print("["+str(site_id)+"] ", end='')
			# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(plan_data[currentCycleNumber][pinIndex][0]+1)).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')

			sleepInterval = 0
			# ##print("<<"+str(pinIndex)+" "+str(len(defplan))+" "+str(plan_data[currentCycleNumber][pinIndex][1])+">>??")
			if pinIndex == len(defplan)-1:
				pinIndex = -1
				currentCycleNumber = currentCycleNumber + 1
			for stagePin in range(pinIndex+1,len(defplan)):
				# ##print("<<"+str(stagePin)+" "+str(len(defplan))+" "+str(plan_data[currentCycleNumber][stagePin][1])+">>")
				if stagePin == len(defplan)-1:
					# ##print("%%%%"+str(plan_data[currentCycleNumber][stagePin][1])+" "+str(secondsSinceMidnight(datetime.now()))+"%%%%\n")
					sleepInterval = plan_data[currentCycleNumber][stagePin][1] - secondsSinceMidnight(datetime.now())
					# stagePin = 0
				currentReplyPin = plan_ug405_reply_pin[stagePin]
				currentPin = plan_ug405_pin[stagePin]
				stmt  = ""
				stmt1 = ""
				stmt2 = ""
				stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(currentPin)+"`, `"+str(currentReplyPin)+"`"
				for key in pinsarray:
					if key != str(currentReplyPin):
						stmt += ", `"+str(key)+"`"
				stmt1 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][stagePin][0])+2)+","+pfb+","+pfb+",0,0,0,0)"
				# stmt2 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][stagePin][0])+4)+","+psb+","+psb+",0,0,0,0)"
				##print("if1 "+stmt1 + " " + str(datetime.now()) + " \n")
				##print("if2 "+stmt2 + " \n\n")
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
				print("["+str(currentReplyPin)+" "+str(pfb)+"] ", end='')
				print("["+str(site_id)+"] ", end='')
				print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(plan_data[currentCycleNumber][stagePin][0])).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
				
				# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
				# print("[INFO] ", end='')
				# print("[ATCS] ", end='')
				# print("[Control] ", end='')
				# print("["+str(currentReplyPin)+" "+str(psb)+"] ", end='')
				# print("["+str(site_id)+"] ", end='')
				# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(plan_data[currentCycleNumber][stagePin][0]+1)).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')

			if currentStageRunning == 1:
				currentCycleNumber = currentCycleNumber + 1
				currentReplyPin = plan_ug405_reply_pin[0]
				currentPin = plan_ug405_pin[0]
				stmt  = ""
				stmt1 = ""
				stmt2 = ""
				stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(currentPin)+"`, `"+str(currentReplyPin)+"`"
				for key in pinsarray:
					if key != str(currentReplyPin):
						stmt += ", `"+str(key)+"`"
				stmt1 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][0][0])+2)+","+pfb+","+pfb+",0,0,0,0)"
				# stmt2 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][0][0])+4)+","+psb+","+psb+",0,0,0,0)"
				##print("if21 "+stmt1 + " " + str(datetime.now()) + " \n")
				##print("if22 "+stmt2 + " \n\n")
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
				print("["+str(currentReplyPin)+" "+str(pfb)+"] ", end='')
				print("["+str(site_id)+"] ", end='')
				print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(plan_data[currentCycleNumber][0][0])).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
				
				# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
				# print("[INFO] ", end='')
				# print("[ATCS] ", end='')
				# print("[Control] ", end='')
				# print("["+str(currentReplyPin)+" "+str(psb)+"] ", end='')
				# print("["+str(site_id)+"] ", end='')
				# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(plan_data[currentCycleNumber][0][0]+1)).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
			
			cur.close()
			db.close()
			
				#now wait till the cycle is complete in this iteration
				#then take it to manual mode and then set the timings in that interval.
	elif oldMode == "manual" and currentMode=="manualplan" and is_active == 1:
		print("Came to Manual To Manual Plan,Current Signal Running: "+str(i) + "\n", end='')
		cur.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+","+str(start_time)+",1)")
		db.commit()
		cur.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+","+str(start_time)+",1)")
		db.commit()
		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ")
		print("[INFO] ", end='')
		print("[ATCS] ", end='')
		print("[Control] ", end='')
		print("[utcControlHI 1] ", end='')
		print("["+str(site_id)+"] ", end='')
		print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')

		stagesInHex = ''.join([format(i,'02x').upper() for i in timings])
		Fn = stagesInHex + ''.join(['0' for i in range(0,16 - len(stagesInHex))])

		while(True):
			stmt  = ""
			stmt1 = ""
			stmt2 = ""
			if start_time <= end_time:
				stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(ug405_pin[i])+"`, `"+str(ug405_reply_pin[i])+"`"
				for key in pinsarray:
					if key != str(ug405_reply_pin[i]):
						stmt += ", `"+str(key)+"`"
				stmt1 = stmt + ",`utcControlMO`,`utcControlFn`,`utcControlDX`) VALUES ("+str(site_id)+","+str(int(start_time)+2)+","+fb+","+fb+",0,0,0,0,1,'"+Fn+"',"+str(va)+")"
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
				print("["+str(ug405_reply_pin[i])+" "+str(fb)+"] ", end='')
				print("["+str(site_id)+"] ", end='')
				print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
				
				# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
				# print("[INFO] ", end='')
				# print("[ATCS] ", end='')
				# print("[Control] ", end='')
				# print("["+str(ug405_reply_pin[i])+" "+str(sb)+"] ", end='')
				# print("["+str(site_id)+"] ", end='')
				# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time+1))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
				start_time = start_time + timings[i] + interstagetimings[i]
				i = i + 1
				i = 0 if i == len(timings) else i
				db.commit()
			else:
				i = i-1
				i = len(timings)-1 if i < 0 else i
				start_time = start_time - timings[i] - interstagetimings[i]
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
		cur.execute("INSERT INTO tis_signal_mode_change_log (signalId,user,previousMode,newMode) VALUES ('"+str(signal_id)+"','admin','manualplan','manualplan')")
		db.commit()
		cur.close()
		db.close()
	elif currentMode == "manualplan" and is_active == 1:
		print("Came to Manual Plan To Manual Plan")
		print(" start_time: " +str(start_time) + " end_time: "+str(end_time) + "\n", end='')
		CycleTime = totalStageTime + totalInterStageTime
		if secondsSinceMidnight(runPlanClicked) > secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time):
			start_time = secondsSinceMidnightISTTosecondsSinceMidnightUTC(secondsSinceMidnight(runPlanClicked))

		print(str(start_time)+" starttttt\n", end='')
		cur.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,1)")
		db.commit()
		cur.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,1)")
		db.commit()
		print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
		print("[INFO] ", end='')
		print("[ATCS] ", end='')
		print("[Control] ", end='')
		print("[utcControlHI 1] ", end='')
		print("["+str(site_id)+"] ", end='')
		print("[utcControlTimestamp: "+(datetime.now()).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
		# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(start_time))).strftime("%Y-%m-%d %H:%M:%S")+"]\n")
		startDayTime = 23394
		endDayTime = 84600
		if secondsSinceMidnight(datetime.now()) < startDayTime + 300 or secondsSinceMidnight(datetime.now()) > endDayTime:
			cur.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,0)")
			db.commit()
			print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
			print("[INFO] ", end='')
			print("[ATCS] ", end='')
			print("[Control] ", end='')
			print("[utcControlHI 0] ", end='')
			print("["+str(site_id)+"] ", end='')
			print("[utcControlTimestamp: "+(datetime.now()).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
			cur.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,0)")
			db.commit()
			if secondsSinceMidnight(datetime.now()) > startDayTime + 60:
				startDayTime = 23394
				endDayTime = 84600
				plan_data = {}
				i = 0
				if secondsSinceMidnight(datetime.now()) < startDayTime or secondsSinceMidnight(datetime.now()) > endDayTime:
					cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentStageOrder`='0',lastStageChanged=now() WHERE SignalID='"+signal_id+"'")
					db.commit()
					sendSocketMessage("Flash,"+signal_id+"pass")
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
				currentStageRunning = 0
				for interval in plan_data[currentCycleNumber]:
					if istCurrentTime >= interval[0] and istCurrentTime < interval[1] and startAdding == 0:
						for checker in range(0,len(plan_data[currentCycleNumber])):
							if interval[0] == plan_data[currentCycleNumber][checker][0]:
								currentStageRunning = checker+1
						startAdding = 1
					if startAdding == 1:
						cycleRunTimeRequired = min((interval[1]-interval[0]), interval[1]-istCurrentTime)
				if cycleRunTimeRequired > 60:
					sys.exit(0)
				else:
					#print("currs "+str(currentStageRunning)+"\n")
					stmt  = ""
					stmt1 = ""
					stmt2 = ""
					pinIndex=currentStageRunning
					if pinIndex == len(defplan):
						pinIndex = 0
						currentCycleNumber = currentCycleNumber + 1
					currentReplyPin = plan_ug405_reply_pin[pinIndex]
					currentPin = plan_ug405_pin[pinIndex]
					stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(currentPin)+"`, `"+str(currentReplyPin)+"`"
					for key in pinsarray:
						if key != str(currentReplyPin):
							stmt += ", `"+str(key)+"`"
					stmt1 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][pinIndex][0])+2)+","+pfb+","+pfb+",0,0,0,0)"
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
					print("["+str(currentReplyPin)+" "+str(pfb)+"] ", end='')
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
					if pinIndex == len(defplan)-1:
						pinIndex = -1
						currentCycleNumber = currentCycleNumber + 1
					for stagePin in range(pinIndex+1,len(defplan)):
						if stagePin == len(defplan)-1:
							sleepInterval = plan_data[currentCycleNumber][stagePin][1] - secondsSinceMidnight(datetime.now())
						currentReplyPin = plan_ug405_reply_pin[stagePin]
						currentPin = plan_ug405_pin[stagePin]
						stmt  = ""
						stmt1 = ""
						stmt2 = ""
						stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(currentPin)+"`, `"+str(currentReplyPin)+"`"
						for key in pinsarray:
							if key != str(currentReplyPin):
								stmt += ", `"+str(key)+"`"
						stmt1 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][stagePin][0])+2)+","+pfb+","+pfb+",0,0,0,0)"
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
						print("["+str(currentReplyPin)+" "+str(pfb)+"] ", end='')
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
						currentReplyPin = plan_ug405_reply_pin[0]
						currentPin = plan_ug405_pin[0]
						stmt  = ""
						stmt1 = ""
						stmt2 = ""
						stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `"+str(currentPin)+"`, `"+str(currentReplyPin)+"`"
						for key in pinsarray:
							if key != str(currentReplyPin):
								stmt += ", `"+str(key)+"`"
						stmt1 = stmt + ") VALUES ("+str(site_id)+","+str(secondsSinceMidnightISTTosecondsSinceMidnightUTC(plan_data[currentCycleNumber][0][0])+2)+","+pfb+","+pfb+",0,0,0,0)"
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
						print("["+str(currentReplyPin)+" "+str(pfb)+"] ", end='')
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
					
			cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentStageOrder`='0',lastStageChanged='now()',`runPlanClicked`='"+datetime.now().strftime("%Y-%m-%d")+" 06:59:56', `is_active`=0 WHERE SignalID='"+signal_id+"'")
			db.commit()
			sendSocketMessage("Flash,"+signal_id+"pass")
			sys.exit(0)
		
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

		stagesInHex = ''.join([format(i,'02x').upper() for i in timings])
		Fn = stagesInHex + ''.join(['0' for i in range(0,16 - len(stagesInHex))])
		
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
			stmt1 = stmt + ",`utcControlMO`,`utcControlFn`,`utcControlDX`) VALUES ("+str(site_id)+","+str(timings_to_insert[value]+2)+","+fb+","+fb+",0,0,0,0,1,'"+Fn+"',"+str(va)+")"
			cur.execute(stmt1)
			db.commit()
			cur.execute(stmt1.replace("utcControlTable","utcControlTable_dummy"))
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
			
			# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
			# print("[INFO] ", end='')
			# print("[ATCS] ", end='')
			# print("[Control] ", end='')
			# print("["+str(ug405_reply_pin[stages_at_insert[value]])+" "+str(sb)+"] ", end='')
			# print("["+str(site_id)+"] ", end='')
			# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(timings_to_insert[value]+1))).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
			
			#print("loop "+stmt1+"\n")
			#print("loop "+stmt2+"\n\n")
		# cur.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+","+str(int(end_time)+10)+",0)")
		# db.commit()
		# cur.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+","+str(int(end_time)+10)+",0)")		
		# db.commit()
		# cur.close()
		# db.close()
		# print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ")
		# print("[INFO] ")
		# print("[ATCS] ")
		# print("[Control] ")
		# print("[utcControlHI 0] ")
		# print("["+str(site_id)+"] ")
		# print("[utcControlTimestamp: "+(secondsSinceMidnightToIST(secondsSinceMidnightUTCTosecondsSinceMidnightIST(int(end_time)+10))).strftime("%Y-%m-%d %H:%M:%S")+"]\n")
		
	elif currentMode == "manual" and is_active == 1:
		print("Came to Only Manual")
		startDayTime = 23394
		endDayTime = 84600
		if secondsSinceMidnight(datetime.now()) < startDayTime + 300 or secondsSinceMidnight(datetime.now()) > endDayTime:
			cur.execute("INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,0)")
			db.commit()
			print(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " ", end='')
			print("[INFO] ", end='')
			print("[ATCS] ", end='')
			print("[Control] ", end='')
			print("[utcControlHI 0] ", end='')
			print("["+str(site_id)+"] ", end='')
			print("[utcControlTimestamp: "+(datetime.now()).strftime("%Y-%m-%d %H:%M:%S")+"]\n", end='')
			cur.execute("INSERT INTO `tis`.`utcControlTable_dummy`(`site_id`, `utcControlTimeStamp`, `utcControlHI`) VALUES ("+str(site_id)+",1,0)")
			db.commit()
			cur.execute("UPDATE `utmc_traffic_signal_static` SET `currentStageOrder`='0',lastStageChanged='now()',`runPlanClicked`='"+datetime.now().strftime("%Y-%m-%d")+" 06:59:56', `is_active`=0 WHERE SignalID='"+signal_id+"'")
			db.commit()
			sendSocketMessage("Flash,"+signal_id+"pass")
			db.close()
			sys.exit(0)
else:
	print("else active")
	cur.execute("UPDATE `utmc_traffic_signal_static` SET `is_active`='0' WHERE `SignalID`='"+signal_id+"'")
	db.commit()
	cur.execute("SELECT * FROM `tis_traffic_signal_fault` WHERE `SystemCodeNumber`='"+signalscn+"' ORDER BY `LastUpdated` DESC LIMIT 1")
	data = cur.fetchone()
	if data[2] != 0:
		cur.execute("INSERT INTO `tis_traffic_signal_fault` VALUES('"+signalscn+"','"+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"',0, UNIX_TIMESTAMP(now()) - UNIX_TIMESTAMP('"+str(data[1])+"'))")
		db.commit()
	sendSocketMessage("TimOffline,"+signal_id+"pass")
	db.close()
	sys.exit(0)
