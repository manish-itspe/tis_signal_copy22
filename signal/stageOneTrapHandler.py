import MySQLdb
from datetime import datetime, date, timedelta
import time
import os
import sys
from config import *

pid = str(os.getpid())
pidfile = "/tmp/trap_reply_stage_one.pid"
if os.path.isfile(pidfile):
	sys.exit()
file(pidfile, 'w').write(pid)
started = 0
try:
	while(1):
		db = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIM)
		cursor = db.cursor()
		cursor.execute("SELECT stage_one_triggers.*,sites.site_ref FROM stage_one_triggers INNER JOIN sites ON stage_one_triggers.site_id=sites.id")
		results = cursor.fetchall()
		if started != 0:
			for result in results:
				os.system("python "+PATH+"/background/triggerStageOneCheck.py "+str(result[0])+" &")
		cursor.execute("DELETE FROM stage_one_triggers WHERE 1")
		db.commit()
		cursor.close()
		db.close()
		started = 1
		time.sleep(1)
finally:
	os.unlink(pidfile)
