import MySQLdb
import os
import sys
sys.path.append('/var/www/html/tis')
from background.config import * 
from background.client import sendSocketMessage
from datetime import datetime
import subprocess

def get_faultid(fid):
	try:
		FaultID = int(fid) #int((res[0])[1:]) + 1
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

	return FaultID


def process_check(out, process_to_check):
	count = 0
	for process in out.splitlines():
		if process_to_check in process:
			count = count + 1
	if count <= 1:
		return True
	else:
		return False

p = subprocess.Popen(['ps', '-aef'], stdout=subprocess.PIPE)
out, err = p.communicate()

if not process_check(out, 'osho_offline'):
    sys.exit(0)

db = MySQLdb.connect(DB_HOST, DB_USER, DB_PASSWORD ,DB_NAME_TIS)
cur = db.cursor()

cur.execute("SELECT site_id, SignalSCN, ShortDescription from utmc_traffic_signal_static")
signals = cur.fetchall()

for signal in signals:
	site_id = signal[0]
	SignalSCN = signal[1]
	ShortDescription = signal[2]

	print SignalSCN, ShortDescription

	cur.execute("SELECT reply_timestamp, utcReplyCO from tis.utcReplyTable where site_id='"+str(site_id)+"' and utcReplyCO is not null order by reply_timestamp desc limit 1")
	reply = cur.fetchone()
	print reply

	if reply is not None:
		co = reply[1]

		cur.execute("SELECT FaultID FROM `utmc_device_fault` WHERE `SystemCodeNumber`='"+SignalSCN+"' AND FaultType='4' AND EquipmentFault='Y' AND CommunicationsFault='Y' AND ClearedDate IS NULL ORDER BY `CreationDate` DESC LIMIT 1")
		faultid = cur.fetchone()
		print faultid
		if co == 1 and faultid is None:
			print 'create alert'
			description = 'Internal Data Loss at Junction: '+ShortDescription+'. Signal may be Hang or in Flash mode'

			message = "ControllerOffline," + SignalSCN + "," + description + "pass"
			sendSocketMessage("JunctionAlerts",message)

			print datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " [INFO] [ATCS] [Osho Offline] "+ description + "\n"			

			cur.execute("SELECT id,FaultID from `utmc_device_fault` ORDER BY CreationDate DESC LIMIT 1")
			res = cur.fetchone()
			
			faultid = get_faultid(res[0])

			cur.execute("INSERT INTO `utmc_device_fault`(`FaultID`, `SystemCodeNumber`, `FaultType`, `SubSystemTypeID`, `DataSource_TypeID`, `CreationDate`, `EquipmentFault`, `CommunicationsFault`, `Description`,DeviceType) VALUES('"+str(faultid)+"','"+SignalSCN+"',4,1,1,NOW(),'Y','Y','"+description+"',9)")
			db.commit()

			cur.execute("INSERT INTO `utmc_freeflow_alert_dynamic`(`SystemCodeNumber`,ObjectReferenceType_ID) VALUES('"+str(faultid)+"', 9)")
			db.commit()

			cur.execute("UPDATE utmc_traffic_signal_static SET is_controller_active=0 WHERE site_id='"+str(site_id)+"'")
			db.commit()
		elif co == 0 and faultid is not None:
			print 'close alert'
			faultid = faultid[0]
			description = 'Controller Connectivity regained at Junction: '+ShortDescription
			message = "ControllerOnline," + SignalSCN + "," + description +"pass"
			sendSocketMessage("JunctionAlerts",message)
			

			print datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " [INFO] [ATCS] [Osho Offline] "+ description + "\n"

			cur.execute("UPDATE utmc_freeflow_alert_dynamic SET ActionStatus='Closed',`HistoricDate`=NOW() WHERE SystemCodeNumber='"+str(faultid)+"'")
			db.commit()

			cur.execute("UPDATE utmc_device_fault SET `ClearedDate`=NOW() WHERE FaultID='"+str(faultid)+"'")
			db.commit()

			cur.execute("UPDATE utmc_traffic_signal_static SET is_controller_active=1 WHERE site_id='"+str(site_id)+"'")
			db.commit()

