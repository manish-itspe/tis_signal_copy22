
import math
import sys
import json
import MySQLdb
import os
import time
import copy
from demjson import decode
from datetime import datetime
from config import *

# is_atcs
# 1 - va
# 2 - nflo
# 3 - hflo
# 4 - tflo
# 5 - atflo
# 6 - ctflo

def secondsSinceMidnight(c_time):
	return int((c_time - c_time.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())

def handleOffsets(stagesSet, interstagesSet, offsetTimings, referenceJunction):
	t1 = stagesSet
	t2 = interstagesSet
	ctr = 0

	tempstagesSet = copy.deepcopy(t1)
	tempinterstagesSet = copy.deepcopy(t2)
	cycleTimeArray = []
	
	has_offset = 0
	offstagesSet = offsetTimings

	for s in tempstagesSet:
		cy2 = sum(tempstagesSet[s][:])
		cycleTime = sum(tempstagesSet[s][:]) + sum(tempinterstagesSet[s][:])#calculate cycle time
		# cycleTimeArray.append(cycleTime)
		offset = offstagesSet[s]%cycleTime#if offset is greater then ct
		if offset > cycleTime/2:#negative/positive offset
			offset = -cycleTime + offset

		print offset
		if offset > 0:#if positive, increase cycle time
			newCycleTime = cycleTime+offset
			if newCycleTime > MAXCYCLETIME:#if nct>max ct, limit nct to max ct
				newCycleTime = MAXCYCLETIME
				offset = offset - (newCycleTime - cycleTime)#calculate offset still to handle
			else:
				offset = 0
		elif offset < 0:#if negative, decrease ct
			newCycleTime = cycleTime + offset
			if newCycleTime < MINCYCLETIME:#ifc nct<min ct, limit nct to min ct
				newCycleTime = MINCYCLETIME
				offset = offset - (newCycleTime - cycleTime)
				offset = offset + cycleTime#calculate offset still to handle
			else:
				offset = 0
		else:
			newCycleTime = cycleTime
			offset = 0
		delta = newCycleTime - cycleTime#divide difference between stages

		for d in range(1,len(tempstagesSet[s])):
			tempstagesSet[s][d-1] = tempstagesSet[s][d-1] + int(math.ceil(float(delta)*float(tempstagesSet[s][d-1]) / float(cycleTime)))
			if tempstagesSet[s][d-1] > MAXGREENTIME:
				offset = offset + tempstagesSet[s][d-1] - MAXGREENTIME
				tempstagesSet[s][d-1] = MAXGREENTIME
			if tempstagesSet[s][d-1] < MINGREENTIME:
				offset = offset + MINGREENTIME - tempstagesSet[s][d-1]
				tempstagesSet[s][d-1] = MINGREENTIME
		
		tempstagesSet[s][len(tempstagesSet[s])-1] = newCycleTime - sum(tempstagesSet[s][:-1]) - sum(tempinterstagesSet[s])
		if tempstagesSet[s][len(tempstagesSet[s])-1] > MAXGREENTIME:
			offset = offset + tempstagesSet[s][len(tempstagesSet[s])-1] - MAXGREENTIME
			tempstagesSet[s][len(tempstagesSet[s])-1] = MAXGREENTIME
		if tempstagesSet[s][len(tempstagesSet[s])-1] < MINGREENTIME:
			offset = offset + MINGREENTIME - tempstagesSet[s][len(tempstagesSet[s])-1]
			tempstagesSet[s][len(tempstagesSet[s])-1] = MINGREENTIME

		offsetTimings[s] = offset#update offsets to be handled
		if offset != 0:
			has_offset = 1

		# print "all--"
		print s,tempstagesSet[s],offstagesSet[s],sum(tempstagesSet[s][:]),planSCN,planID,"before os\n"
		# print "php "+PATH+"/gui/utils/run_hflo_plan.php " + str(s) + " " + (','.join([str(i) for i in tempstagesSet[s]])) + " " + (','.join([str(i) for i in tempinterstagesSet[s]])) + " '" + planSCN + "' " + str(planID) + ((" >> "+LOGPATH_OutputLog+" 2>&1") if DEBUG == True else "")+" &\n"

		os.system("php "+PATH+"/gui/utils/run_hflo_plan.php " + str(s) + " " + (','.join([str(i) for i in tempstagesSet[s]])) + " " + (','.join([str(i) for i in tempinterstagesSet[s]])) + " '" + planSCN + "' " + str(planID) + ((" >> "+LOGPATH_OutputLog+" 2>&1") if DEBUG == True else "")+" &")
		
		sleepCycleTime = sum(tempstagesSet[s][:]) + sum(tempinterstagesSet[s][:])#calculate cycle time
		cycleTimeArray.append(sleepCycleTime)
	
	print offsetTimings,has_offset,cycleTimeArray,"last\n"

def calculateOffset(stagesSet,interstagesSet,priorityStage,offsetOld,offsetNew,refStage):
	for k in stagesSet:
	    cT = sum(stagesSet[k][:]) + sum(interstagesSet[k][:])
	    a = priorityStage[refStage]
	    if k != refStage:

	        initOffset = offsetOld[k]
	        newOffset = offsetNew[k]
	        pA = sum(stagesSet[refStage][:priorityStage[refStage]]) + sum(interstagesSet[refStage][:priorityStage[refStage]])
	        pB = sum(stagesSet[k][:priorityStage[k]])  + sum(interstagesSet[k][:priorityStage[k]])
	        totalOffset = pA - pB + newOffset-initOffset
	        if (totalOffset < 0):
	            totalOffset = totalOffset + 3 * cT
	        totalOffset = totalOffset % cT
	        # print k,totalOffset
	        offsetNew[k] = totalOffset
	        oldOffset = pA - pB + newOffset
	return offsetNew


db = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIS)
cur = db.cursor()

