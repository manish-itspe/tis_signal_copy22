from __future__ import division
import os, subprocess, sys, time, csv, math, json
import random
import copy
import pickle
import anydbm
import xml.etree.ElementTree as etree
import time
import datetime
import multiprocessing as mp
import MySQLdb
from datetime import datetime
from datetime import timedelta
from operator import itemgetter
from warnings import filterwarnings
from config import *

EVERY = 900 / 180

# from sumolib import checkBinary
# import traci
# import traci.constants as tc

htmsdb = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIS)
tisdb = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIM)
tis_cursor = tisdb.cursor()
htms_cursor = htmsdb.cursor()

siteid = sys.argv[1]
scn = sys.argv[2]
# htms_cursor.execute("SELECT GROUP_CONCAT(DET_SCN SEPARATOR '') as detectors, utmc_traffic_signal_static.SignalSCN, site_id FROM utmc_signal_movements INNER JOIN utmc_traffic_signal_static ON utmc_traffic_signal_static.SignalSCN = utmc_signal_movements.SignalSCN AND utmc_traffic_signal_static.Group_SCN = 'AGRA' GROUP BY site_id")
htms_cursor.execute("SELECT GROUP_CONCAT(DET_SCN ORDER BY id ASC SEPARATOR '') as detectors, utmc_traffic_signal_static.SignalSCN, site_id, GROUP_CONCAT(ug405DetectorBitNumber ORDER BY id ASC SEPARATOR '') as bitnumber FROM utmc_signal_movements INNER JOIN utmc_traffic_signal_static ON utmc_traffic_signal_static.SignalSCN = utmc_signal_movements.SignalSCN AND site_id = '"+str(siteid)+"' GROUP BY site_id")
detector_data = htms_cursor.fetchall()

junctions_list=[]
junction_to_detectors_dict={}
det = {}
# print detector_data,'dete'
for data in detector_data:
	
	bitnumber_arr = data[3].split(';')
	bitnumber_arr.pop()
	# print bitnumber_arr
	bitnumber_arr = [ 0 if n == '' else int(n) for n in bitnumber_arr]

	det_arr = data[0].split(';')
	det_arr.pop()

	jd = {}
	for i in range(len(bitnumber_arr)):
		jd[bitnumber_arr[i]] = det_arr[i]

	junctions_list.append(data[2])
	junction_to_detectors_dict[data[2]] = jd.values()
	# junction_to_detectors_dict[data[2]].pop()

# print junctions_list
# print junction_to_detectors_dict

# sys.exit()
# print "----------------\n\n\n"
# junctions_list = [1L,2L,3L]
# junction_to_detectors_dict = {
# 2L: ['STJOHN0', 'STJOHN1', 'STJOHN2', 'STJOHN3', 'STJOHN4', 'STJOHN5', 'STJOHN6', 'STJOHN7', 'STJOHN8', 'STJOHN9', 'STJOHN10', 'STJOHN11', 'STJOHN12', 'STJOHN13', 'STJOHN14', 'STJOHN15'],
# 1L: ['HARIPARWAT0', 'HARIPARWAT1', 'HARIPARWAT2', 'HARIPARWAT3', 'HARIPARWAT4', 'HARIPARWAT5', 'HARIPARWAT6', 'HARIPARWAT7', 'HARIPARWAT8', 'HARIPARWAT9', 'HARIPARWAT10', 'HARIPARWAT11', 'HARIPARWAT12', 'HARIPARWAT13', 'HARIPARWAT14', 'HARIPARWAT15'], 
# 3L: ['NAGARNIGAM0', 'NAGARNIGAM1', 'NAGARNIGAM2', 'NAGARNIGAM3', 'NAGARNIGAM4', 'NAGARNIGAM5', 'NAGARNIGAM6', 'NAGARNIGAM7', 'NAGARNIGAM8', 'NAGARNIGAM9', 'NAGARNIGAM10', 'NAGARNIGAM11', 'NAGARNIGAM12', 'NAGARNIGAM13', 'NAGARNIGAM14', 'NAGARNIGAM15']
# }

