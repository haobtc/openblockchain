# -*- coding: utf-8 -*-

import os
import sys
import signal
import binascii
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData
from sqlalchemy.dialects.postgresql import BIGINT, BIT, BOOLEAN, BYTEA, INTEGER, BOOLEAN, TEXT
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref
from database import *
import config
import logging
import multiprocessing as mul
import time

engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
Session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

session=Session()

#first run this
def group_addr():
    groupid=1;
    while True:
        ida=1
        idb=0
        print '%d \n' % groupid
        count = session.execute('update addr_send s set group_id=0 from (select * from addr_send where group_id is NULL limit 1) sub where s.addr_id=sub.addr_id and s.tx_id=sub.tx_id').rowcount
        if count==0:
           print 'finish \n'
           break
        while True:

            session.execute('insert into addr_group_tmp (select * from addr_send where group_id=%d)' % (idb))
            session.commit()

            #count=session.execute('update addr_send s set group_id=%d from (select a.* from addr_send a join (select distinct addr_id,tx_id from addr_send where group_id=%d) b on(a.addr_id=b.addr_id or a.tx_id=b.tx_id) where a.group_id is NULL) sub where s.addr_id=sub.addr_id and s.tx_id=sub.tx_id' % (ida, idb)).rowcount
            #session.execute("insert into addr_group (select addr_id,tx_id,%d from addr_send where group_id=%d)" % (groupid,idb))
            #session.execute("delete from addr_send where group_id=%d" % idb)
            session.execute("delete from addr_send where group_id=%d" % idb)
            session.commit()
            count1=session.execute('update addr_send set group_id=%d where addr_id in (select distinct addr_id from addr_group_tmp)' % (ida)).rowcount
            count2=session.execute('update addr_send set group_id=%d where tx_id in (select distinct tx_id from addr_group_tmp)' % (ida)).rowcount
            session.execute("insert into addr_group (select addr_id,tx_id,%d from addr_group_tmp)" % (groupid))
            session.commit()
            #print 'count %d' % count;
            #session.execute('truncate table addr_group_tmp')
            session.execute('delete from addr_group_tmp')
            session.commit()
            if count1==0 and count2==0:
                print 'end group id %d\n' % groupid;
                session.commit()
                break
            ida,idb = idb,ida
      
        groupid = groupid + 1

def new_addr_init(max_tx_id=None):
    max_tx_id = session.execute('select max(tx_id) from addr_group').first()[0]
    session.execute('alter table addr_group rename to addr_group_pre')
    #session.execute('delete from addr_group')
    session.execute('delete from addr_group_tmp')
    session.execute('delete from addr_send')
    session.execute('drop MATERIALIZED view group_vout')
    session.commit()
    max_blk_height = session.execute('select max(height)-10 from blk').first()[0]
    session.execute('CREATE MATERIALIZED VIEW group_vout as SELECT g.id as addr_id, e.id AS txin_tx_id FROM txout a LEFT JOIN tx b ON b.id = a.tx_id left join txin c on (c.prev_out=b.hash and c.prev_out_index=a.tx_idx) left JOIN tx e ON e.id = c.tx_id left JOIN addr_txout f on f.txout_id=a.id left JOIN addr g on g.id=f.addr_id where e.id is not NULL and g.id is not NULL and b.id>%d' % maxTxId)
    session.commit()
    session.execute('insert into addr_send select distinct addr_id,txin_tx_id as tx_id from group_vout')
    session.commit()