planSCN = sys.argv[1]
print planSCN,"----"
cur.execute("SELECT signal_timings.SignalSCN,signal_timings.Plan_SCN,GROUP_CONCAT(signal_timings.StageNumber ORDER BY signal_timings.execOrder ASC SEPARATOR ',') as StageNumber,GROUP_CONCAT(signal_timings.StageTime ORDER BY signal_timings.execOrder ASC SEPARATOR ',') as StageTime,GROUP_CONCAT(signal_timings.InterStageTime ORDER BY signal_timings.execOrder ASC SEPARATOR ',') as InterStageTime,plans.Group_SCN, plans.ID FROM signal_timings INNER JOIN plans ON plans.PlanSCN = signal_timings.Plan_SCN where signal_timings.Plan_SCN='"+planSCN+"' AND execOrder <> 0 GROUP BY signal_timings.SignalSCN")
planinfo = cur.fetchall()

signalTimingsObect = {}
signalSCNArr = []
signalCTimeObject = {}
stagesSet = {}
interstagesSet = {}
Group_SCN = ''
planID = ''

for plans in planinfo:
	cycleTime = 0
	StageTimeArr = plans[3].split(',')
	InterStageTimeArr = plans[4].split(',')
	timingsArr = []
	for i in range(0,len(StageTimeArr)):
		cycleTime += int(StageTimeArr[i])	
		timingsArr.append(int(StageTimeArr[i]))	
		timingsArr.append(int(InterStageTimeArr[i]))
	
	signalTimingsObect[plans[0]] = timingsArr
	signalCTimeObject[plans[0]] = cycleTime
	signalSCNArr.append(plans[0])
	planSCN = plans[1]
	Group_SCN = plans[5]
	planID = plans[6]

	stagesSet[plans[0]] = [int(n) for n in plans[3].split(",")]
	interstagesSet[plans[0]] = [int(n) for n in plans[4].split(",")]

print signalTimingsObect
print signalCTimeObject
print signalSCNArr
print planSCN
print Group_SCN,"------"
print stagesSet
print interstagesSet


cur.execute("SELECT SignalSCN,SignalOffset FROM utmc_traffic_signal_static WHERE Group_SCN='"+Group_SCN+"'")
result = cur.fetchall()
offsetOld = {}
for res in result:
	offsetOld[res[0]] = res[1]
print offsetOld

cur.execute("SELECT plans.CriticalSignalSCN,routes.FromSignalSCN,routes.ToSignalSCN,routes.FromApproach,routes.ToApproach,routes.CurrentOffset FROM plans INNER JOIN routes ON FIND_IN_SET(routes.id, REPLACE(TRIM(REPLACE(`plans`.`CriticalRoutes`, ';', ' ')), ' ', ',')) WHERE plans.PlanSCN = '"+planSCN+"'")
routeinfo = cur.fetchall()

offsetNew = {}
offsetObj = {}
CriticalSignalSCN = ''
# print offsetOld

