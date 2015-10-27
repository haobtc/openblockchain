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


engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
Session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

session=Session()

expire=time.time()- 24 * 60 * 60
res = db_session.execute('select a.id from utx a join tx b on(b.id=a.id) where b.recv_time<%d' % expire).fetchall()
for tx in res:
    session.execute('select delete_tx(%d)' % tx.id)
    try:
        session.commit()
    except:
        session.rollback()
        logging.exception('delete fail')
session.close()

