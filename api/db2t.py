#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for,redirect,request,jsonify,Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import simplejson as json
# import json
import binascii
from binascii import hexlify
from database import *
from sqlalchemy import and_
from datetime import datetime
from util     import calculate_target, calculate_difficulty,work_to_difficulty
import re
import config
from deserialize import extract_public_key

def db2t_tx(dtx):
    t = {}

    t["txid"] = hexlify(dtx.hash)
    t["network"] = 'bitcoin'
    t['hash'] = hexlify(dtx.hash)
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
            t['blockhash'] = hexlify(blk.hash)
            t['blockheight'] = blk.height
            t['blocktime'] = blk.time
            t['time'] = blk.time
            t['blockindex']  = BlockTx.query.filter(BlockTx.blk_id == blkid, BlockTx.tx_id == dtx.id).first().idx
    else:
         t['time'] = dtx.recv_time

    txinlist = TxIn.query.filter(TxIn.tx_id == dtx.id).all()
    for vin in txinlist:
        inp = {}
        if dtx.coinbase:
            inp['script'] = hexlify(vin.script_sig)
        else:
            inp['hash'] = hexlify(vin.prev_out)
            inp['vout'] = vin.prev_out_index
            inp['script'] = hexlify(vin.script_sig)
            inp['q'] = vin.sequence

            prev_tx = Tx.query.filter(Tx.hash == vin.prev_out).first()
            if prev_tx:
                prev_txout = TxOut.query.filter(
                    TxOut.tx_id == prev_tx.id,
                    TxOut.tx_idx == vin.prev_out_index).first()
                if prev_txout:
                    inp['address'] = ',' + extract_public_key(prev_txout.pk_script)
                    inp['amountSatoshi'] = str(prev_txout.value)
        t['inputs'].append(inp)

    txoutlist = TxOut.query.filter(TxOut.tx_id == dtx.id).all()
    for vout in txoutlist:
        outp = {}
        outp['address'] = ',' + extract_public_key(vout.pk_script)
        outp['amountSatoshi'] = str(vout.value)
        outp['script'] = hexlify(vout.pk_script)
        t['outputs'].append(outp)

    return t

def db2t_block(block):
    b = {}

    b["hash"] = hexlify(block.hash)
    b["version"] = block.version
    b["timestamp"] = block.time
    b["merkle_root"] = hexlify(block.mrkl_root)
    b["height"] = block.height
    b["prev_hash"] = hexlify(block.prev_hash)
    b["tx_cnt"] = block.tx_count
    
    
    b["confirmations"] = 1
    b["bits"] = block.bits

    block_next = Block.query.filter(Block.prev_hash == block.hash).limit(1).first()
    if block_next:
        b["nextHash"] = hexlify(block_next.hash)
    return b