def get_utcReplyTableData(endTime):
	""" Function to extract data from utcReplyTable
		Output: {"det1":[1,4,0,2,3,..],"det2":[8,12,0,0,1,..]}
	"""

	global junctions_list,junction_to_detectors_dict
	global EVERY

	big_measure_dict = {}
	occupancy_dict = {}
	for site_id in junctions_list:

		detectors = junction_to_detectors_dict[site_id]
		# print detectors

		timeInt = EVERY
		# end_Time = datetime.strptime(endTime,"%Y-%m-%d %H:%M:%S") #datetime.utcnow()
		end_Time = endTime - timedelta(minutes = 1)
		start_Time = end_Time - timedelta(minutes = EVERY)

		counter_dict,time_counter_dict = loopOverDetector(site_id,start_Time,end_Time,1,detectors,"utcReplyBDn")
		# print counter_dict, "cdit"
		# print time_counter_dict, "ticdic"

		for i in counter_dict:
			# print counter_dict[i],time_counter_dict[i],"timectr"
			big_measure_dict[i] = sum(counter_dict[i])
			# if sum(time_counter_dict[i]) == 0:
			# 	occupancy_dict[i] = sum(counter_dict[i]) / 1
			# else:
			occupancy_dict[i] = sum(time_counter_dict[i]) / (EVERY*60) #sum(counter_dict[i]) / sum(time_counter_dict[i])
			# print occupancy_dict[i],"occdic"
	# print big_measure_dict,occupancy_dict
	return big_measure_dict,occupancy_dict
	
def getVehicleCount(config, detectors, out, dettime):
	count=0
	scale = 2#16
	num_of_bits = 16#64	#8
	# v=np.zeros(len(detectors))
	arr_1to0 = []
	arr_0to1 = []
	arr_time_0to1 = []

	for i in range(0,len(detectors)):
		arr_0to1.append(0)
		# arr_1to0.append(0)
		arr_time_0to1.append(0)

	# print arr_time_0to1,"time"
	for i in range(1,len(config)):
		# print config[i], config[i-1], "in"
		i1 = bin(int(config[i][0], scale))[2:].zfill(num_of_bits)
		t1 = config[i][1]
		i2 = bin(int(config[i-1][0], scale))[2:].zfill(num_of_bits)
		t2 = config[i-1][1]
		time_diff = int((t1 - t2).total_seconds())
		k=len(i1)
		# v=0
		
		for j in range(0,len(detectors)-1):
			if int(i1[j]) == 0 and int(i2[j]) == 1:
				arr_0to1[j] = arr_0to1[j] + 1
				arr_time_0to1[j] = arr_time_0to1[j] + time_diff
			elif int(i1[j]) == 1 and int(i2[j]) == 1:
				arr_time_0to1[j] = arr_time_0to1[j] + time_diff
			# elif int(i1[j]) == 1 and int(i2[j]) == 0:
			# 	arr_1to0[j] = arr_1to0[j] + 1

	# print arr_0to1, arr_time_0to1, "arr"
	for i in range(0,len(detectors)):
		out[detectors[i]].append(arr_0to1[i])
		dettime[detectors[i]].append(arr_time_0to1[i])
		
	# print out, "---------", dettime, "\n\n"
	return out,dettime

def loopOverDetector(site_id, start_Time, end_Time, timeInt,detectors, key):
	out={}
	dettime={}
	for i in range(0,len(detectors)):
		out[detectors[i]]=[]
		dettime[detectors[i]]=[]
	
	while start_Time<end_Time:
		eTime = start_Time + timedelta(minutes=timeInt)
		tis_cursor.execute("SELECT "+str(key)+", reply_timestamp FROM `utcReplyTable` WHERE `site_id` ='"+str(site_id) +"' AND `reply_timestamp` < '"+str(eTime)+"' AND `reply_timestamp` > '"+str(start_Time)+"' AND "+str(key)+" IS NOT NULL")
		config = tis_cursor.fetchall()
		# print config, "config", start_Time, eTime
		if len(config) != 0:			
			out, dettime = getVehicleCount(config,detectors,out,dettime)
			
		start_Time = start_Time + timedelta(minutes=timeInt)

	return out,dettime

