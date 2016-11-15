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

address_set_update = '/tmp/addr_set_update.csv'

def create_table():
    session=Session()
    session.execute('CREATE TABLE addr_send as select distinct addr_id, txin_tx_id as tx_id from stxo where addr_id is not NULL and txin_tx_id is not NULL and addr_id not in (select id from weak_address)')
    session.execute('CREATE INDEX addr_send_tx_id_index ON addr_send USING btree (tx_id)')
    session.commit()
 
def update_table():
    session=Session()
    r = session.execute('select max(tx_id) as tx_id from addr_send').fetchone()
    logging.info('max tx_id is %d' % r.tx_id)
    session.execute('insert into addr_send select distinct addr_id, txin_tx_id as tx_id from stxo where txin_tx_id>%d and addr_id is not NULL and txin_tx_id is not NULL and addr_id not in (select id from weak_address) ' % r.tx_id)
    #remove weaked private key addr
    session.execute('delete from addr_send where addr_id in (select id from weak_address)')
    session.commit()
    return r.tx_id

def create_addr_set(txid = 0):
    session=Session()
    
    r =  session.execute('select max(tx_id) as tx_id from addr_send').fetchone()
    maxTxId =  r.tx_id

    f=open(config.ADDRESS_SET, 'w')
    f.write('DROP TABLE addr_set;\n')
    f.write('CREATE TABLE addr_set(id1 integer, id2 integer, tx_id integer);\n')
    f.write('COPY	addr_set(id1,	id2,	tx_id)	FROM	stdin;\n')

    while txid <= maxTxId :
        r =  session.execute('select * from addr_send where tx_id=%d order by addr_id' % txid).fetchall()
        txid += 1
        if r==None:
            continue
        
        for i,r1 in enumerate(r[:-1]):
            r2 =  r[i+1]
            if r1.addr_id == r2.addr_id:
                continue
            else:
                id1=min(r1.addr_id, r2.addr_id)
                id2=max(r1.addr_id, r2.addr_id)
                f.write('%d	%d	%d\n' % (id1, id2, txid))
    f.write('\.\n')
        
    f.close()
    session.close()

def create_addr_set_update(txid = 0):
    session=Session()
    
    r =  session.execute('select max(tx_id) as tx_id from addr_send').fetchone()
    maxTxId =  r.tx_id

    if txid==0:
        r =  session.execute('select max(tx_id) as tx_id from addr_set').fetchone()
        if r!=None:
            txid =  r.tx_id+1

    print "start txid is %d" % txid
    cs=open(config.ADDRESS_SET_UPDATE, 'w')
    while txid <= maxTxId :
        r =  session.execute('select * from addr_send where tx_id=%d order by addr_id' % txid).fetchall()
        txid += 1
        if r==None:
            continue
        
        for i,r1 in enumerate(r[:-1]):
            r2 =  r[i+1]
            if r1.addr_id == r2.addr_id:
                continue
            else:
                id1=min(r1.addr_id, r2.addr_id)
                id2=max(r1.addr_id, r2.addr_id)
                cs.write('%d,%d\n' % (id1, id2))
    f.write('\.\n')
        
    cs.close()
    session.close()
