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
from check_db import check_db

app = Flask(__name__)

page_size=10

from bitcoinrpc.authproxy import AuthServiceProxy


access = AuthServiceProxy(config.RPC_URL)

# /queryapi/v2/tx/list
# /queryapi/v1/watch/bitcoin/%s/addresses/
# /queryapi/v1/tx/details
# /queryapi/v1/watch/bitcoin/%s/tx/list/
# /queryapi/v1/block/bitcoin/tip
# /queryapi/v1/sendtx/bitcoin

@app.route('/queryapi/v1/watch/bitcoin/<group>/addresses/', methods=['GET', 'POST'])
def watchAddresses(group):
    pass

@app.route('/queryapi/v1/watch/bitcoin/<group>/tx/list/', methods=['GET'])
def getWatchingTxList(group):
    pass

@app.route('/queryapi/v2/tx/list/', methods=['GET'])
def getRelatedTxIdList():
    cursor = request.args.get('cursor') or 0
    cursor = int(cursor)

    count = request.args.get('count') or None
    if count is None or count <=0 or count > 50:
        count = 50

    addresses_params = request.args.get('addresses')
    print addresses_params

    addressList = addresses_params.split(',')
    print addressList, len(addressList)
    if len(addressList) <= 0:
        return jsonify({"error":"not found"}), 404

    params = ''
    for address in addressList:
        params = params + "'" + address + "',"
    params = params[:-1]   

    print "params, count, cursor", params, count,cursor

    sqlcommand = "SELECT txout_tx_id from vout where address in (%s) ORDER BY txout_tx_id DESC LIMIT %d OFFSET %d" % (params,count,cursor)

    print "sqlcommand:",sqlcommand
    txidlist = engine.execute(text(sqlcommand)).fetchall()
    if txidlist == None:
        return jsonify({"error":"not found"}), 404
    print txidlist

    txHashList = [(Tx.query.with_entities(Tx.hash).filter(Tx.id==txid[0]).first()) for txid in txidlist]
    txHashList = [hexlify(txHash[0]) for txHash in txHashList]
    print "txHashList:", txHashList


    resp_data={}
    resp_data['bitcoin'] = txHashList
    resp_data['bitcoin.cursor'] = cursor+count
    return jsonify(resp_data)


@app.route('/queryapi/v1/tx/details/', methods=['GET'])
def getTxDetails():
    txhash = request.args.get('bitcoin')
    print "txhash:",txhash
    tx = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    print tx
    if tx:
        t_tx = db2t_tx(tx)
        print t_tx
        return jsonify(t_tx)
    else:
        return jsonify({"error":"not found"}), 404

@app.route('/queryapi/v1/block/bitcoin/tip', methods=['GET'])
def getTipBlock():
    block = Block.query.order_by(Block.height.desc()).limit(1).first()
    # print block.id
    # block = Block.query.order_by("height desc").limit(1).first()
    if block:
        t_block = db2t_block(block)
        print t_block
        return jsonify(t_block)
    else:
        return jsonify({"error":"not found"}), 404

@app.route('/queryapi/v1/sendtx/bitcoin/<tx>', methods=['GET', 'POST'])
def sendTx(tx):
    if Tx.query.filter(Tx.hash == stx.hash).limit(1).first():
        raise ttypes.AppException(
            code="tx_exist",
            message="tx already exists in the blockchain")

def db2t_tx(tx):
    t = {}

    t["txid"] = hexlify(tx.hash)

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

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
