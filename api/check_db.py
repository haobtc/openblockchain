#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division 
import os 
import sys
import simplejson as json
import binascii
from BCDataStream import *
from deserialize import *
from util import double_sha256, get_ip_address
import time

import requests
from database import *
from sqlalchemy import and_
import logging

from config import *

logging.basicConfig(format='%(asctime)s %(message)s', filename=config.CHECK_LOG_FILE,level=logging.INFO)
console = logging.StreamHandler()  
console.setLevel(logging.DEBUG)  
formatter = logging.Formatter('%(asctime)-12s: %(message)s')  
console.setFormatter(formatter)  
logging.getLogger('').addHandler(console) 

from bitcoinrpc.authproxy import AuthServiceProxy

access = AuthServiceProxy(RPC_URL)

vout_type ={'nonstandard':0, 'pubkey':1, 'pubkeyhash':2, 'scripthash':3, 'multisig':4, 'nulldata':5}
 
def read_tx(txhash):
  return json.loads(access.getrawtransaction(txhash,1))
   
def read_block(blkhash):
  return json.loads(access.getblock(blkhash))

def verifyTxIn(txin1, txin2, coinbase):  

    assert txin1.tx_idx         == txin2['tx_idx']
    assert txin1.sequence       == txin2['sequence']
    if not coinbase:
        assert txin1.script_sig     == txin2['scriptSig']['hex']
        assert txin1.prev_out_index == txin2['vout']
        assert txin1.prev_out       == txin2['txid']

def verifyTxOut(txout1,  txout2):  

    assert txout1.tx_idx    == txout2['n']
    assert txout1.pk_script == txout2['scriptPubKey']['hex']
    assert txout1.value     == round(txout2['value'] * 100000000)
    assert txout1.type      == vout_type[txout2['scriptPubKey']['type']]

def verifyTx(txhash, coinbase):
    logging.debug('verifyTx begin... %s', txhash)
    tx1 = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    tx2 = read_tx(txhash)

    
    assert tx1.hash      == tx2['txid']
    assert tx1.version   == tx2['version'] 
    assert tx1.lock_time == tx2['locktime'] 
    assert tx1.tx_size   == len(tx2['hex'])/2

    assert tx1.in_count  == len(tx2['vin'])
    assert tx1.out_count == len(tx2['vout'])
    assert tx1.coinbase  == (tx2['vin'][0].get("coinbase")!=None)
    coinbase=tx1.coinbase

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

    logging.debug('verifyTx end... %s', txhash)
    return tx1

def verifyBlkTx(txhash,blkid, idx,coinbase): 
    blktx = BlockTx.query.filter(and_(BlockTx.blk_id==blkid, BlockTx.idx==idx)).first()

    tx1 = Tx.query.filter(Tx.id==blktx.tx_id).first()

    tx2 = read_tx(txhash)
    
    assert tx1.hash      == tx2['txid']
    assert tx1.version   == tx2['version'] 
    assert tx1.lock_time == tx2['locktime'] 
    assert tx1.tx_size   == len(tx2['hex'])/2

    assert tx1.in_count  == len(tx2['vin'])
    assert tx1.out_count == len(tx2['vout'])
    assert tx1.coinbase  == (tx2['vin'][0].get("coinbase")!=None)

    coinbase = tx1.coinbase
    
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
    logging.debug('verifyBlk begin... %s', blkhash)
    blk1 = Block.query.filter(Block.hash == blkhash.decode('hex')).first()

    blk2 = read_block(blkhash)
    
    assert blk1.hash            == blk2['hash']
    assert blk1.height          == blk2['height']
    assert blk1.version         == blk2['version']
    assert blk1.prev_hash       == blk2['previousblockhash']
    assert blk1.mrkl_root       == blk2['merkleroot'] 
    assert blk1.time            == blk2['time']
    assert blk1.bits            == int(blk2['bits'],16)
    assert blk1.nonce           == blk2['nonce']
    assert blk1.blk_size        == blk2['size']

    total_in_count  = 0
    total_in_value  = 0
    fees            = 0
    total_out_count = 0
    total_out_value = 0
    tx_count        = 0

    for i,txhash in enumerate(blk2['tx']):
        logging.debug('verifyBlkTx begin... %s:%s', i, txhash)
        tx1 = verifyBlkTx(txhash,blk1.id,i, i==0)
        logging.debug('verifyBlkTx end... %s:%s',  i, txhash)
        total_in_count  +=tx1.in_count
        total_in_value  +=tx1.in_value
        fees            +=tx1.fee
        total_out_count +=tx1.out_count
        total_out_value +=tx1.out_value
        tx_count        +=1

    assert blk1.work            == blk2['chainwork']
    assert blk1.total_in_count  == total_in_count  
    assert blk1.total_in_value  == total_in_value  
    assert blk1.fees            == fees            
    assert blk1.total_out_count == total_out_count 
    assert blk1.total_out_value == total_out_value 
    assert blk1.tx_count        == tx_count        

    logging.debug('verifyBlk end...... %s', blkhash)

    return blkhash

