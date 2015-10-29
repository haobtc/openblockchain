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
from deserialize import extract_public_key
from db2t import db2t_tx, db2t_block

app = Flask(__name__)

page_size=10

from bitcoinrpc.authproxy import AuthServiceProxy


access = AuthServiceProxy(config.RPC_URL)

@app.route("/")
def hello():
    return "Hello World!"

# /queryapi/v2/tx/list
# /queryapi/v1/watch/bitcoin/<group>/addresses/
# /queryapi/v1/tx/details
# /queryapi/v1/watch/bitcoin/<group>/tx/list/
# /queryapi/v1/block/bitcoin/tip
# /queryapi/v1/sendtx/bitcoin

@app.route('/queryapi/v1/watch/bitcoin/<group>/addresses/', methods=['GET', 'POST'])
def watchAddresses(group):
    if group is None or len(group) <= 0:
        return jsonify({"error":"not found"}), 404

    if request.method == 'POST':
        addresses_params = request.form['addresses']

        addressList = addresses_params.split(',')
        print addressList, len(addressList)
        if len(addressList) <= 0:
            return jsonify({"error":"not found"}), 404

        for address in addressList:
            missing = AddrGroup.query.filter_by(address=address, groupname=group).first()
            if missing is None:
                newRecord = AddrGroup()
                newRecord.address = address
                newRecord.groupname = group
                db_session.add(newRecord)
                db_session.flush()
                db_session.refresh(newRecord)
                print newRecord

        return jsonify({"result": "ok"})
    else:
        cursor = request.args.get('cursor') or 0
        cursor = int(cursor)

        count = request.args.get('count') or None
        if count is None or count <=0 or count > 500:
            count = 500

        # getWatchingAddressList(group)
        address_groups = AddrGroup.query.filter_by(groupname=group).offset(cursor).limit(count)

        resp_data = {}
        resp_data['bitcoin.cursor'] = cursor+count
        resp_data['bitcoin'] = [address_group.address for address_group in address_groups]

        print resp_data
        return jsonify(resp_data)


@app.route('/queryapi/v1/watch/bitcoin/<group>/tx/list/', methods=['GET'])
def getWatchingTxList(group):
    if group is None or len(group) <= 0:
        return jsonify({"error":"not found"}), 404

    cursor = request.args.get('cursor') or 0
    cursor = int(cursor)

    count = request.args.get('count') or 0
    count = int(count)
    if count <=0 or count > 2000:
        count = 2000

    address_groups = AddrGroup.query.filter_by(groupname=group).offset(cursor).limit(count)
    for address_group in address_groups:
        address = address_group.address
        addr = Addr.query.filter(Addr.address == address).first()
        if addr == None:
            continue

        txidlist = AddrTx.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id==int(addr.id)).order_by(AddrTx.tx_id.desc()).offset(cursor).limit(count)

    resp_data = {}
    resp_data['bitcoin.cursor'] = cursor+count
    resp_data['bitcoin'] = [txid.tx_id for txid in txidlist]

    print resp_data
    return jsonify(resp_data)

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


@app.route('/queryapi/v1/tx/details', methods=['GET'])
def getTxDetails():
    txhash_params = request.args.get('bitcoin')
    print "txhash_params:",txhash_params
    
    txhashList = txhash_params.split(',')
    print txhashList, len(txhashList)
    if len(txhashList) <= 0:
        return jsonify({"error":"not found"}), 404

    t_txs = []
    for txhash in txhashList:
        tx = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
        if tx:
            t_tx = db2t_tx(tx)
            t_txs.append(t_tx)
        
    if t_txs:
        print t_txs
        # return jsonify(t_txs)
        return Response(json.dumps(t_txs),  mimetype='application/json')
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

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
