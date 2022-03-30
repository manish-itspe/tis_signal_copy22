from multiprocessing.pool import ThreadPool as Pool
# from multiprocessing import Pool
import MySQLdb
import os
from config import *
import datetime
import subprocess
import time
import sys

db = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIS)
cursor = db.cursor()

cursor.execute("SELECT SignalSCN from utmc_traffic_signal_static WHERE Group_SCN <> ''")
signals = cursor.fetchall()

cursor.execute("SELECT DISTINCT Group_SCN from utmc_traffic_signal_static WHERE Group_SCN <> ''")
groups = cursor.fetchall()

pool_size = 14  # your "parallelness"

is_cronjob = '1'

def signal_reports(signal_scn, date, start_datetime, end_datetime):
	#try:
	#	subprocess.Popen(['php', (UTILS_PATH + "/reports/get_stagetimereport_data.php"), is_cronjob, signal_scn, date, start_datetime, end_datetime], stdout=subprocess.PIPE)
	#except:
	#	print('get_stagetimereport_data report error - ' + signal_scn)

	#try:
	#	subprocess.Popen(['php', (UTILS_PATH + "/reports/get_cycletimereport_data.php"), is_cronjob, signal_scn, date, start_datetime, end_datetime], stdout=subprocess.PIPE)
	#except:
	#	print('get_cycletimereport_data report error - ' + signal_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_modeswitchingreport_data.php"), is_cronjob, signal_scn, date], stdout=subprocess.PIPE)
	except:
		print('get_modeswitchingreport_data report error - ' + signal_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_modechangereport_data.php"), is_cronjob, signal_scn, date], stdout=subprocess.PIPE)
	except:
		print('get_modechangereport_data report error - ' + signal_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_planchangereport_data.php"), is_cronjob, signal_scn, date], stdout=subprocess.PIPE)
	except:
		print('get_planchangereport_data report error - ' + signal_scn)
	
	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_eventreport_data.php"), is_cronjob, signal_scn, start_datetime, end_datetime], stdout=subprocess.PIPE)
	except:
		print('get_eventreport_data report error - ' + signal_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_poweronanddownreport_data.php"), is_cronjob, signal_scn, start_datetime, end_datetime], stdout=subprocess.PIPE)
	except:
		print('get_poweronanddownreport_data report error - ' + signal_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_intensitychangereport_data.php"), is_cronjob, signal_scn, start_datetime, end_datetime], stdout=subprocess.PIPE)
	except:
		print('get_intensitychangereport_data report error - ' + signal_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_timeupdatereport_data.php"), is_cronjob, signal_scn, start_datetime, end_datetime], stdout=subprocess.PIPE)
	except:
		print('get_timeupdatereport_data report error - ' + signal_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_lampstatusreport_data.php"), is_cronjob, signal_scn, start_datetime, end_datetime], stdout=subprocess.PIPE)
	except:
		print('get_lampstatusreport_data report error - ' + signal_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_loopfailurereport_data.php"), is_cronjob, signal_scn, start_datetime, end_datetime], stdout=subprocess.PIPE)
	except:
		print('get_loopfailurereport_data report error - ' + signal_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_conflictreport_data.php"), is_cronjob, signal_scn, start_datetime, end_datetime], stdout=subprocess.PIPE)
	except:
		print('get_conflictreport_data report error - ' + signal_scn)

def group_reports(group_scn, date):
        try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_floreport_data.php"), is_cronjob, group_scn, date, start_datetime, end_datetime], stdout=subprocess.PIPE)
	except:
		print('get_floreport_data report error - ' + group_scn)

	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_corridorcycletimereport_data.php"), is_cronjob, group_scn, date], stdout=subprocess.PIPE)
	except:
		print('get_corridorcycletimereport_data report error - ' + group_scn)
'''
	try:
		subprocess.Popen(['php', (UTILS_PATH + "/reports/get_corridorperformancereport_data.php"), is_cronjob, group_scn, date], stdout=subprocess.PIPE)
	except:
		print('get_corridorperformancereport_data report error - ' + group_scn)
'''
ctr = 1
while ctr < 2:
	date = (datetime.datetime.today() - datetime.timedelta(days=ctr)).strftime("%Y-%m-%d")
	start_datetime = (datetime.datetime.today() - datetime.timedelta(days=ctr)).strftime("%Y-%m-%d") + " 00:00:00"
	end_datetime = (datetime.datetime.today() - datetime.timedelta(days=ctr)).strftime("%Y-%m-%d") + " 23:59:59"

	# print date
	# print start_datetime
	# print end_datetime

	pool = Pool(pool_size)
	
	for signal in signals:
		signal_scn = signal[0]
		pool.apply_async(signal_reports, (signal_scn, date, start_datetime, end_datetime))
		time.sleep(120)

	for group in groups:
		group_scn = group[0]
		pool.apply_async(group_reports, (group_scn, date))
		time.sleep(300)

	pool.close()
	pool.join()

	# time.sleep(1200)

	ctr = ctr + 1
os.system("mysqldump -u "+str(DB_USER)+" -h "+str(DB_HOST)+" -p"+str(DB_PASSWORD)+" "+str(DB_NAME_TIM)+" utcReplyTable > /home/localadmin/archives/db/utcReplyTable-"+date+".sql")

cursor.execute("TRUNCATE TABLE tis.utcReplyTable;")
db.commit()
cursor.execute("TRUNCATE TABLE tis.utcControlTable_dummy;")
db.commit()

cursor.close()
db.close()

