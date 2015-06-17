# -*- coding: utf-8 -*-

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData
from sqlalchemy.dialects.postgresql import BIGINT, BIT, BOOLEAN, BYTEA, INTEGER, BOOLEAN
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref

#import logging
#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

engine = create_engine('postgresql://postgres@127.0.0.1:5432/bitcoin',
                       echo=False)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
SQLBase = declarative_base()
SQLBase.query = db_session.query_property()


class database:
    engine = engine
    nettype = 1
    name = 'pq_bitcoin'
    netname = 'bitcoin'

    def __init__(self, netname):
        self.netname = netname


class Block(SQLBase):
    __tablename__ = 'blk'
    id = Column(INTEGER, primary_key=True)
    hash = Column(BYTEA)
    height = Column(INTEGER)
    version = Column(BIGINT)
    prev_hash = Column(BYTEA)
    mrkl_root = Column(BYTEA)
    time = Column(BIGINT)
    bits = Column(BIGINT)
    nonce = Column(BIGINT)
    blk_size = Column(INTEGER)
    chain = Column(INTEGER)
    work = Column(BYTEA)

    def __repr__(self):
        return "<('%s')>" % (self.hash.decode('hex'))


class Tx(SQLBase):
    __tablename__ = 'tx'
    id = Column(INTEGER, primary_key=True)
    hash = Column(BYTEA)
    version = Column(BIGINT)
    lock_time = Column(BIGINT)
    coinbase = Column(BOOLEAN)
    tx_size = Column(BIGINT)
    nhash = Column(BYTEA)

    def __repr__(self):
        return "<('%s')>" % (self.hash.encode('hex'))


class BlockTx(SQLBase):
    __tablename__ = 'blk_tx'
    blk_id = Column(INTEGER, ForeignKey("blk.id"))
    tx_id = Column(INTEGER, ForeignKey("tx.id"))
    idx = Column(INTEGER)
    __table_args__ = (PrimaryKeyConstraint(blk_id, tx_id, idx), )


class TxIn(SQLBase):
    __tablename__ = 'txin'
    id = Column(INTEGER, primary_key=True)
    tx_id = Column(INTEGER, ForeignKey("tx.id"))
    tx_idx = Column(INTEGER)
    prev_out_index = Column(BIGINT)
    sequence = Column(BIGINT)
    script_sig = Column(BYTEA)
    prev_out = Column(BYTEA)
    p2sh_type = Column(INTEGER)


class TxOut(SQLBase):
    __tablename__ = 'txout'
    id = Column(INTEGER, primary_key=True)
    tx_id = Column(INTEGER, ForeignKey("tx.id"))
    tx_idx = Column(INTEGER)
    pk_script = Column(BYTEA)
    value = Column(BIGINT)
    type = Column(INTEGER)
