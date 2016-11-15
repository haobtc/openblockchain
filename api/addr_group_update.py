import os
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
 
from addr_dataset import * 
from AddrGroup import * 

#if first run
first_run = False

session=Session()

#only first run
if first_run:
   os.system('psql -U postgres test -c "truncate table addr_g"')
   create_table()
   create_addr_set()
   addr_group()

r = session.execute('select max(tx_id) as tx_id from addr_send').fetchone()
last_max_tx_id = r.tx_id
print last_max_tx_id 

print "update addr_send table"
update_table()

print "update addr_set"
create_addr_set_update(txid = 0)

print "update addr_set table"
os.system('psql -U postgres test < ' +  config.ADDRESS_SET_UPDATE_SQL)
 
print "update addr_group"
addr_group_update()

print "update addr_g table"
os.system('psql -U postgres test < ' + config.ADDRESS_SET_UPDATE_SQL)
os.system('psql -U postgres test -c "CREATE INDEX addr_g_id_index ON addr_g USING btree (id)"');
os.system('psql -U postgres test -c "CREATE INDEX addr_g_group_id_index ON addr_g USING btree (group_id)"')
os.system('psql -U postgres test -c "create view vaddrg as SELECT a.id, a.group_id AS ogid, b.group_id AS ngid, a.balance, a.spent_count, a.recv_count, a.address FROM addr a LEFT JOIN addr_g b ON b.id = a.id"')

