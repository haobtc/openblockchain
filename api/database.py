# -*- coding: utf-8 -*-

import binascii
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData
from sqlalchemy.dialects.postgresql import BIGINT, BIT, BOOLEAN, BYTEA, INTEGER, BOOLEAN, TEXT
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref

import config

#import logging
#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
db_session = scoped_session(sessionmaker(autocommit=True,
                                         autoflush=False,
                                         bind=engine))
SQLBase = declarative_base()
SQLBase.query = db_session.query_property()

class SBYTEA(TypeDecorator):
    impl = BYTEA 
    def process_result_value(self, value, dialect):
        if value!=None:
	       return binascii.hexlify(value)
        else:
	       return value

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
    __tablename__ = 'v_blk'
    id = Column(INTEGER, primary_key=True)
    hash = Column(SBYTEA)
    height = Column(INTEGER)
    version = Column(BIGINT)
    prev_hash = Column(SBYTEA)
    mrkl_root = Column(SBYTEA)
    time = Column(BIGINT)
    bits = Column(BIGINT)
    nonce = Column(BIGINT)
    blk_size = Column(INTEGER)
    work = Column(SBYTEA)
    total_in_count  = Column(INTEGER)
    total_in_value  = Column(BIGINT)
    fees            = Column(BIGINT)
    total_out_count = Column(INTEGER)
    total_out_value = Column(BIGINT)
    tx_count        = Column(INTEGER) 
    pool_id         = Column(INTEGER) 
    recv_time       = Column(BIGINT) 
    pool_bip        = Column(INTEGER) 
    pool_name       = Column(TEXT) 
    pool_link       = Column(TEXT) 
    bip_name        = Column(TEXT) 
    bip_link        = Column(TEXT) 
    orphan          = Column(BOOLEAN) 

    def todict(self):
        return to_dict(self, self.__class__)

    def __repr__(self):
        return "<('%s')>" % (self.hash.decode('hex'))



class Tx(SQLBase):
    __tablename__ = 'v_tx'
    id = Column(INTEGER, primary_key=True)
    hash = Column(SBYTEA)
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
    removed = Column(BOOLEAN)

    def todict(self):
        return to_dict(self, self.__class__)

    def __repr__(self):
        return "<('%s')>" % (self.hash.encode('hex'))


class BlockTx(SQLBase):
    __tablename__ = 'blk_tx'
    blk_id = Column(INTEGER, ForeignKey("blk.id"))
    tx_id = Column(INTEGER, ForeignKey("v_tx.id"))
    idx = Column(INTEGER)
    __table_args__ = (PrimaryKeyConstraint(blk_id, tx_id, idx), )


class TxIn(SQLBase):
    __tablename__ = 'txin'
    id = Column(INTEGER, primary_key=True)
    tx_id = Column(INTEGER, ForeignKey("v_tx.id"))
    tx_idx = Column(INTEGER)
    prev_out_index = Column(BIGINT)
    sequence = Column(BIGINT)
    script_sig = Column(SBYTEA)
    prev_out = Column(SBYTEA)

    def todict(self):
        return to_dict(self, self.__class__)


class TxOut(SQLBase):
    __tablename__ = 'txout'
    id = Column(INTEGER, primary_key=True)
    tx_id = Column(INTEGER, ForeignKey("v_tx.id"))
    tx_idx = Column(INTEGER)
    pk_script = Column(SBYTEA)
    value = Column(BIGINT)
    type = Column(INTEGER)

    def todict(self):
        return to_dict(self, self.__class__)

class Addr(SQLBase):
    __tablename__ = 'vaddr'
    id = Column(INTEGER, primary_key=True)
    address = Column(TEXT, primary_key=True)
    hash160 = Column(TEXT)
    balance = Column(BIGINT)
    recv_value  = Column(BIGINT)
    recv_count  = Column(INTEGER)  
    spent_value = Column(BIGINT) 
    spent_count = Column(INTEGER)  
    group_id    = Column(INTEGER)  
    tag_name    = Column(TEXT)  
    tag_link   = Column(TEXT)  

    def todict(self):
        return to_dict(self, self.__class__)

class WatchedAddrGroup(SQLBase):
    __tablename__ = 'watched_addr_group'
    id = Column(INTEGER, primary_key=True)
    address = Column(TEXT)
    groupname = Column(TEXT)

    def todict(self):
        return to_dict(self, self.__class__)

    def __repr__(self):
        return "<('%s %s %s')>" % (self.id, self.address, self.groupname)

class WatchedAddrTx(SQLBase):
    __tablename__ = 'watched_addr_tx'
    id = Column(INTEGER, primary_key=True)
    address = Column(TEXT)
    tx = Column(TEXT)

    def todict(self):
        return to_dict(self, self.__class__)

    def __repr__(self):
        return "<('%s %s %s')>" % (self.id, self.address, self.tx)

class SystemCursor(SQLBase):
    __tablename__ = 'system_cursor'
    id = Column(INTEGER, primary_key=True)
    cursor_name = Column(INTEGER)
    cursor_id = Column(TEXT)

    def todict(self):
        return to_dict(self, self.__class__)

    def __repr__(self):
        return "<('%s %s %s')>" % (self.id, self.cursor_name, self.cursor_id)

class AddrTx(SQLBase):
    __tablename__ = 'addr_tx'
    addr_id = Column(INTEGER)
    tx_id = Column(INTEGER)
    __table_args__ = (PrimaryKeyConstraint(addr_id, tx_id), )

    def todict(self):
        return to_dict(self, self.__class__)

