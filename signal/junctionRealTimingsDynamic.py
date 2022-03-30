import os, sys
import time
import datetime
import MySQLdb
from datetime import datetime, timedelta
from config import *

def calculateTimings(timestamps, stageorder, signal_scn, PlanID, currentMode):
	timestamps = timestamps.split(',')
	stageorder = stageorder[::-1]

	timings = []
	for i in range(1,len(timestamps)):
		time_diff = datetime.strptime(timestamps[i-1],fmt) - datetime.strptime(timestamps[i],fmt)
		timings.append(int(time_diff.total_seconds()))

	timings = timings[::-1]
	timings = (','.join(str(x) for x in timings))
	# print timings

	try:
		htms_cursor.execute("INSERT INTO `utmc_traffic_signal_dynamic`(`SystemCodeNumber`, `ControlStrategy`, `PlanNumber`, `StageSequence`, `PlanTimings`, `LastUpdated`, `HistoricDate`, `Reality`) VALUES ('" + signal_scn + "', '" + str(currentMode) + "', '" + str(PlanID) + "', '" + stageorder + "', '" + timings + "', NOW(), NOW(), 'Real')")
		htmsdb.commit()
	except Exception as e:
		print e

fmt = '%Y-%m-%d %H:%M:%S'
pid = str(os.getpid())
pidfile = "/tmp/junction_real_timings.pid"
if os.path.isfile(pidfile):
	sys.exit()
file(pidfile, 'w').write(pid)

try:
	idObj = {}

	while(1):
		htmsdb = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIS)
		tisdb = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIM)
		tis_cursor = tisdb.cursor()
		htms_cursor = htmsdb.cursor()

		try:
			htms_cursor.execute("SELECT GROUP_CONCAT(signal_timings.StageNumber ORDER BY execOrder DESC SEPARATOR ',') as StageNumber, utmc_traffic_signal_static.SignalSCN, utmc_traffic_signal_static.site_id, plans.ID, utmc_traffic_signal_static.currentMode FROM signal_timings INNER JOIN plans ON plans.PlanSCN = signal_timings.Plan_SCN INNER JOIN utmc_traffic_signal_static ON utmc_traffic_signal_static.currentPlan = plans.ID AND utmc_traffic_signal_static.SignalSCN = signal_timings.SignalSCN GROUP BY signal_timings.Plan_SCN,signal_timings.SignalSCN ")
			stageObj = htms_cursor.fetchall()

			for data in stageObj:
				stageorder = data[0]
				signal_scn = data[1]
				site_id = data[2]
				PlanID = data[3]
				currentMode = data[4]

				# print stageorder, signal_scn, site_id
				try:
					tis_cursor.execute("SELECT GROUP_CONCAT(d.reply_timestamp SEPARATOR ',') as timestamp, GROUP_CONCAT(d.Stages) as Stages, GROUP_CONCAT(d.id SEPARATOR ',') as id FROM (SELECT reply_timestamp, RIGHT(utcReplyGn,1) as Stages, id FROM utcReplyTable WHERE site_id='" + str(site_id) + "' AND utcReplyGn IS NOT NULL AND utcReplyGn != '0000000000000000' ORDER BY reply_timestamp DESC LIMIT " + str(len(stageorder.split(','))+1) + ") d GROUP BY NULL")
					livedata = tis_cursor.fetchone()

					l_timestamps = livedata[0]
					l_stageorder = livedata[1]
					ids = livedata[2]

					# print l_timestamps, l_stageorder
					if (site_id in idObj) and idObj[site_id] != ids:
						if stageorder == (l_stageorder[2:]):
							calculateTimings(l_timestamps, stageorder, signal_scn, PlanID, currentMode)
					
					idObj[site_id] = ids

				except Exception as e:
					print e

				time.sleep(1)

		except Exception as e:
			print e

		# print idObj

		tis_cursor.close()
		htms_cursor.close()
		tisdb.close()
		htmsdb.close()
finally:
	os.unlink(pidfile)