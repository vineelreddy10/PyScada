# -*- coding: utf-8 -*-

from datetime import timedelta
from datetime import datetime
import os
from time import time, localtime, strftime,mktime
from numpy import float64,float32,int32,uint16,int16,uint8, nan

from pyscada import log
from pyscada.models import Variable
from pyscada.models import RecordedDataFloat
from pyscada.models import RecordedDataInt
from pyscada.models import RecordedDataBoolean
from pyscada.models import InputConfig
from pyscada.models import RecordedTime
from pyscada.models import TaskProgress
from pyscada.export.hdf5 import mat
from django.db import connection


"""
export measurements from the database to a file
"""


def timestamp_unix_to_matlab(timestamp):
    return (timestamp/86400)+719529


def export_database_to_h5(time_id_min=None,filename=None,time_id_max=None):
    tp = TaskProgress(start=time(),label='data export',message='init',timestamp=time())
    tp.save()
    
    if filename is None:
        backup_file_path = os.path.expanduser('~/measurement_data_dumps')
        backup_file_name = 'measurement_data'
        if not os.path.exists(backup_file_path ):
            os.mkdir(backup_file_path)
        cdstr = strftime("%Y_%m_%d_%H%M",localtime())
        filename = os.path.join(backup_file_path,backup_file_name + '_' + cdstr + '.h5')
    
    last_time_id = RecordedTime.objects.last().pk
    first_time_id = RecordedTime.objects.first().pk
    if type(time_id_min) is str:
        timestamp = mktime(datetime.strptime(time_id_min, "%d-%b-%Y %H:%M:%S").timetuple())
        time_id_min = RecordedTime.objects.filter(timestamp__gte=timestamp).first().pk
    if time_id_max is not None:
        last_time_id = min(last_time_id,time_id_max)
    
    if time_id_min is None:
        first_time_id = RecordedTime.objects.filter(timestamp__lte=time()-86460).last().pk
    else:
        first_time_id = max(first_time_id,time_id_min)

    tp.timestamp = time()
    tp.message = 'reading time values from SQL'
    tp.save()
    
    timevalues = [timestamp_unix_to_matlab(element) for element in RecordedTime.objects.filter(id__range = (first_time_id,last_time_id)).values_list('timestamp',flat=True)]
    time_ids = list(RecordedTime.objects.filter(id__range = (first_time_id,last_time_id)).values_list('id',flat=True))
    
    tp.timestamp = time()
    tp.message = 'writing time values to file'
    tp.save()
    
    bf = mat(filename)
    bf.write_data('time',float64(timevalues))
    bf.reopen()
    
    tp.timestamp = time()
    tp.message = 'reading float data values from SQL'
    tp.save()
    
    raw_data = list(RecordedDataFloat.objects.filter(time_id__range = (first_time_id,last_time_id)).values_list('variable_id','time_id','value'))
    
    tp.timestamp = time()
    tp.message = 'reading int data values from SQL'
    tp.save()
    
    raw_data += list(RecordedDataInt.objects.filter(time_id__range = (first_time_id,last_time_id)).values_list('variable_id','time_id','value'))
    
    tp.timestamp = time()
    tp.message = 'reading bool data values from SQL'
    tp.save()
    
    raw_data += list(RecordedDataBoolean.objects.filter(time_id__range = (first_time_id,last_time_id)).values_list('variable_id','time_id','value'))
    
    tp.timestamp = time()
    tp.message = 'prepare raw data'
    tp.save()
    
    data = {}
    for item in raw_data:
        if not data.has_key(item[0]):
            data[item[0]] = []
        data[item[0]].append([item[1],item[2]])
        
    tp.timestamp = time()
    tp.message = 'writing data to file'
    tp.max = Variable.objects.all().count()
    tp.save()
    
    for var in Variable.objects.filter(active = 1):
        tp.timestamp = time()
        tp.message = 'writing value %s to file' %var.variable_name
        tp.progress = tp.progress +1
        tp.save()
        var_id = var.pk
        variable_class = var.value_class
        if data.has_key(var_id):
            records = data[var_id]
        else:
            records = []
        first_record = _last_matching_record(variable_class,first_time_id,var_id)
        if first_record:
            records.insert(0,first_record)
        
        if not first_record and not records:
            continue
        """
        ###################################################################################
        """
        tmp = [0]*len(time_ids)
        t_idx = 0
        v_idx = 0
        nb_v_idx = len(records)-1
        for id in time_ids:
            if nb_v_idx < v_idx: 
                if t_idx > 0:
                    tmp[t_idx] = tmp[t_idx-1]
            else:
                if records[v_idx][0]==id:
                    tmp[t_idx] = records[v_idx][1]
                    laid = id
                    v_idx += 1
                elif t_idx > 0:
                    tmp[t_idx] = tmp[t_idx-1]
    
                if nb_v_idx > v_idx:
                    while records[v_idx][0]<=id and v_idx <= nb_v_idx:
                        log.debug(("double id %d ")%(id))
                        v_idx += 1
            t_idx += 1
                
        if variable_class.upper() in ['FLOAT','FLOAT64','DOUBLE'] :
            tmp = float64(tmp)
        elif variable_class.upper() in ['FLOAT32','SINGLE','REAL'] :
            tmp = float32(tmp)
        elif  variable_class.upper() in ['INT32']:
            tmp = int32(tmp)
        elif  variable_class.upper() in ['WORD','UINT','UINT16']:
            tmp = uint16(tmp)    
        elif  variable_class.upper() in ['INT16','INT']:
            tmp = int16(tmp)
        elif variable_class.upper() in ['BOOL']:
            tmp = uint8(tmp)
        else:
            tmp = float64(tmp)
        
        bf.write_data(var.variable_name,tmp)
        bf.reopen()
        
    tp.timestamp = time()
    tp.message = 'done'
    tp.progress = tp.max
    tp.done = 1
    tp.save()
    """
    end for ###################################################################################
    """
    
    


