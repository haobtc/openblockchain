# -*- coding: utf-8 -*-

import binascii
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData
from sqlalchemy.dialects.postgresql import BIGINT, BIT, BOOLEAN, BYTEA, INTEGER, BOOLEAN, TEXT
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref
from database import *
import config
import time
import sys
import logging

logging.basicConfig(format='%(asctime)s %(message)s', filename=config.CHECK_LOG_FILE,level=logging.INFO)
console = logging.StreamHandler()  
console.setLevel(logging.DEBUG)  
formatter = logging.Formatter('%(asctime)-12s: %(message)s')  
console.setFormatter(formatter)  
logging.getLogger('').addHandler(console) 

engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
Session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

session=Session()

txhash = sys.argv[1]

logging.info('delete utx hash: %s', txhash)

tx = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()

print tx
if tx is None:
    logging.info('delete utx hash failed, not found: %s', txhash)
    exit(-1)

logging.info('delete utx id: %d', tx.id)
res = UTX.query.filter(UTX.id == tx.id).first()
if res is None:
    logging.info('delete utx hash failed, not utx: %s', txhash)
    exit(-1)

session.execute('select delete_tx(%d)' % res.id)
try:
    session.commit()
except:
    session.rollback()
    logging.exception('delete fail: %s', txhash)
session.close()

