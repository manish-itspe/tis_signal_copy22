import math
import sys
import json
import MySQLdb
import os
import time
import copy
from demjson import decode
from datetime import datetime

def secondsSinceMidnight(c_time):
	return int((c_time - c_time.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds())

def handleOffsets(stagesSet, interstagesSet, offsetTimings, referenceJunction):
	cur.execute("UPDATE utmc_traffic_signal_static SET has_offset = '1' WHERE is_atcs_active=1")
	db.commit()

	time.sleep(1)

	has_offset = 1
	t1 = stagesSet
	t2 = interstagesSet
	ctr = 0

	while(True):	
		# print t1
		tempstagesSet = copy.deepcopy(t1)
		tempinterstagesSet = copy.deepcopy(t2)
		# print tempstagesSet
		# print "-----------"
		cycleTimeArray = []
		
		if has_offset == 1:
			has_offset = 0
			offstagesSet = offsetTimings

			# print "oooooooo"
			# print tempstagesSet,offsetTimings
			# print "oooooooo\n\n"
			

			for s in tempstagesSet:
				cycleTime = sum(tempstagesSet[s][:]) #+ sum(tempinterstagesSet[s][:])#calculate cycle time
				# cycleTimeArray.append(cycleTime)
				offset = offstagesSet[s]%cycleTime#if offset is greater then ct
				if offset > cycleTime/2:#negative/positive offset
					offset = -cycleTime + offset

				if offset > 0:#if positive, increase cycle time
					newCycleTime = cycleTime+offset
					if newCycleTime > MAXCYCLETIME:#if nct>max ct, limit nct to max ct
						newCycleTime = MAXCYCLETIME
						offset = offset - (newCycleTime - cycleTime)#calculate offset still to handle
					else:
						offset = 0
				elif offset < 0:#if negative, decrease ct
					newCycleTime = cycleTime - offset
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
				
				tempstagesSet[s][len(tempstagesSet[s])-1] = newCycleTime - sum(tempstagesSet[s][:-1])
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
				print s,tempstagesSet[s],offstagesSet[s],sum(tempstagesSet[s][:])
				# print "all--"
				cur.execute("SELECT site_id FROM utmc_traffic_signal_static WHERE SCN='"+s+"'")
				site_id = cur.fetchone()

				stagesInHex = ''.join([format(i,'02x').upper() for i in tempstagesSet[s]])
				Fn = stagesInHex + ''.join(['0' for i in range(0,16 - len(stagesInHex))])

				stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlDX`,`utcControlFn`) VALUES ("+str(site_id[0])+",1,1,'" + Fn + "')"
				cur.execute(stmt)
				db.commit()
				cur.execute(stmt.replace("utcControlTable","utcControlTable_dummy"))
				db.commit()

				print site_id,Fn,site_id[0]

				os.system("php /var/www/html/tis/gui/utils/run_atcs_plans.php " + str(s) + " " + (','.join([str(i) for i in tempstagesSet[s]])) + " " + (','.join([str(i) for i in tempinterstagesSet[s]])) + " >> /var/log/tisLog/tisdatalog 2>&1 & echo $!")
				sleepCycleTime = sum(tempstagesSet[s][:]) + sum(tempinterstagesSet[s][:])#calculate cycle time
				cycleTimeArray.append(sleepCycleTime)
			
			print offsetTimings,has_offset,cycleTimeArray

			# if has_offset == 1:
				# time.sleep(min(cycleTimeArray) - 5)
			if has_offset == 0 and ctr == 0:
				has_offset = 1
				ctr = 1
				# time.sleep(5)
			
			# time.sleep(min(cycleTimeArray) - 5)
			time.sleep(2)
			
			cur.execute("SELECT runPlanClicked FROM utmc_traffic_signal_static WHERE SCN='"+referenceJunction+"' and is_atcs_active=1")
			runPlanClicked = cur.fetchone()[0]
			# print runPlanClicked
			sleeptime = secondsSinceMidnight(runPlanClicked) - secondsSinceMidnight(datetime.now()) + min(cycleTimeArray) - 5
			
			print secondsSinceMidnight(runPlanClicked), secondsSinceMidnight(datetime.now()), min(cycleTimeArray)

			if sleeptime < 0:
				sleeptime = 0
			
			time.sleep(sleeptime)

		else:
			cur.execute("SELECT site_id FROM utmc_traffic_signal_static WHERE is_atcs_active='1'")
			sites = cur.fetchall()
			
			for s in sites:
				print str(s[0])+"stes"
				stmt = "INSERT INTO `tis`.`utcControlTable`(`site_id`, `utcControlTimeStamp`, `utcControlDX`) VALUES ("+str(s[0])+",1,0)"
				cur.execute(stmt)
				db.commit()
				cur.execute(stmt.replace("utcControlTable","utcControlTable_dummy"))
				db.commit()
			cur.execute("UPDATE utmc_traffic_signal_static SET has_offset = '0' WHERE is_atcs_active=1")
			db.commit()
			# print "else"
			cur.close()
			db.close()
			break
		# print offsetTimings,has_offset

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

signalData = decode(sys.argv[1]) #{"Amballur":[30,4,25,4,19,4,40,4], "Pudukkad":[25,4,25,4,50,4,14,4], "C3":[36,4,32,4,24,4,22,4]}
offsetNew = decode(sys.argv[2]) #{"Amballur":0,"Pudukkad":10,"C3":29}
priorityStages = decode(sys.argv[3]) #{"Amballur":0,"Pudukkad":3,"C3":2}
referenceJunction = sys.argv[4] #"Amballur"

# python implementOffset.py '{"NAGARN":[36,4,26,4,26,4],"LAKXMI":[36,4,26,4,26,4],"GANDHI":[36,4,26,4,26,4]}' '{"LAKXMI":0,"GANDHI":85,"NAGARN":150}' '{"NAGARN":0,"LAKXMI":0,"GANDHI":0}' 'LAKXMI'

db = MySQLdb.connect(host="localhost",user="root",passwd="itspe",db="htms")
cur = db.cursor()

cur.execute("SELECT SCN,SignalOffset FROM utmc_traffic_signal_static WHERE is_atcs_active=1")
result = cur.fetchall()

offsetOld = {}
for res in result:
	offsetOld[res[0]] = res[1]

stagesSet = {}
interstagesSet = {}

for key in signalData:
	stagearray = []
	interstagearray = []
	print signalData[key],len(signalData[key])
	for i in range(0,len(signalData[key])):
		if i % 2 == 0:
			stagearray.append(signalData[key][i])
		else:
			interstagearray.append(signalData[key][i])
	stagesSet[key] = stagearray
	interstagesSet[key] = interstagearray


cur.execute("SELECT min_green_time,max_green_time FROM utmc_traffic_signal_stages GROUP BY SignalID LIMIT 1")
timeLimits = cur.fetchone()

cur.execute("SELECT CycleTime,SUM(InterStageTime) FROM plans INNER JOIN signal_timings ON signal_timings.Plan_SCN = plans.PlanSCN WHERE plans.is_atcs=1 AND is_active=1 GROUP BY PlanSCN LIMIT 1")
refCycleTime = cur.fetchone()

YELLOWTIME = 0
MINGREENTIME = timeLimits[0]
MAXGREENTIME = timeLimits[1]
MINCYCLETIME = int(refCycleTime[0]) - 16
MAXCYCLETIME = int(refCycleTime[0]) + 16
UT = 0

print MINCYCLETIME,MAXCYCLETIME,refCycleTime[0],refCycleTime[1],MINGREENTIME,MAXGREENTIME

calculateOffset(stagesSet, interstagesSet, priorityStages,offsetOld,offsetNew,referenceJunction)

for scn in offsetNew:
	cur.execute("UPDATE utmc_traffic_signal_static SET SignalOffset ='"+str(offsetNew[scn])+"' WHERE SCN='"+scn+"'")
	db.commit()

handleOffsets(stagesSet, interstagesSet, offsetNew, referenceJunction)