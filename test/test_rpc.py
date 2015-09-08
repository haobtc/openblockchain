#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division 
import os 
import sys
import simplejson as json
import binascii
from BCDataStream import *
from deserialize import *
from util import double_sha256

import requests
from database import *
from sqlalchemy import and_

from bitcoinrpc.authproxy import AuthServiceProxy

RPC_URL = "http://bitcoinrpc:A4MjCQEiCyMeK9b3w2aLL2P5m1wGaHFXV25TLPjM4yoS@127.0.0.1:8332"
access = AuthServiceProxy(RPC_URL)


vout_type ={'nonstandard':0, 'pubkey':1, 'pubkeyhash':2, 'scripthash':3, 'multisig':4, 'nulldata':5}
 
def read_tx(txhash):
  return json.loads(access.getrawtransaction(txhash,1))
   
def read_block(blkhash):
  return json.loads(access.getblock(blkhash))

def verifyTxIn(txin1, txin2, coinbase):  

    assert txin1.tx_idx         == txin2['tx_idx']
    #assert txin1.sequence       == txin2['sequence']
    if not coinbase:
        assert txin1.script_sig     == txin2['scriptSig']['hex'].decode('hex')
        assert txin1.prev_out_index == txin2['vout']
        assert txin1.prev_out       == txin2['txid'].decode('hex')

def verifyTxOut(txout1,  txout2):  

    assert txout1.tx_idx    == txout2['n']
    assert txout1.pk_script == txout2['scriptPubKey']['hex'].decode('hex')
    assert txout1.value     == round(txout2['value'] * 100000000)
    assert txout1.type      == vout_type[txout2['scriptPubKey']['type']]

def verifyTx(txhash, coinbase):  
    tx1 = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    tx2 = read_tx(txhash)
    
    assert tx1.hash      == tx2['txid'].decode('hex')
    assert tx1.version   == tx2['version'] 
    assert tx1.lock_time == tx2['locktime'] 
    assert tx1.tx_size   == len(tx2['hex'])/2

    assert tx1.in_count  == len(tx2['vin'])
    assert tx1.out_count == len(tx2['vout'])
    assert tx1.coinbase  == coinbase

    invalue = 0
    for i, txin2 in enumerate(tx2['vin']):
        txin1 = TxIn.query.filter(and_(TxIn.tx_id == tx1.id, TxIn.tx_idx==i)).first()
        txin2['tx_idx'] = i
        verifyTxIn(txin1, txin2, coinbase)
        prevtx = read_tx(txin2['txid'])
        invalue += prevtx['vout'][txin2['vout']]['value'] 
         
    outvalue = 0
    for j, txout2 in enumerate(tx2['vout']):
        txout1 = TxOut.query.filter(and_(TxOut.tx_id == tx1.id, TxOut.tx_idx==j)).first()
        verifyTxOut(txout1, txout2)
        outvalue += txout2['value']

    assert tx1.out_value == round(outvalue * 100000000)
    assert tx1.in_value  == round(invalue  * 100000000) 
    assert tx1.fee       == round((invalue  * 100000000) -(outvalue * 100000000))
    return tx1

def verifyBlkTx(txhash,blkid, idx,coinbase):  
    blktx = BlockTx.query.filter(and_(BlockTx.blk_id==blkid, BlockTx.idx==idx)).first()
    tx1 = Tx.query.filter(Tx.id==blktx.tx_id).first()
    tx2 = read_tx(txhash)
    
    assert tx1.hash      == tx2['txid'].decode('hex')
    assert tx1.version   == tx2['version'] 
    assert tx1.lock_time == tx2['locktime'] 
    assert tx1.tx_size   == len(tx2['hex'])/2

    assert tx1.in_count  == len(tx2['vin'])
    assert tx1.out_count == len(tx2['vout'])
    assert tx1.coinbase  == (tx2['vin'][0].get("coinbase")!=None)

    invalue = 0
    for i, txin2 in enumerate(tx2['vin']):
        txin1 = TxIn.query.filter(and_(TxIn.tx_id == tx1.id, TxIn.tx_idx==i)).first()
        txin2['tx_idx'] = i
        verifyTxIn(txin1, txin2,coinbase)
        if not coinbase:
            prevtx = read_tx(txin2['txid'])
            invalue += prevtx['vout'][txin2['vout']]['value'] 
         
    outvalue = 0
    for j, txout2 in enumerate(tx2['vout']):
        txout1 = TxOut.query.filter(and_(TxOut.tx_id == tx1.id, TxOut.tx_idx==j)).first()
        verifyTxOut(txout1, txout2)
        outvalue += txout2['value']

    assert tx1.out_value == round(outvalue * 100000000)
    assert tx1.in_value  == round(invalue  * 100000000)
    if not coinbase:
        assert tx1.fee       == round((invalue  * 100000000) -(outvalue * 100000000))
    return tx1
 
 
def verifyBlk(blkhash):  

    blk1 = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    blk2 = read_block(blkhash)
    
    assert blk1.hash            == blk2['hash'].decode('hex')
    assert blk1.height          == blk2['height']
    assert blk1.version         == blk2['version']
    assert blk1.prev_hash       == blk2['previousblockhash'].decode('hex') 
    assert blk1.mrkl_root       == blk2['merkleroot'].decode('hex')  
    assert blk1.time            == blk2['time']
    assert blk1.bits            == int(blk2['bits'],16)
    assert blk1.nonce           == blk2['nNonce']
    assert blk1.blk_size        == blk2['size']

    total_in_count  = 0
    total_in_value  = 0
    fees            = 0
    total_out_count = 0
    total_out_value = 0
    tx_count        = 0

    for i,txhash in enumerate(blk2['tx']):
        tx1 = verifyBlkTx(txhash,blk1.id,i, i==0)
        total_in_count  +=tx1.in_count
        total_in_value  +=tx1.in_value
        fees            +=tx1.fee
        total_out_count +=tx1.out_count
        total_out_value +=tx1.out_value
        tx_count        +=1

    assert blk1.work            == blk2['chainwork'].decode('hex')
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
    assert addr2.balance == int(addr1['final_balance'])

verifyBlk('000000000000000007b66b3ca329af38380bfd6bed9df8f3fa14d74ddee8d3dc')
verifyTx('aeca55bbeb9495e50500fefcd1e80d4c4aa592f5c277a2a859494ae4b06818a4',False)
verifyAddr('1AytLgGSigqiMGYyy4ces7rSHm7hgCJTv2');
