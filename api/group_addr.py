# -*- coding: utf-8 -*-

import sys
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
        #if groupid==17:
        #    print 'exit 1';
        #    break
             


def group_new_addr():
    max_group_id = session.execute('select max(group_id) from addr').first()[0]
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
        #if groupid==17:
        #    print 'exit 1';
        #    break

def merge_addr_group():
    import pdb;pdb.set_trace()
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
           tagIdCount=session.execute('select count(1) from addr_tag where id in (select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is not NULL)' % newGroupId).first()[0]
           if tagIdCount==0: #tested
               oldGroupId = session.execute('select distinct group_id, count(1) as c from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is not NULL group by group_id order by c desc limit 1' % newGroupId).first()[0]
               session.execute('update addr set group_id=%d where group_id in (select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id!=%d)' % (oldGroupId, newGroupId, oldGroupId))
               session.execute('update addr set group_id=%d where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is NULL' % (oldGroupId, newGroupId))
               session.execute('delete from addr_group where group_id=%d' % newGroupId)
           elif tagIdCount==1:
               tagGroupId=session.execute('select id from addr_tag where id in (select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is not NULL)' % newGroupId).first()[0]
               session.execute('update addr set group_id=%d where group_id in (select distinct group_id from addr where id in (select distinct addr_id from addr_group where group_id=%d) and group_id!=%d)' % (tagGroupId, newGroupId, tagGroupId))
               session.execute('update addr set group_id=%d where id in (select distinct addr_id from addr_group where group_id=%d) and group_id is NULL' % (tagGroupId,newGroupId))
               session.execute('delete from addr_group where group_id=%d' % newGroupId)
           else:
               print "tagcount %d,  new groupId %d\n" % (tagIdCount,newGroupId)
               session.commit()
               manualGroupIds.append(newGroupId)
               newGroupId = session.execute('select group_id from addr_group where group_id not in (%s) limit 1' % (",".join(str(e) for e in manualGroupIds))).first()[0]
               continue
        session.commit()
        newGroupId = session.execute('select group_id from addr_group where group_id not in (%s) limit 1' % (",".join(str(e) for e in manualGroupIds))).first()[0]

merge_addr_group();
#def merge_addr_group():
#    pass
#    select group_id from addr_group limit 1;
#    select addr_id from addr_group where group_id=38864238;
#    select distinct addr_id from addr_group where group_id=38864238;                                                       
#    select count(distinct addr_id) from addr_group where group_id=38864238;                                                
#    select (distinct addr_id) from addr_group where group_id=38864238;  
#    select distinct group_id from addr where id in (select count(distinct addr_id) from addr_group where group_id=38864238) and group_id is not NULL;
#    select * from addr_tag where id=234561;  
 
# select distinct group_id, count(1) as c from addr where id in (select distinct addr_id from addr_group where group_id=38864238) and group_id is not NULL order by c desc limit 1

if __name__ == "__main__" :                                                                                               
                                                                                                                          
    if len(sys.argv)<2:                                                                                                   
       exit(0)                                                                                                            
    if sys.argv[1]=='first':                                                                                             
        group_addr()
    elif sys.argv[1]=='second':                                                                                               
        group_new_addr()
        merge_addr_group()