def export_database_to_mat(time_id_min=None,filename=None,time_id_max=None):
    
    if filename is None:
        backup_file_path = os.path.expanduser('~/measurement_data_dumps')
        backup_file_name = 'measurement_data'
        if not os.path.exists(backup_file_path ):
            os.mkdir(backup_file_path)
        cdstr = strftime("%Y_%m_%d_%H%M",localtime())
        filename = os.path.join(backup_file_path,backup_file_name + '_' + cdstr + '.mat')
    
    last_time_id = RecordedTime.objects.last().pk
    first_time_id = RecordedTime.objects.first().pk
    if type(time_id_min) is str:
        timestamp = mktime(datetime.strptime(time_id_min, "%d-%b-%Y %H:%M:%S").timetuple())
        time_id_min = RecordedTime.objects.filter(timestamp__gte=timestamp).first().pk
    if time_id_max is not None:
        last_time_id = min(last_time_id,time_id_max)
    
    if time_id_min is not None:
        first_time_id = max(first_time_id,time_id_min)


    timevalues = [timestamp_unix_to_matlab(element) for element in RecordedTime.objects.filter(id__range = (first_time_id,last_time_id)).values_list('timestamp',flat=True)]
    time_ids = list(RecordedTime.objects.filter(id__range = (first_time_id,last_time_id)).values_list('id',flat=True))
    
    bf = mat(filename)
    bf.write_data('time',float64(timevalues))
    bf.reopen()
    data = {}

    for var in Variable.objects.filter(value_class__in = ('FLOAT32','SINGLE','FLOAT','FLOAT64','REAL')):
        var_id = var.pk
        variable_class = var.value_class
        r_time_ids = list(RecordedDataFloat.objects.filter(variable_id=var_id,time_id__range = (first_time_id,last_time_id)).values_list('time_id',flat=True))
        r_values = list(RecordedDataFloat.objects.filter(variable_id=var_id,time_id__range = (first_time_id,last_time_id)).values_list('value',flat=True))
        if len(r_values)==0:
            rto = RecordedDataFloat.objects.filter(variable_id=var_id,time_id__lt=first_time_id).last()
            if not rto:
                continue
            r_time_ids = [first_time_id]
            r_values = [rto.value]
        if r_time_ids[0] > first_time_id:
            rto = RecordedDataFloat.objects.filter(variable_id=var_id,time_id__lt=first_time_id).last()
            if rto:
                r_time_ids.insert(0,first_time_id)
                r_values.insert(0,rto.value)
            else:
                r_time_ids.insert(0,first_time_id)
                r_values.insert(0,0)
        _write_to_mat(var.variable_name,variable_class,bf,r_time_ids,r_values,time_ids)
        
    for var in Variable.objects.filter(value_class__in = ('INT32','UINT32','INT16','INT','WORD','UINT','UINT16')):
        var_id = var.pk
        variable_class = var.value_class
        r_time_ids = list(RecordedDataInt.objects.filter(variable_id=var_id,time_id__range = (first_time_id,last_time_id)).values_list('time_id',flat=True))
        r_values = list(RecordedDataInt.objects.filter(variable_id=var_id,time_id__range = (first_time_id,last_time_id)).values_list('value',flat=True))
        if len(r_values)==0:
            rto = RecordedDataInt.objects.filter(variable_id=var_id,time_id__lt=first_time_id).last()
            if not rto:
                continue
            
            r_time_ids = [first_time_id]
            r_values = [rto.value]
        if r_time_ids[0] > first_time_id:
            rto = RecordedDataInt.objects.filter(variable_id=var_id,time_id__lt=first_time_id).last()
            if rto:
                r_time_ids.insert(0,first_time_id)
                r_values.insert(0,rto.value)
            else:
                r_time_ids.insert(0,first_time_id)
                r_values.insert(0,0)
        _write_to_mat(var.variable_name,variable_class,bf,r_time_ids,r_values,time_ids)
    
    for var in Variable.objects.filter(value_class = 'BOOL'):
        var_id = var.pk
        variable_class = var.value_class
        r_time_ids = list(RecordedDataBoolean.objects.filter(variable_id=var_id,time_id__range = (first_time_id,last_time_id)).values_list('time_id',flat=True))
        r_values = list(RecordedDataBoolean.objects.filter(variable_id=var_id,time_id__range = (first_time_id, last_time_id, )).values_list('value',flat=True))
        if len(r_values)==0:
            rto = RecordedDataBoolean.objects.filter(variable_id=var_id,time_id__lt=first_time_id).last()
            if not rto:
                continue
            r_time_ids = [first_time_id]
            r_values = [rto.value]
        if r_time_ids[0] > first_time_id:
            rto = RecordedDataBoolean.objects.filter(variable_id=var_id,time_id__lt=first_time_id).last()
            if rto:
                r_time_ids.insert(0,first_time_id)
                r_values.insert(0,rto.value)
            else:
                r_time_ids.insert(0,first_time_id)
                r_values.insert(0,0)
        _write_to_mat(var.variable_name,variable_class,bf,r_time_ids,r_values,time_ids)
        
    
    bf.close_file()

