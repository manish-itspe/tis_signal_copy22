import redis
import sys
import mysql.connector as mysql
sys.path.append('/var/www/html/tis')
from background.config import *
from background.client import sendSocketMessage
import time
from datetime import datetime, timedelta
import json
import os

def subscribe_all():
        global subscriber
        subscriber.subscribe('/tim-detector-data/')
        subscriber.subscribe('/tim-cycle-data/')
        subscriber.subscribe('/tim-queuelength-data/')

def parse_data(channel, data):
        print('parse', channel, data)
        if channel == '/tim-cycle-data/':
                parse_cycle_data(json.loads(data))
        elif channel == '/tim-detector-data/':
                parse_detector_data(json.loads(data))
        elif channel == '/tim-queuelength-data/':
                parse_qlength_data(json.loads(data))

def get_link_names(cur, signal_scn):
        global signal_links_mapping
        if signal_scn not in signal_links_mapping:
                print('call')
                cur.execute("SELECT LinkOrder, LinkName from utmc_traffic_signal_static_links WHERE utmc_traffic_signal_static_links.SignalSCN='{}'".format(signal_scn))
                link_data=cur.fetchall()
                links_mapping={}
                for l in link_data:
                        links_mapping[l[0]] = l[1]
                cur.execute("SELECT StageOrder, group_concat(DISTINCT concat(`utmc_signal_movements`.`from_link`,'-',`utmc_signal_movements`.`to_link`) separator ';') as VehicleMovements from utmc_traffic_signal_stages INNER JOIN `utmc_signal_movements` ON FIND_IN_SET(`utmc_signal_movements`.`id`, REPLACE(TRIM(REPLACE(`utmc_traffic_signal_stages`.`VehicleMovements`, ';', ' ')), ' ', ',')) AND utmc_signal_movements.SignalSCN='{}' WHERE utmc_traffic_signal_stages.SignalSCN='{}' GROUP BY utmc_traffic_signal_stages.StageOrder".format(signal_scn, signal_scn))
                stage_data=cur.fetchall()
                signal_links_mapping[signal_scn] = {}
                for d in stage_data:
                        stage_order = d[0]
                        vm = d[1].split(';')
                        signal_links_mapping[signal_scn][stage_order] = ';'.join([links_mapping[int(v.split('-')[0])]+'-'+links_mapping[int(v.split('-')[1])] for v in vm])
                print(signal_links_mapping[signal_scn])

        return signal_links_mapping

def parse_cycle_data(data):
        try:
                data = json.loads(data['data'])
                signal_scn = data['signal_scn']
                cycle_data = data['data']

                # db = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIS)
                db = mysql.connect(host=DB_HOST,user=DB_USER,password=DB_PASSWORD,db=DB_NAME_TIS)
                cur=db.cursor()

                link_data = get_link_names(cur, signal_scn)

                cur.execute("SELECT CycleNumber FROM atcs_cycletime_report WHERE DATE(StartTime)=CURDATE() AND SignalSCN='{}' ORDER BY StartTime DESC LIMIT 1".format(signal_scn))
                cycle_number = cur.fetchone()
                if cycle_number is None:
                        cycle_number = 1
                else:
                        cycle_number = int(cycle_number[0]) + 1

                cycle_info = {
                        'cycle_time': 0,
                        'stage_timings': '',
                        'saturation': '',
                        'max_cycle_time': 0,
                        'start_time': '',
                        'end_time': '',
                        'provided_timings': ''
                }

                stage_sequence = ''.join([str(x)+',' for x in cycle_data['sequence']])[:-1]
                va_type = int(cycle_data['va_type'])
                for k, sd in cycle_data['stage_data'].items():
                        stage_no = sd['stage']
                        stage_time = sd['stage_time']
                        elapsed_time = sd['elapsed_time']
                        stage_tstamp_ist = datetime.strptime(sd['timestamp'], '%Y-%m-%d %H:%M:%S') + timedelta(seconds=19800)
                        stage_tstamp = stage_tstamp_ist.strftime('%Y-%m-%d %H:%M:%S')
                        max_stage_time = sd['max_time']

                        if cycle_info['start_time'] == '': cycle_info['start_time']=stage_tstamp
                        cycle_info['end_time'] = (stage_tstamp_ist + timedelta(seconds=int(elapsed_time))).strftime('%Y-%m-%d %H:%M:%S')

                        stage_movements = link_data[signal_scn][int(stage_no)] if int(stage_no) in link_data[signal_scn] else '--'
                        cur.execute("INSERT IGNORE INTO atcs_stagetime_report_h1(TimeStamp, StageChanged, SignalSCN, LastUpdated, Movement, StageTime) VALUES ('{}', '{}', '{}', NOW(), '{}', '{}')".format(stage_tstamp, stage_no, signal_scn, stage_movements, elapsed_time))
                        db.commit()

                        cycle_info['cycle_time'] += int(elapsed_time)
                        cycle_info['max_cycle_time'] += int(stage_time) if (va_type == 0 or va_type == 1) else int(max_stage_time)
                        cycle_info['stage_timings'] += (str(elapsed_time) +',') if not sd['interstage'] else ''
                        cycle_info['saturation'] += ('Stage ' + str(stage_no) + ': ' + str(round(int(elapsed_time)/(int(stage_time) if va_type == 0 else int(max_stage_time)), 2)) + ', ') if not sd['interstage'] else ''
                        cycle_info['provided_timings'] += ((str(stage_time) if (va_type == 0 or va_type == 1) else str(max_stage_time)) + ',') if not sd['interstage'] else ''

                cycle_info['stage_timings'] = cycle_info['stage_timings'][:-1]
                cycle_info['saturation'] = cycle_info['saturation'][:-2]
                cycle_info['provided_timings'] = cycle_info['provided_timings'][:-1]
                # print(cycle_info)

                cur.execute("INSERT INTO `atcs_stagetime_report_h2`(`SignalSCN`, `CycleNumber`, `Saturations`, `StageSequence`, `StageTimings`, `Timestamp`, `LastUpdated`, `ProvidedStageTimings`) VALUES ('{}', '{}', '{}', '{}', '{}', '{}', NOW(), '{}')".format(signal_scn, cycle_number, cycle_info['saturation'], stage_sequence, cycle_info['stage_timings'], cycle_info['start_time'], cycle_info['provided_timings']))
                db.commit()

                time_saved = round(((cycle_info['max_cycle_time']-cycle_info['cycle_time']) / cycle_info['max_cycle_time']),4) * 100
                cur.execute("INSERT INTO `atcs_cycletime_report`(`SignalSCN`, `CycleNumber`, `StartTime`, `EndTime`, `StageSequence`, `CycleTime`, `LastUpdated`, `FixedCycleTime`, `TimeSaved`) VALUES ('{}', '{}', '{}', '{}', '{}', '{}', NOW(), '{}', '{}')".format(signal_scn, cycle_number, cycle_info['start_time'], cycle_info['end_time'], stage_sequence, cycle_info['cycle_time'], cycle_info['max_cycle_time'], time_saved))
                db.commit()

                cur.close()
                db.close()
        except Exception as e:
                print('parse cycle data error: ',e)