def get_addr_info(address):
    for x in xrange(1,4):
        try:
            result = requests.get('https://blockchain.info/zh-cn/address/%s?format=json' % address)
        except Exception, e:
            print "exception:", e, x
        
        # //Maximum concurrent requests for this endpoint reached. Please try again shortly.
        try:
            return json.loads(result.content)
        except Exception, e:
            print "exception:", e, x
            if x == 3:
                raise
            else:
                time.sleep(5)
    print x
    raise

def verifyAddr(address):  
    print 'verifyAddr begin...',address
    addr1 = get_addr_info(address)
    addr2 = Addr.query.filter(Addr.address == address).first()

    assert addr2.address == addr1['address']
    assert addr2.hash160 == addr1['hash160']
    print addr2.balance, int(addr1['final_balance'])
    assert addr2.balance == int(addr1['final_balance'])
    print 'verifyAddr end...'


#check tx count
def check_tx_count():
    return db_session.execute('select check_tx_count()').first()[0]

#check blk count
def check_blk_count():
    return db_session.execute('select check_blk_count()').first()[0]

#check addr balance
def check_addr_balance():
    if db_session.execute('select id from addr where balance<0 limit 1').rowcount >0:
       return False
    return True

#check last 10 blks
def check_last_block():
    try:
        res = Block.query.with_entities(Block.hash).order_by(Block.height.desc()).limit(10).all()
        for blk in res:
            if not verifyBlk(blk.hash):
                logging.error("check blk fail %s" % blk.hash)
                return False
    except:
        logging.error("check blk exception %s" % blk.hash)
        return False
    return True

#check last 10 txs
def check_last_tx():
    try:
        res = Tx.query.with_entities(Tx.hash).order_by(Tx.id.desc()).limit(10).all()
        for tx in res:
            if not verifyTx(tx.hash, tx.coinbase):
                logging.error("check tx fail %s" % tx.hash)
                return False
    except:
        logging.error("exception check_last_tx:", exc_info=True)

        logging.error("check tx exception %s" % tx.hash)
        return False
    return True

#if alert admin with mail and sms
def sendmail(msg):
    import smtplib

    message = "From: %s\r\nTo: %s\r\nSubject: postgres db check fail!\r\n\r\n%s\r\n" % (config.EMAIL_HOST_USER, ", ".join(config.EMAIL_RECEIVER), msg)
    try:
        smtpserver = smtplib.SMTP(config.EMAIL_HOST)
        smtpserver.set_debuglevel(1)
        smtpserver.ehlo()
        smtpserver.starttls()
        smtpserver.ehlo
        smtpserver.login(config.EMAIL_HOST_USER, config.EMAIL_HOST_PASSWORD)
        smtpserver.sendmail(config.EMAIL_HOST_USER, config.EMAIL_RECEIVER, message)
        smtpserver.quit()  
        smtpserver.close()       
    except:
        logging.error("send mail Fail")


#TODO
def sendsms(msg):
    print msg
    pass

def alter_admin(msg):
    # sendsms(msg)
    sendmail(msg)

def check_db(level=0):
    ip = "debug"
    if config.DEBUG is False:
        ip = get_ip_address(config.NET_PORT)
    msg = time.ctime() + '\n' +  ip +'\n'
    fail = False
    try:
        if level >= 0:
            if not check_tx_count():
               msg = msg + ("check tx count fail\n")
               fail = True
            else:
               msg = msg + ("check tx count success\n")
               
            if not check_blk_count():
               msg = msg + ("check blk count fail\n")
               fail = True
            else:
               msg = msg + ("check blk count success\n")

        if level >= 1:
            if not check_addr_balance():
               msg = msg + ("check address fail\n")
               fail = True
            else:
               msg = msg + ("check address success\n")

        if level >= 2:
            if not check_last_block():
               msg = msg + ("check last blk fail\n")
               fail = True
            else:
               msg = msg + ("check last blk success\n")

            if not check_last_tx():
               msg = msg + ("check last tx fail\n")
               fail = True
            else:
               msg = msg + ("check last tx success\n")

    except Exception, e:
        msg = msg + ("check db fail:\n %s" % e)
        fail = True

    if not fail:
        return {'success': msg}
    else:
        alter_admin(msg)
        return {'fail': msg}

if __name__ == '__main__':
    print check_db(3)