for route in routeinfo:
	CriticalSignalSCN = route[0]
	FromSignalSCN = route[1]
	ToSignalSCN = route[2]
	FromApproach = route[3] - 1
	ToApproach = route[4] - 1
	CurrentOffset = route[5]
	offsetObj[CriticalSignalSCN] = 0
	
	if CriticalSignalSCN == FromSignalSCN:
		cT = sum(stagesSet[ToSignalSCN][:]) + sum(interstagesSet[ToSignalSCN][:])
		initOffset = offsetOld[ToSignalSCN]
		newOffset = CurrentOffset
		pA = sum(stagesSet[CriticalSignalSCN][:FromApproach]) + sum(interstagesSet[CriticalSignalSCN][:FromApproach])
		pB = sum(stagesSet[ToSignalSCN][:ToApproach])  + sum(interstagesSet[ToSignalSCN][:ToApproach])
		totalOffset = pA - pB + newOffset-initOffset
		print pA,pB,newOffset,initOffset,"data"
		if (totalOffset < 0):
			totalOffset = totalOffset + 3 * cT
		totalOffset = totalOffset % cT
		# print k,totalOffset
		offsetNew[ToSignalSCN] = totalOffset
		# oldOffset = pA - pB + newOffset
		offsetObj[ToSignalSCN] = totalOffset
	elif CriticalSignalSCN == ToSignalSCN:
		cT = sum(stagesSet[ToSignalSCN][:]) + sum(interstagesSet[ToSignalSCN][:])
		initOffset = offsetOld[FromSignalSCN]
		newOffset = CurrentOffset
		pA = sum(stagesSet[CriticalSignalSCN][:ToApproach]) + sum(interstagesSet[CriticalSignalSCN][:ToApproach])
		pB = sum(stagesSet[FromSignalSCN][:FromApproach])  + sum(interstagesSet[FromSignalSCN][:FromApproach])
		totalOffset = -(pA - pB + newOffset-initOffset)
		print pA,pB,newOffset,initOffset,"data"
		if (totalOffset < 0):
			totalOffset = totalOffset + 3 * cT
		totalOffset = totalOffset % cT
		# print k,totalOffset
		offsetNew[FromSignalSCN] = totalOffset
		offsetObj[FromSignalSCN] = totalOffset
		# oldOffset = pA - pB + newOffset	
	elif CriticalSignalSCN != FromSignalSCN and CriticalSignalSCN != ToSignalSCN:
		cT = sum(stagesSet[FromSignalSCN][:]) + sum(interstagesSet[FromSignalSCN][:])
		initOffset = offsetOld[FromSignalSCN]
		newOffset = CurrentOffset
		pA = sum(stagesSet[FromSignalSCN][:FromApproach]) + sum(interstagesSet[FromSignalSCN][:FromApproach])
		pB = sum(stagesSet[ToSignalSCN][:ToApproach])  + sum(interstagesSet[ToSignalSCN][:ToApproach])
		totalOffset = pA - pB + newOffset-initOffset
		print pA,pB,newOffset,initOffset,"data"
		if (totalOffset < 0):
			totalOffset = totalOffset + 3 * cT
		totalOffset = totalOffset % cT
		# print k,totalOffset
		offsetNew[ToSignalSCN] = totalOffset
		# oldOffset = pA - pB + newOffset
		# offsetObj[FromSignalSCN] = totalOffset
		if FromSignalSCN not in offsetObj:
			offsetObj[FromSignalSCN] = 0
		offsetObj[ToSignalSCN] = totalOffset + offsetObj[FromSignalSCN]
		
signalData = signalTimingsObect #{"Amballur":[30,4,25,4,19,4,40,4], "Pudukkad":[25,4,25,4,50,4,14,4], "C3":[36,4,32,4,24,4,22,4]}
offsetNew = offsetObj #{"Amballur":0,"Pudukkad":10,"C3":29}
priorityStages = '' #{"Amballur":0,"Pudukkad":3,"C3":2}
referenceJunction = CriticalSignalSCN #"Amballur"

stagesSet = {}
interstagesSet = {}

for key in signalData:
	stagearray = []
	interstagearray = []
	# print signalData[key],len(signalData[key])
	for i in range(0,len(signalData[key])):
		if i % 2 == 0:
			stagearray.append(signalData[key][i])
		else:
			interstagearray.append(signalData[key][i])
	stagesSet[key] = stagearray
	interstagesSet[key] = interstagearray

cur.execute("SELECT min_green_time,max_green_time FROM utmc_traffic_signal_stages where SignalSCN='"+CriticalSignalSCN+"' GROUP BY SignalSCN LIMIT 1")
timeLimits = cur.fetchone()

# cur.execute("SELECT CycleTime,SUM(InterStageTime) FROM plans INNER JOIN signal_timings ON signal_timings.Plan_SCN = plans.PlanSCN WHERE plans.is_atcs=1 AND is_active=1 GROUP BY PlanSCN LIMIT 1")
cur.execute("SELECT SUM(StageTime) as CycleTime,SUM(InterStageTime) FROM plans INNER JOIN signal_timings ON signal_timings.Plan_SCN = plans.PlanSCN AND signal_timings.Plan_SCN='"+str(planSCN)+"' AND signal_timings.SignalSCN='"+CriticalSignalSCN+"' AND execOrder <> 0")
refCycleTime = cur.fetchone()
print planSCN,CriticalSignalSCN
YELLOWTIME = 0
MINGREENTIME = timeLimits[0]
MAXGREENTIME = timeLimits[1]
MINCYCLETIME = int(refCycleTime[0]) - 16
MAXCYCLETIME = int(refCycleTime[0]) + 16
UT = 0

print MINCYCLETIME,MAXCYCLETIME,refCycleTime[0],refCycleTime[1],MINGREENTIME,MAXGREENTIME

# calculateOffset(stagesSet, interstagesSet, priorityStages,offsetOld,offsetNew,referenceJunction)

for scn in offsetObj:
	cur.execute("UPDATE utmc_traffic_signal_static SET SignalOffset ='"+str(offsetObj[scn])+"' WHERE SignalSCN='"+scn+"'")
	db.commit()

print stagesSet
print interstagesSet
print offsetObj
print referenceJunction
print str(sum(stagesSet[referenceJunction]))



# cur.execute("UPDATE plans SET groupCycleTime ='"+str(sum(stagesSet[referenceJunction]))+"' WHERE PlanSCN='"+planSCN+"'")
# db.commit()

handleOffsets(stagesSet, interstagesSet, offsetObj, referenceJunction)

cur.close()
db.close()