class AddrTxN(SQLBase):
    __tablename__ = 'addr_tx_normal'
    addr_id = Column(INTEGER)
    tx_id = Column(INTEGER)
    __table_args__ = (PrimaryKeyConstraint(addr_id, tx_id), )

    def todict(self):
        return to_dict(self, self.__class__)

class AddrTxR(SQLBase):
    __tablename__ = 'addr_tx_removed'
    addr_id = Column(INTEGER)
    tx_id = Column(INTEGER)
    __table_args__ = (PrimaryKeyConstraint(addr_id, tx_id), )

    def todict(self):
        return to_dict(self, self.__class__)

class AddrTxUC(SQLBase):
    __tablename__ = 'addr_tx_unconfirmed'
    addr_id = Column(INTEGER, ForeignKey("addr.id"))
    tx_id = Column(INTEGER)
    __table_args__ = (PrimaryKeyConstraint(addr_id, tx_id), )

    def todict(self):
        return to_dict(self, self.__class__)

class AddrTxC(SQLBase):
    __tablename__ = 'addr_tx_confirmed'
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
    txin_tx_hash = Column(SBYTEA)
    txout_tx_hash = Column(SBYTEA)
    def __init__(self):
        self.txin_tx_hash = binascii.hexlify(self.txin_tx_hash)
        self.txout_tx_hash = binascii.hexlify(self.txout_tx_hash)

    @property
    def todict(self):
        return to_dict(self, self.__class__)

#Materialized view vout for fast search only for txin_count>100 or txout_count>100
class M_VOUT(SQLBase):
    __tablename__ = 'm_vout'
    address = Column(TEXT, primary_key=True)
    addr_id = Column(INTEGER)
    txout_id = Column(INTEGER)
    txin_id = Column(INTEGER)
    txin_tx_id = Column(INTEGER)
    txout_tx_id = Column(INTEGER)
    value = Column(BIGINT)
    in_idx = Column(INTEGER)
    out_idx = Column(INTEGER)
    txin_tx_hash = Column(SBYTEA)
    txout_tx_hash = Column(SBYTEA)
    def __init__(self):
        self.txin_tx_hash = binascii.hexlify(self.txin_tx_hash)
        self.txout_tx_hash = binascii.hexlify(self.txout_tx_hash)

    @property
    def todict(self):
        return to_dict(self, self.__class__)

#spent vout table
class STXO(SQLBase):
    __tablename__ = 'stxo'
    address = Column(TEXT, primary_key=True)
    addr_id = Column(INTEGER)
    txout_id = Column(INTEGER)
    txin_id = Column(INTEGER)
    txin_tx_id = Column(INTEGER)
    txout_tx_id = Column(INTEGER)
    value = Column(BIGINT)
    in_idx = Column(INTEGER)
    out_idx = Column(INTEGER)
    txin_tx_hash = Column(SBYTEA)
    txout_tx_hash = Column(SBYTEA)
    height   = Column(INTEGER) 
    time = Column(BIGINT)
    def __init__(self):
        self.txin_tx_hash = binascii.hexlify(self.txin_tx_hash)
        self.txout_tx_hash = binascii.hexlify(self.txout_tx_hash)

    @property
    def todict(self):
        return to_dict(self, self.__class__)

#vout not in stxo table
class VTXO(SQLBase):
    __tablename__ = 'vtxo'
    address = Column(TEXT, primary_key=True)
    addr_id = Column(INTEGER)
    txout_id = Column(INTEGER)
    txin_id = Column(INTEGER)
    txin_tx_id = Column(INTEGER)
    txout_tx_id = Column(INTEGER)
    value = Column(BIGINT)
    in_idx = Column(INTEGER)
    out_idx = Column(INTEGER)
    txin_tx_hash = Column(SBYTEA)
    txout_tx_hash = Column(SBYTEA)
    height   = Column(INTEGER) 
    time = Column(BIGINT)
    def __init__(self):
        self.txin_tx_hash = binascii.hexlify(self.txin_tx_hash)
        self.txout_tx_hash = binascii.hexlify(self.txout_tx_hash)

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

class POOL(SQLBase):
    __tablename__ = 'pool'
    id = Column(INTEGER, primary_key=True)
    name = Column(TEXT)
    link = Column(TEXT)

    def todict(self):
        return to_dict(self, self.__class__)
 
class ADDR_SEND(SQLBase):
    __tablename__ = 'addr_send'
    addr_id = Column(INTEGER)
    tx_id = Column(INTEGER)
    group_id = Column(INTEGER)
    __table_args__ = (PrimaryKeyConstraint(addr_id, tx_id), )

    def todict(self):
        return to_dict(self, self.__class__)
 

class ADDR_GROUP(SQLBase):
    __tablename__ = 'addr_group'
    addr_id = Column(INTEGER)
    tx_id = Column(INTEGER)
    group_id = Column(INTEGER)
    __table_args__ = (PrimaryKeyConstraint(addr_id, tx_id), )

class AddrTag(SQLBase):
    __tablename__ = 'addr_tag'
    id = Column(INTEGER, primary_key=True)
    addr = Column(TEXT)
    name = Column(TEXT)
    link = Column(TEXT)

    def todict(self):
        return to_dict(self, self.__class__)
 
class JsonCache(SQLBase):
    __tablename__ = 'json_cache'
    key = Column(TEXT, primary_key=True)
    val = Column(TEXT)
