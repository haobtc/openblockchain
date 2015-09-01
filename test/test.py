#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os 
import sys
import simplejson as json
import binascii
import plyvel
from BCDataStream import *
from deserialize import *
from util import double_sha256

import requests
from database import *
from sqlalchemy import and_

datadir = '/media/fast/btcdata/' #bitcoin data directory
verifystatics =False

def _open_blkindex(datadir):
  try:
    db=plyvel.DB(os.path.join(datadir, 'blocks','index'),compression=None)
  except:
    logging.error("Couldn't open blocks/index.  Try quitting any running Bitcoin apps.")
    sys.exit(1)
  return db
 
db = _open_blkindex(datadir)

def _dump_tx(datadir, tx_hash, tx_pos):
  BLOCK_HEADER_SIZE = 80
  blockfile = open(os.path.join(datadir, "blocks","blk%05d.dat"%(tx_pos[0],)), "rb")
  ds = BCDataStream()
  ds.map_file(blockfile, tx_pos[1]+BLOCK_HEADER_SIZE+tx_pos[2])
  tx = parse_Transaction(ds)
  tx['hash'] = tx_hash[::-1]
  ds.close_file()
  blockfile.close()
  return tx

def _read_CDiskTxPos(stream):
  n_file = stream.read_var_int()
  n_block_pos = stream.read_var_int()
  n_tx_pos = stream.read_var_int()
  return (n_file, n_block_pos, n_tx_pos)
 
def _read_tx(db, txhash):
  kds = BCDataStream()
  vds = BCDataStream()

  key_prefix = "t"+txhash
  cursor = db.iterator(prefix=key_prefix)
  (key, value) = cursor.next()
  kds.clear(); kds.write(key)
  vds.clear(); vds.write(value)

  # Skip the t prefix
  kds.read_bytes(1)
  hash256 = (kds.read_bytes(32))
  tx_pos = _read_CDiskTxPos(vds)
  return _dump_tx(datadir, hash256, tx_pos)
 

def read_tx(txhash):
   return _read_tx(db, txhash)
   
def _parse_block_index(vds):
  d = {}
  d['version'] = vds.read_var_int()
  d['nHeight'] = vds.read_var_int()
  d['nStatus'] = vds.read_var_int()
  d['nTx'] = vds.read_var_int()
  d['nFile'] = vds.read_var_int()
  d['nBlockPos'] = vds.read_var_int()
  d['nUndoPos'] = vds.read_var_int()

  header_start = vds.read_cursor
  d['b_version'] = vds.read_int32()
  d['hashPrev'] = vds.read_bytes(32)
  d['hashMerkle'] = vds.read_bytes(32)
  d['nTime'] = vds.read_var_int()
  d['nBits'] = vds.read_int32()
  d['nNonce'] = vds.read_int32()
  header_end = vds.read_cursor
  d['__header__'] = vds.input[header_start:header_end]
  return d

def _dump_block(datadir, nFile, nBlockPos, blkhash):
  blockfile = open(os.path.join(datadir,"blocks","blk%05d.dat"%(nFile,)), "rb")
  ds = BCDataStream()
  ds.map_file(blockfile, nBlockPos)
  block_start = ds.read_cursor
  block = parse_Block(ds)
  block_end = ds.read_cursor
  block['blk_size'] = (block_end - block_start)
  ds.close_file()
  blockfile.close()
  return block
 

def _read_block(db, blkhash):
  key_prefix = "b"+(blkhash.decode('hex_codec')[::-1])
  cursor = db.iterator(prefix=key_prefix)
  (key, value) = cursor.next()
  vds = BCDataStream()
  vds.clear(); vds.write(value)
  block_data = _parse_block_index(vds)
  block = _dump_block(datadir, block_data['nFile'], block_data['nBlockPos'], blkhash)
  block['hash256'] = blkhash
  block['nHeight'] = block_data['nHeight']
  return block

def read_block(blkhash):
  return _read_block(db, blkhash)

def verifyTxIn(txin1, txin2, coinbase):  

    assert txin1.tx_idx         == txin2['tx_idx']
    #assert txin1.sequence       == txin2['sequence']
    assert txin1.script_sig     == txin2['scriptSig']
    if not coinbase:
        assert txin1.prev_out_index == txin2['prevout_n']
        assert txin1.prev_out       == txin2['prevout_hash'][::-1]

def verifyTxOut(txout1,  txout2):  

    assert txout1.tx_idx    == txout2['tx_idx']
    assert txout1.pk_script == txout2['scriptPubKey']
    assert txout1.value     == txout2['value']
    assert txout1.type      == txout2['scripttype']