def parse_detector_data(data):
        try:
                data_timestamp = data['timestamp']
                data = json.loads(data['data'])
                signal_scn = data['signal_scn']
                detector_data = data['data']
                #print(detector_data)
                # db = MySQLdb.connect(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME_TIS)
                db = mysql.connect(host=DB_HOST,user=DB_USER,password=DB_PASSWORD,db=DB_NAME_TIS)
                cur=db.cursor()

                for scn, class_count in detector_data.items():
                        count = sum([int(x) for x in class_count])
                        occ = round(int(count)/300, 4)
                        print(scn, count, class_count, class_count[1])

                        cur.execute("UPDATE utmc_detector_dynamic SET HistoricDate=NOW() WHERE SystemCodeNumber='{}' AND HistoricDate IS NULL".format(scn))
                        db.commit()

                        cur.execute("INSERT INTO `utmc_detector_dynamic`(`SystemCodeNumber`, `TotalFlow`, `FlowInterval`, `Class1Count`, `Class2Count`, `Class3Count`, `Class4Count`, `Class5Count`, `Class6Count`, `Class7Count`, `Class8Count`, `FlowStatus_TypeID`, `Occupancy`, `OccupancyInterval`, `OccupancyStatus_TypeID`, `Speed`, `SpeedInterval`, `SpeedStatus_TypeID`, `QueuePresent`, `QueueSeverity_TypeID`, `Headway`, `HeadwayInterval`, `HeadwayStatus_TypeID`, `LastUpdated`, `HistoricDate`, `Colour`, `Reality`) VALUES ('{}', '{}', 5, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', 0, '{}', 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, NOW(), NULL, NULL, 'Real')".format(scn, str(count), class_count[1], class_count[2], class_count[3], class_count[4], class_count[5], class_count[6], class_count[7], class_count[8], occ))
                        db.commit()

                cur.close()
                db.close()
        except Exception as e:
                print('parse detector data error: ',e)

def parse_qlength_data(data):
        try:
                data = json.loads(data['data'])
                signal_scn = data['signal_scn']
                qlen_data = data['data']

                db = mysql.connect(host=DB_HOST,user=DB_USER,password=DB_PASSWORD,db=DB_NAME_TIS)
                cur=db.cursor()

                cur.execute("SELECT ShortDescription FROM utmc_traffic_signal_static WHERE SignalSCN='"+signal_scn+"'")
                signal_name = cur.fetchone()

                cur.execute("SELECT SystemCodeNumber, ShortDescription FROM utmc_detector_static WHERE SystemCodeNumber LIKE '%"+signal_scn+"%'")
                det_list = cur.fetchall()
                det_map = {}
                for d in det_list:
                        det_map[d[0]] = d[1]

                for scn, qlength in qlen_data.items():
                        ql = round(qlength, 2)

                        cur.execute("INSERT INTO `atcs_queuelength_report`(`SignalSCN`, `SignalName`, `DetectorSCN`, `ApproachName`, `QueueLength`, `TimeStamp`) VALUES ('{}', '{}', '{}', '{}', '{}', NOW())".format(signal_scn, signal_name[0], scn, det_map[scn], str(ql)))
                        db.commit()

        except Exception as e:
                print('parse qlength data error: ', e)

if __name__ == '__main__':
        pid = str(os.getpid())
        pidfile = "/tmp/redis_read_data.pid"
        if os.path.isfile(pidfile):
                sys.exit()
        with open(pidfile, 'w') as fp:
                fp.write(pid)

        try:
                redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_timeout=0.2, socket_connect_timeout=0.2, socket_keepalive=True, retry_on_timeout=True)
                subscriber = redis.pubsub()
                subscribe_all()

                signal_links_mapping={}

                """
                        Maintain status in global vars and fetch from db in case of restart
                """
                # cycle_number={}

                while True:
                        try:
                                message = subscriber.get_message()
                                if message:
                                        channel = message['channel'].decode("utf-8")
                                        data = '' if isinstance(message['data'], int) else message['data'].decode("utf-8")
                                        parse_data(channel, data)
                        except Exception as e:
                                print(e)
                        finally:
                                time.sleep(1)
        except Exception as e:
                print(e)
        finally:
                os.unlink(pidfile)

