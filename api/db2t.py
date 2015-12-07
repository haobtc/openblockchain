#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for,redirect,request,jsonify,Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import simplejson as json
# import json
import binascii
from database import *
from sqlalchemy import and_
from datetime import datetime
from util     import calculate_target, calculate_difficulty,work_to_difficulty
import re
import config
from deserialize import extract_public_key
from bitcoin.core import COIN, str_money_value

def db2t_tx(dtx):
    t = {}

    t["txid"] = dtx.hash
    t["network"] = 'bitcoin'
    t['hash'] = dtx.hash
    t['lock_time']＝dtx.lock_time
    confirm = db_session.execute('select get_confirm(%d)' % dtx.id).first()[0];
    if confirm ==None:
        t['confirmations'] = 0
    else:
        t['confirmations'] =confirm
    
    t['inputs'] = []
    t['outputs'] = []

    blktx = BlockTx.query.filter(BlockTx.tx_id == dtx.id).limit(1).first()
    if blktx != None:
        blkid = blktx.blk_id
        blk = Block.query.filter(Block.id == blkid).limit(1).first()
        if blk:
            t['blockhash'] = blk.hash
            t['blockheight'] = blk.height
            t['blocktime'] = blk.time
            t['time'] = blk.time
            t['blockindex']  = BlockTx.query.filter(BlockTx.blk_id == blkid, BlockTx.tx_id == dtx.id).first().idx
    else:
         t['time'] = dtx.recv_time

    txinlist = TxIn.query.filter(TxIn.tx_id == dtx.id).order_by(TxIn.tx_idx.asc()).all()
    for vin in txinlist:
        inp = {}
        if dtx.coinbase:
            inp['script'] = vin.script_sig
        else:
            inp['hash'] = vin.prev_out
            inp['vout'] = vin.prev_out_index
            inp['script'] = vin.script_sig
            inp['q'] = vin.sequence

            prev_tx = Tx.query.filter(Tx.hash == vin.prev_out.decode('hex')).first()
            if prev_tx:
                prev_txout = TxOut.query.filter(
                    TxOut.tx_id == prev_tx.id,
                    TxOut.tx_idx == vin.prev_out_index).first()
                if prev_txout:
                    inp['address'] = ''
                    address = VOUT.query.with_entities(VOUT.address).filter(and_(VOUT.txout_tx_id==prev_tx.id, VOUT.out_idx==prev_txout.tx_idx)).order_by(VOUT.in_idx).all()
                    for addr in  address: 
                        inp['address'] = inp['address'] + addr[0] + ','
                    inp['address'] =inp['address'][0:-1]
                    inp['amountSatoshi'] = str(prev_txout.value)
                    inp['amount'] = str_money_value(prev_txout.value)
        t['inputs'].append(inp)

    txoutlist = TxOut.query.filter(TxOut.tx_id == dtx.id).order_by(TxOut.tx_idx.asc()).all()
    for vout in txoutlist:
        outp = {}
        outp['address'] = ''
        address = VOUT.query.with_entities(VOUT.address).filter(and_(VOUT.txout_tx_id==dtx.id, VOUT.out_idx==vout.tx_idx)).order_by(VOUT.out_idx).all()
        for addr in address:
            if addr[0] is not None:# http://qukuai.com/tx/d9bdd00b373a92fd64b595263e3ac47841ca3b90ae7f5efdd423865ee3833eda
                outp['address'] = outp['address'] + addr[0] + ',' 
        outp['address'] =outp['address'][0:-1]
        
        outp['amountSatoshi'] = str(vout.value)
        outp['amount'] = str_money_value(vout.value)
        outp['script'] = vout.pk_script
        t['outputs'].append(outp)

    return t

def db2t_block(block):
    b = {}

    b["hash"] = block.hash
    b["version"] = block.version
    b["timestamp"] = block.time
    b["merkle_root"] = block.mrkl_root
    b["height"] = block.height
    b["prev_hash"] = block.prev_hash
    b["tx_cnt"] = block.tx_count
    
    b["confirmations"] = 1
    b["bits"] = block.bits

    block_next = Block.query.filter(Block.prev_hash == block.hash.decode('hex')).limit(1).first()
    if block_next:
        b["nextHash"] = block_next.hash
    return b