def _write_to_mat(variable_name,variable_class,bf,r_time_ids,r_values,time_ids):
    tmp = [0]*len(time_ids)
    t_idx = 0
    v_idx = 0
    nb_v_idx = len(r_time_ids)-1
    for id in time_ids:
        if nb_v_idx < v_idx: 
            if t_idx > 0:
                tmp[t_idx] = tmp[t_idx-1]
        else:
            if r_time_ids[v_idx]==id:
                tmp[t_idx] = r_values[v_idx]
                laid = id
                v_idx += 1
            elif t_idx > 0:
                tmp[t_idx] = tmp[t_idx-1]

            if nb_v_idx > v_idx:
                while r_time_ids[v_idx]<=id and v_idx <= nb_v_idx:
                    log.debug(("double id %d ")%(id))
                    v_idx += 1
        t_idx += 1
            
    if variable_class.upper() in ['FLOAT','FLOAT64','DOUBLE'] :
        tmp = float64(tmp)
    elif variable_class.upper() in ['FLOAT32','SINGLE','REAL'] :
        tmp = float32(tmp)
    elif  variable_class.upper() in ['INT32']:
        tmp = int32(tmp)
    elif  variable_class.upper() in ['WORD','UINT','UINT16']:
        tmp = uint16(tmp)    
    elif  variable_class.upper() in ['INT16','INT']:
        tmp = int16(tmp)
    elif variable_class.upper() in ['BOOL']:
        tmp = uint8(tmp)
    else:
        tmp = float64(tmp)
    
    bf.write_data(variable_name,tmp)
    bf.reopen()

def _last_matching_record(variable_class,time_id,variable_id):
    cursor = connection.cursor()
    if variable_class.upper() in ['FLOAT32','SINGLE','FLOAT','FLOAT64','REAL'] :
        item = cursor.execute("SELECT time_id,value FROM pyscada_recordeddatafloat WHERE time_id <= %s AND variable_id = %s ORDER BY time_id DESC LIMIT 1;",[time_id,variable_id])
    elif variable_class.upper() in ['INT32','UINT32','INT16','INT','WORD','UINT','UINT16'] :
        item = cursor.execute("SELECT time_id,value FROM pyscada_recordeddataint WHERE time_id <= %s AND variable_id = %s ORDER BY time_id DESC LIMIT 1;",[time_id,variable_id])
    elif variable_class.upper() in ['BOOL'] :
        item = cursor.execute("SELECT time_id,value FROM pyscada_recordeddataboolean WHERE time_id <= %s AND variable_id = %s ORDER BY time_id DESC LIMIT 1;",[time_id,variable_id])
        #item = cursor.execute("SELECT time_id,value FROM pyscada_recordeddataboolean WHERE id = (SELECT max(id) FROM pyscada_recordeddataboolean WHERE time_id <= %s AND variable_id = %s);",[time_id,variable_id])
    
    else:
        return None
    
    if 1 == item:
        return cursor.fetchone()
    else:
        return None

def _last_matching_records(variable_class,time_id_min,time_id_max,variable_id):
    cursor = connection.cursor()
    if variable_class.upper() in ['FLOAT32','SINGLE','FLOAT','FLOAT64','REAL'] :
        item = cursor.execute("SELECT time_id,value FROM pyscada_recordeddatafloat WHERE time_id > %s AND time_id < %s AND variable_id = %s;",[time_id_min,time_id_max,variable_id])
    elif variable_class.upper() in ['INT32','UINT32','INT16','INT','WORD','UINT','UINT16'] :
        item = cursor.execute("SELECT time_id,value FROM pyscada_recordeddataint WHERE time_id > %s AND time_id < %s AND variable_id = %s;",[time_id_min,time_id_max,variable_id])
    elif variable_class.upper() in ['BOOL'] :
        item = cursor.execute("SELECT time_id,value FROM pyscada_recordeddataboolean WHERE time_id > %s AND time_id < %s AND variable_id = %s;",[time_id_min,time_id_max,variable_id])

    else:
        return None
    
    if item > 0:
        return cursor.fetchall()
    else:
        return None