def getFlowData(start_Time, end_Time):
	global junctions_list,junction_to_detectors_dict

	count_arr = {}

	for site_id in junctions_list:
		detectors = junction_to_detectors_dict[site_id]
		# print detectors,"fl"
		print "SELECT site_id, reply_timestamp, utcReplySDn FROM utcReplyTable WHERE utcReplySDn IS NOT NULL AND reply_timestamp > '"+str(start_Time)+"' AND reply_timestamp < '"+str(end_Time)+"' AND site_id='"+str(site_id)+"' ORDER BY reply_timestamp ASC"
		tis_cursor.execute("SELECT site_id, reply_timestamp, utcReplySDn FROM utcReplyTable WHERE utcReplySDn IS NOT NULL AND reply_timestamp > '"+str(start_Time)+"' AND reply_timestamp < '"+str(end_Time)+"' AND site_id='"+str(site_id)+"' ORDER BY reply_timestamp ASC")
		result = tis_cursor.fetchall()

		
		sdn_arr = {}
		det_arr = detectors #[0,1,2]

		for d in detectors:
			sdn_arr[d] = []

		for res in result:
			data = list(res[2])
			# print data

			for i in range(len(detectors)):
				sdn_arr[detectors[i]].append(data[i])

		# print sdn_arr

		for data in sdn_arr:
			d = sdn_arr[data]
			# print d,data
			count_arr[data] = 0
			for i in range(len(d)):
				if i < len(d)-1:
					diff = int(d[i+1], 16) - int(d[i], 16)
					if diff >= 0:
						count_arr[data] = count_arr[data] + diff
					else:
						count_arr[data] = count_arr[data] + int(d[i+1], 16)
					# print count_arr
		# print count_arr
	
	return count_arr

endTime = datetime.utcnow() #datetime.strptime("2019-01-09 08:00:00","%Y-%m-%d %H:%M:%S")
startTime = endTime - timedelta(minutes = EVERY)

detector_count,occupancy = get_utcReplyTableData(endTime)
detectorFlow = getFlowData(startTime, endTime)

print detector_count, "detector count"
# print occupancy, "occupancy"
# print detectorFlow

# for data in detector_count:
print "---"
print siteid
print detectorFlow
print "---"
det_count = {}

