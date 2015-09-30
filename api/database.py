# -*- coding: utf-8 -*-

import binascii
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData
from sqlalchemy.dialects.postgresql import BIGINT, BIT, BOOLEAN, BYTEA, INTEGER, BOOLEAN, TEXT
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref

#import logging
#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

engine = create_engine('postgresql://postgres:c1u2u9z@@127.0.0.1:5432/test',
                       echo=False)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
SQLBase = declarative_base()
SQLBase.query = db_session.query_property()

def to_dict(inst, cls):
    """
    dictify the sql alchemy query result.
    """
    d = dict()
    for c in cls.__table__.columns:
        v = getattr(inst, c.name)
        if isinstance(c.type, BYTEA):
            d[c.name] = binascii.hexlify(v)
        elif v is None:
            d[c.name] = ''
        else:
            d[c.name] = v
    return d

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
    work = Column(BYTEA)
    total_in_count  = Column(INTEGER)
    total_in_value  = Column(BIGINT)
    fees            = Column(BIGINT)
    total_out_count = Column(INTEGER)
    total_out_value = Column(BIGINT)
    tx_count        = Column(INTEGER) 

    def todict(self):
        return to_dict(self, self.__class__)

    def __repr__(self):
        return "<('%s')>" % (self.hash.decode('hex'))



class Tx(SQLBase):
    __tablename__ = 'vtx'
    id = Column(INTEGER, primary_key=True)
    hash = Column(BYTEA)
    version = Column(BIGINT)
    lock_time = Column(BIGINT)
    coinbase = Column(BOOLEAN)
    tx_size = Column(BIGINT)
    in_count  = Column(INTEGER)
    in_value  = Column(BIGINT )
    out_count = Column(INTEGER)
    out_value = Column(BIGINT )
    fee       = Column(BIGINT )
    recv_time = Column(BIGINT )
    ip  = Column(TEXT)
    idx  = Column(INTEGER)
    height  = Column(INTEGER)
    time  = Column(BIGINT)

    def todict(self):
        return to_dict(self, self.__class__)

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

    def todict(self):
        return to_dict(self, self.__class__)


class TxOut(SQLBase):
    __tablename__ = 'txout'
    id = Column(INTEGER, primary_key=True)
    tx_id = Column(INTEGER, ForeignKey("tx.id"))
    tx_idx = Column(INTEGER)
    pk_script = Column(BYTEA)
    value = Column(BIGINT)
    type = Column(INTEGER)

    def todict(self):
        return to_dict(self, self.__class__)

class Addr(SQLBase):
    __tablename__ = 'addr'
    id = Column(INTEGER, primary_key=True)
    address = Column(TEXT, primary_key=True)
    hash160 = Column(TEXT)
    balance = Column(BIGINT)
    recv_value  = Column(BIGINT)
    recv_count  = Column(INTEGER)  
    spent_value = Column(BIGINT) 
    spent_count = Column(INTEGER)  

    def todict(self):
        return to_dict(self, self.__class__)
 
class AddrTx(SQLBase):
    __tablename__ = 'addr_tx'
    addr_id = Column(INTEGER, ForeignKey("addr.id"))
    tx_id = Column(INTEGER)
    __table_args__ = (PrimaryKeyConstraint(addr_id, tx_id), )

    def todict(self):
        return to_dict(self, self.__class__)


class VOUT(SQLBase):
    __tablename__ = 'vout'
    address = Column(TEXT, primary_key=True)
    addr_id = Column(INTEGER)
    txout_id = Column(INTEGER)
    txin_id = Column(INTEGER)
    txin_tx_id = Column(INTEGER)
    txout_tx_id = Column(INTEGER)
    value = Column(BIGINT)
    in_idx = Column(INTEGER)
    out_idx = Column(INTEGER)

    @property
    def todict(self):
        return to_dict(self, self.__class__)

class UTXO(SQLBase):
    __tablename__ = 'utxo'
    address = Column(TEXT, primary_key=True)
    addr_id = Column(INTEGER)
    txout_id = Column(INTEGER)
    txin_id = Column(INTEGER)
    txin_tx_id = Column(INTEGER)
    txout_tx_id = Column(INTEGER)
    value = Column(BIGINT)

    @property
    def todict(self):
        return to_dict(self, self.__class__)

class UTX(SQLBase):
    __tablename__ = 'utx'
    id = Column(INTEGER, primary_key=True)
    
    @property
    def todict(self):
        return to_dict(self, self.__class__)