def verifyTx(txhash, coinbase):  
    tx1 = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    txhash=txhash.decode('hex_codec')[::-1]
    tx2 = read_tx(txhash)
    
    assert tx1.hash      == tx2['hash']
    assert tx1.version   == tx2['version'] 
    assert tx1.lock_time == tx2['lockTime'] 
    assert tx1.tx_size   == len(tx2['__data__'])

    assert tx1.in_count  == len(tx2['txIn'])
    assert tx1.out_count == len(tx2['txOut'])
    assert tx1.coinbase  == coinbase

    invalue = 0
    for i, txin2 in enumerate(tx2['txIn']):
        txin1 = TxIn.query.filter(and_(TxIn.tx_id == tx1.id, TxIn.tx_idx==i)).first()
        txin2['tx_idx'] = i
        verifyTxIn(txin1, txin2, coinbase)
        prevtx = read_tx(txin2['prevout_hash'])
        invalue += prevtx['txOut'][txin2['prevout_n']]['value'] 
         
    outvalue = 0
    for j, txout2 in enumerate(tx2['txOut']):
        txout1 = TxOut.query.filter(and_(TxOut.tx_id == tx1.id, TxOut.tx_idx==j)).first()
        txout2['tx_idx'] = j
        verifyTxOut(txout1, txout2)
        outvalue += txout2['value']

    assert tx1.out_value == outvalue
    assert tx1.in_value  == invalue
    assert tx1.fee       == (invalue-outvalue)
    return tx1

def verifyBlkTx(tx2,blkid, idx,coinbase):  
    blktx = BlockTx.query.filter(and_(BlockTx.blk_id==blkid, BlockTx.idx==idx)).first()
    tx1 = Tx.query.filter(Tx.id==blktx.tx_id).first()
    
    assert tx1.hash      == double_sha256(tx2['__data__'])[::-1]
    assert tx1.version   == tx2['version'] 
    assert tx1.lock_time == tx2['lockTime'] 
    assert tx1.tx_size   == len(tx2['__data__'])

    assert tx1.in_count  == len(tx2['txIn'])
    assert tx1.out_count == len(tx2['txOut'])
    assert tx1.coinbase  == coinbase

    invalue = 0
    for i, txin2 in enumerate(tx2['txIn']):
        txin1 = TxIn.query.filter(and_(TxIn.tx_id == tx1.id, TxIn.tx_idx==i)).first()
        txin2['tx_idx'] = i
        verifyTxIn(txin1, txin2,coinbase)
        if not coinbase:
            prevtx = read_tx(txin2['prevout_hash'])
            invalue += prevtx['txOut'][txin2['prevout_n']]['value'] 
         
    outvalue = 0
    for j, txout2 in enumerate(tx2['txOut']):
        txout1 = TxOut.query.filter(and_(TxOut.tx_id == tx1.id, TxOut.tx_idx==j)).first()
        txout2['tx_idx'] = j
        verifyTxOut(txout1, txout2)
        outvalue += txout2['value']

    assert tx1.out_value == outvalue
    assert tx1.in_value  == invalue
    if not coinbase:
        assert tx1.fee       == (invalue-outvalue)
    return tx1
 
 
def verifyBlk(blkhash):  

    blk1 = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    blk2 = read_block(blkhash)
    
    assert blk1.hash            == blk2['hash256'].decode('hex')
    assert blk1.height          == blk2['nHeight']
    assert blk1.version         == blk2['version']
    assert blk1.prev_hash       == blk2['hashPrev'][::-1]
    assert blk1.mrkl_root       == blk2['hashMerkleRoot'][::-1]
    assert blk1.time            == blk2['nTime']
    assert blk1.bits            == blk2['nBits']
    #assert blk1.nonce           == blk2['nNonce']
    assert blk1.blk_size        == blk2['blk_size']

    total_in_count  = 0
    total_in_value  = 0
    fees            = 0
    total_out_count = 0
    total_out_value = 0
    tx_count        = 0

    for i,tx in enumerate(blk2['transactions']):
        tx1 = verifyBlkTx(tx,blk1.id,i, i==0)
        total_in_count  +=tx1.in_count
        total_in_value  +=tx1.in_value
        fees            +=tx1.fee
        total_out_count +=tx1.out_count
        total_out_value +=tx1.out_value
        tx_count        +=1

    #assert blk1.work            == blk2['work']
    assert blk1.total_in_count  == total_in_count  
    assert blk1.total_in_value  == total_in_value  
    assert blk1.fees            == fees            
    assert blk1.total_out_count == total_out_count 
    assert blk1.total_out_value == total_out_value 
    assert blk1.tx_count        == tx_count        


def get_addr_info(address):
    result = requests.get('https://blockchain.info/zh-cn/address/%s?format=json' % address)
    return json.loads(result.content)

def verifyAddr(address):  

    addr1 = get_addr_info(address)
    addr2 = Addr.query.filter(Addr.address == address).first()

    assert addr2.address == addr1['address']
    assert addr2.hash160 == addr1['hash160']
    assert addr2.balance == int(addr1['final_balance'])*100000000
     
verifyBlk('000000000000000007b66b3ca329af38380bfd6bed9df8f3fa14d74ddee8d3dc')
verifyTx('aeca55bbeb9495e50500fefcd1e80d4c4aa592f5c277a2a859494ae4b06818a4',False)
verifyAddr('1AytLgGSigqiMGYyy4ces7rSHm7hgCJTv2');

db.close()