for data in occupancy:
	if data != '':
		print data
		det_count[data] = detectorFlow[data]

		htms_cursor.execute("UPDATE `utmc_detector_dynamic` SET HistoricDate=NOW() WHERE SystemCodeNumber='"+data+"' AND Reality='Real' AND HistoricDate IS NULL")
		htmsdb.commit()

		htms_cursor.execute("INSERT INTO `utmc_detector_dynamic`(`SystemCodeNumber`, `TotalFlow`, `FlowInterval`, `Class1Count`, `Class2Count`, `Class3Count`, `Class4Count`, `Class5Count`, `Class6Count`, `Class7Count`, `Class8Count`, `FlowStatus_TypeID`, `Occupancy`, `OccupancyInterval`, `OccupancyStatus_TypeID`, `Speed`, `SpeedInterval`, `SpeedStatus_TypeID`, `QueuePresent`, `QueueSeverity_TypeID`, `Headway`, `HeadwayInterval`, `HeadwayStatus_TypeID`, `LastUpdated`, `HistoricDate`, `Colour`, `Reality`) VALUES ('"+data+"', '"+str(detectorFlow[data])+"', '"+str(EVERY)+"',0,0,0,0,0,0,0,0,0,'"+str(occupancy[data])+"','"+str(EVERY)+"', 0, 0, 0, 0, 0, 0, 0, 0, 0, CURRENT_TIMESTAMP, NULL, NULL, 'Real')")
		htmsdb.commit()

		#continue
		htms_cursor.execute("SELECT online, LastUpdated FROM tis_detector_fault where SystemCodeNumber='"+str(data)+"' ORDER BY LastUpdated DESC LIMIT 1")
		res = htms_cursor.fetchone()
		if res is None:
			if detectorFlow[data] == 0:
				htms_cursor.execute("INSERT INTO tis_detector_fault VALUES ('"+str(data)+"', NOW(), '0', '0')")
				htmsdb.commit()
			else:
				htms_cursor.execute("INSERT INTO tis_detector_fault VALUES ('"+str(data)+"', NOW(), '1', '0')")
				htmsdb.commit()
		else:
			status = res[0]
			LastUpdated	= res[1]

			if detectorFlow[data] == 0:
				if status == 1:
                                        try:
					        htms_cursor.execute("INSERT INTO tis_detector_fault VALUES ('"+str(data)+"', NOW(), '0', UNIX_TIMESTAMP(now()) - UNIX_TIMESTAMP('"+str(LastUpdated)+"'))")
					        htmsdb.commit()
                                        except Exception as e:
						htms_cursor.execute("INSERT INTO tis_detector_fault(SystemCodeNumber, LastUpdated, online, time) VALUES('"+str(data)+"', now(), '0', 0)")
						htmsdb.commit()
			else:
				if status == 0:
                                        try:
					    	htms_cursor.execute("INSERT INTO tis_detector_fault VALUES ('"+str(data)+"', NOW(), '1', UNIX_TIMESTAMP(now()) - UNIX_TIMESTAMP('"+str(LastUpdated)+"'))")
					    	htmsdb.commit()
                                        except Exception as e:
						htms_cursor.execute("INSERT INTO tis_detector_fault(SystemCodeNumber, LastUpdated, online, time) VALUES('"+str(data)+"', now(), '1', 0)")
						htmsdb.commit()

htms_cursor.execute("SELECT SystemCodeNumber, GROUP_CONCAT(DET_SCN SEPARATOR '') FROM utmc_transport_link_static INNER JOIN utmc_traffic_signal_static_links ON utmc_traffic_signal_static_links.LinkID = utmc_transport_link_static.TransportLinkRef AND utmc_traffic_signal_static_links.SignalSCN='"+scn+"' INNER JOIN utmc_signal_movements ON utmc_signal_movements.from_link = utmc_traffic_signal_static_links.LinkOrder AND utmc_traffic_signal_static_links.SignalSCN = utmc_signal_movements.SignalSCN AND utmc_signal_movements.SignalSCN='"+scn+"' GROUP BY utmc_transport_link_static.SystemCodeNumber")
res = htms_cursor.fetchall()
for r in res:
    linkscn = r[0]
    dets = (r[1])[:-1]
    det_scn = list(set(dets.split(';')))
    count = 0
    for det in det_scn:
            count = count + det_count[det]

    htms_cursor.execute("UPDATE utmc_transport_link_data_dynamic SET HistoricDate=NOW() WHERE Reality='Detector' AND SystemCodeNumber='"+linkscn+"' AND HistoricDate IS NULL")
    htmsdb.commit()

    htms_cursor.execute("INSERT INTO `utmc_transport_link_data_dynamic`(`SystemCodeNumber`, `CongestionPercent`, `CurrentFlow`, `AverageSpeed`, `LinkStatus_TypeID`, `LinkTravelTime`, `OccupancyPercent`, `LastUpdated`, `HistoricDate`, `Colour`, `Reality`) VALUES ('"+linkscn+"', NULL, '"+str(count)+"',NULL,0,NULL,NULL, CURRENT_TIMESTAMP,NULL, NULL, 'Detector')")
    htmsdb.commit()

tis_cursor.close()
htms_cursor.close()
tisdb.close()
htmsdb.close()