def group_new_addr(max_group_id=None):
    if max_group_id == None:
        #max_group_id = session.execute('select max(group_id) from addr').first()[0]
        max_group_id = session.execute('select max(group_id) from addr_group').first()[0]
    groupid = max_group_id + 1;
    while True:
        ida=1
        idb=0
        print '%d \n' % groupid
        count = session.execute('update addr_send s set group_id=0 from (select * from addr_send where group_id is NULL limit 1) sub where s.addr_id=sub.addr_id and s.tx_id=sub.tx_id').rowcount
        if count==0:
           print 'finish \n'
           break
        while True:
            session.execute('insert into addr_group_tmp (select * from addr_send where group_id=%d)' % (idb))
            session.commit()

            session.execute("delete from addr_send where group_id=%d" % idb)
            session.commit()
            count1=session.execute('update addr_send set group_id=%d where addr_id in (select distinct addr_id from addr_group_tmp)' % (ida)).rowcount
            count2=session.execute('update addr_send set group_id=%d where tx_id in (select distinct tx_id from addr_group_tmp)' % (ida)).rowcount
            session.execute("insert into addr_group (select addr_id,tx_id,%d from addr_group_tmp)" % (groupid))
            session.commit()
            session.execute('delete from addr_group_tmp')
            session.commit()
            if count1==0 and count2==0:
                print 'end group id %d\n' % groupid;
                session.commit()
                break
            ida,idb = idb,ida
      
        groupid = groupid + 1

def merge_addr_group():
    newGroupId = session.execute('select group_id from addr_group limit 1').first()[0]
    manualGroupIds=[]
    while newGroupId >0: 
        groupCount= session.execute('select count(distinct group_id) from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is not NULL' % newGroupId).first()[0]
        if groupCount == 0: #new addrGroup  #tested
           session.execute('update addr set group_id=%d where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is NULL' % (newGroupId,newGroupId))
           session.execute('delete from addr_group where group_id=%d' % newGroupId)
        elif groupCount == 1:  #old addrGroup and no gruop merge
           oldGroupId=session.execute('select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is not NULL' % newGroupId).first()[0]
           session.execute('update addr set group_id=%d where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is NULL' % (oldGroupId, newGroupId))
           session.execute('delete from addr_group where group_id=%d' % newGroupId)
        else: #need merge old groups
           tagIdCount=session.execute('select count(distinct id) from addr_tag where id in (select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is not NULL)' % newGroupId).first()[0]
           if tagIdCount==0: #tested
               oldGroupId = session.execute('select distinct group_id, count(1) as c from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is not NULL group by group_id order by c desc limit 1' % newGroupId).first()[0]
               session.execute('update addr set group_id=%d where group_id in (select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id!=%d)' % (oldGroupId, newGroupId, oldGroupId))
               session.execute('update addr set group_id=%d where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is NULL' % (oldGroupId, newGroupId))
               session.execute('delete from addr_group where group_id=%d' % newGroupId)
           elif tagIdCount==1:
               tagGroupId=session.execute('select distinct id from addr_tag where id in (select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is not NULL)' % newGroupId).first()[0]
               session.execute('update addr set group_id=%d where group_id in (select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id!=%d)' % (tagGroupId, newGroupId, tagGroupId))
               session.execute('update addr set group_id=%d where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is NULL' % (tagGroupId,tagGroupId))
               session.execute('delete from addr_group where group_id=%d' % newGroupId)
           else:
               print "tagcount %d,  new groupId %d\n" % (tagIdCount,newGroupId)
               session.commit()
               manualGroupIds.append(newGroupId)
               newGroupId = session.execute('select group_id from addr_group where group_id not in (%s) limit 1' % (",".join(str(e) for e in manualGroupIds))).first()[0]
               continue
        session.commit()
        if len(manualGroupIds)>0:
            newGroupId = session.execute('select group_id from addr_group where group_id not in (%s) limit 1' % (",".join(str(e) for e in manualGroupIds))).first()[0]
        else:
            newGroupId = session.execute('select group_id from addr_group limit 1').first()[0]
        if newGroupId == None: #no more addr group
            return


