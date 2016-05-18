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
import logging

engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
Session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

session=Session()

while True:
    res = UTX.query.first()
    if res!=None:
        session.execute('select delete_some_utx()')
        try:
            session.commit()
        except:
            session.rollback()
            logging.exception('delete fail')
    else:
        break
session.close()