def group_tx(newsession, txId, newGroupId):
       noGroupAddrIds = newsession.execute('select id from addr where id in (select addr_id from vout where txin_tx_id=%d) and group_id is NULL' % txId).fetchall()
       if len(noGroupAddrIds) == 0: #all addr have group_id or no addr in this tx
           return

       addrIds = newsession.execute('select addr_id from vout where txin_tx_id=%d' % txId).fetchall()
       if len(addrIds) == 0: #should not happen,have checed
            return

       addrIdsStr = ', '.join(str(addr_id[0]) for addr_id in addrIds)
       groupIds = newsession.execute('select distinct group_id from addr where id in (%s) and group_id is not NULL' % addrIdsStr).fetchall()
       if len(groupIds) == 0: #new group
            newsession.execute('update addr set group_id=%d where id in (%s)' % (newGroupId, addrIdsStr))
       elif len(groupIds) ==1: #only one old group
            oldGroupId = groupIds[0][0]
            newsession.execute('update addr set group_id=%d where id in (%s)' % (oldGroupId, addrIdsStr))
       else: #len(groupIds) >1 need merge old group
               groupIdsStr = ', '.join(str(groupId[0]) for groupId in groupIds)
               tagIdCount=newsession.execute('select count(distinct id) from addr_tag where id in (%s)' % groupIdsStr).first()[0]
               if tagIdCount==0: # no tag group
                   oldGroupId = groupIds[0][0]

                   #merge old group addr
                   newsession.execute('update addr set group_id=%d where group_id in (%s)' % (oldGroupId, groupIdsStr))
                   newsession.execute('update addr set group_id=%d where id in (%s) and group_id is NULL' % (oldGroupId, addrIdsStr))
               elif tagIdCount==1: #only one group id by taged
                   tagGroupId=newsession.execute('select distinct id from addr_tag where id in (%s)' % groupIdsStr).first()[0]
                   newsession.execute('update addr set group_id=%d where id in (%s) and group_id is NULL' % (tagGroupId, addrIdsStr ))
               else: #more than two group by taged need mannual merge
                   print "tagcount %d,  new groupId %d\n" % (tagIdCount,newGroupId)

#use t_addr_group  table to save midstate to avoid multi update confilt
#CREATE TABLE t_addr_group (addr_id integer NOT NULL, group_id integer not NULL);
def group_tx_new(newsession, txId, newGroupId):
       noGroupAddrIds = newsession.execute('select id from addr where id in (select addr_id from vout where txin_tx_id=%d) and group_id is NULL' % txId).fetchall()
       if len(noGroupAddrIds) == 0: #all addr have group_id or no addr in this tx
           return

       addrIds = newsession.execute('select addr_id from vout where txin_tx_id=%d' % txId).fetchall()
       if len(addrIds) == 0: #should not happen,have checed
            return

       addrIdsStr = ', '.join(str(addr_id[0]) for addr_id in addrIds)
       groupIds = newsession.execute('select distinct group_id from addr where id in (%s) and group_id is not NULL' % addrIdsStr).fetchall()
       if len(groupIds) == 0: #new group
            newsession.execute('insert into t_addr_group (select id,%d from addr where id in (%s))' % (newGroupId, addrIdsStr))
       elif len(groupIds) ==1: #only one old group
            oldGroupId = groupIds[0][0]
            newsession.execute('insert into t_addr_group (select id,%d from addr where id in (%s))' % (oldGroupId, addrIdsStr))
       else: #len(groupIds) >1 need merge old group
               groupIdsStr = ', '.join(str(groupId[0]) for groupId in groupIds)
               tagIdCount=newsession.execute('select count(distinct id) from addr_tag where id in (%s)' % groupIdsStr).first()[0]
               if tagIdCount==0: # no tag group
                   oldGroupId = groupIds[0][0]

                   #merge old group addr
                   newsession.execute('insert into t_addr_group (select id,%d from addr where group_id  in (%s))' % (oldGroupId, groupIdsStr))
                   newsession.execute('insert into t_addr_group (select id,%d from addr where id in (%s) and group_id is NULL)' % (oldGroupId, addrIdsStr))
               elif tagIdCount==1: #only one group id by taged
                   tagGroupId=newsession.execute('select distinct id from addr_tag where id in (%s)' % groupIdsStr).first()[0]
                   newsession.execute('insert into t_addr_group (select id,%d from addr where id in (%s) and group_id is NULL)' % (tagGroupId, addrIdsStr))
               else: #more than two group by taged need mannual merge
                   print "tagcount %d,  new groupId %d\n" % (tagIdCount,newGroupId)


def group_tx_process(newGroupId, minTxId, offset, limit):
    print 'pid is %d, group id is %d, start TxId is %d ' % (os.getpid(), newGroupId, minTxId + offset)
    newengine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
    newSession = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=newengine))
    newsession=newSession()
    txIds = newsession.execute('select id from tx where id >=%d order by id asc offset %d limit %d' % (minTxId, offset, limit)).fetchall()
    if txIds ==None:
       print "finish"
       return
    for txId in txIds:
        group_tx_new(newsession,txId[0], newGroupId )
        newGroupId = newGroupId+1 
    newsession.execute('insert into addr_group_stat (tx_id, group_id) values (%d,%s)' % (txId[0], newGroupId))
    newsession.commit()
    newsession.close()
    newengine.dispose()
    print "finish ", os.getpid() 
 
def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def group_txs(processCount, minTxId=0):
    lastData = session.execute('select group_id,tx_id from addr_group_stat where tx_id=(select max(tx_id) from addr_group_stat)').first()
    if lastData==None:
        return
    maxGroupId = lastData[0]
    if minTxId == 0:
        minTxId = lastData[1]

    newGroupId = maxGroupId + 1;
    limit=100
    i=0

    pool = mul.Pool(processCount, init_worker)
    activieProcessCount=0
    results = []
    while True:
       while activieProcessCount<processCount:
          results.append(pool.apply_async(group_tx_process, args=(newGroupId, minTxId, i*limit, limit)))
          newGroupId = newGroupId+100*i
          activieProcessCount += 1
          i = i+1
       time.sleep(5)
       while True:
           for r in results:
              if (r.ready()):
                 results.remove(r)
                 activieProcessCount -= 1
           if activieProcessCount<processCount:
              break
           time.sleep(1)

       unGroupTxCount = session.execute('select id from tx where id >=%d order by id asc offset %d limit 1' % (minTxId, i*limit)).first()
       if unGroupTxCount ==None:
           pool.close()
           while True:
                if all(r.ready() for r in pool):
                    print "All processes completed"
                    return
                time.sleep(1)
 

def group_txs_single_thread(minTxId):
    maxGroupId = session.execute('select max(group_id) from addr').first()[0]
    newGroupId = maxGroupId + 1;
    i=0
    while True:
       txIds = session.execute('select id from tx where id >=%d order by id asc offset %d limit 100' % (minTxId, 100*i)).fetchall()
       if txIds ==None:
          print "finish"
          return
       for txId in txIds:
           group_tx(session, txId[0], newGroupId )
       session.execute('insert into addr_group_stat (tx_id, group_id) values (%d,%s)' % (txId[0], newGroupId))
       session.commit()
       i = i+1


#39647280
if __name__ == "__main__" :                                                                                               
                                                                                                                          
    if len(sys.argv)<2:                                                                                                   
       exit(0)                                                                                                            
    if sys.argv[1]=='first':                                                                                             
        group_addr()
    elif sys.argv[1]=='second':                                                                                               
        group_new_addr()
    elif sys.argv[1]=='merge':                                                                                               
        merge_addr_group()
    elif sys.argv[1]=='sync':                                                                                               
        if len(sys.argv)<3:                                                                                                   
           exit(0)                                                                                                            
        procCount = int(sys.argv[2])
        print "cpu count is %d, process count is %d" % (mul.cpu_count(), procCount) 
        group_txs(processCount=procCount)
