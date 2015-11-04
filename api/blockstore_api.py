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
import logging

logging.basicConfig(format='%(asctime)s %(message)s', filename=config.BLOCKSTORE_LOG_FILE,level=logging.INFO)
console = logging.StreamHandler()  
console.setLevel(logging.DEBUG)  
formatter = logging.Formatter('%(asctime)-12s: %(message)s')  
console.setFormatter(formatter)  
logging.getLogger('').addHandler(console) 
app = Flask(__name__)

page_size=10

from bitcoinrpc.authproxy import AuthServiceProxy,JSONRPCException


access = AuthServiceProxy(config.RPC_URL)

@app.route("/")
def hello():
    return "Hello Blockstore!"

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
            missing = WatchedAddrGroup.query.filter_by(address=address, groupname=group).first()
            if missing is None:
                newRecord = WatchedAddrGroup()
                newRecord.address = address
                newRecord.groupname = group
                db_session.add(newRecord)
                db_session.flush()
                db_session.refresh(newRecord)
                print newRecord
                watch_addrtx(address, 0)   
        return jsonify({"result": "ok"})
    else:
        cursor = request.args.get('cursor') or 0
        cursor = int(cursor)

        count = request.args.get('count') or 0
        count = int(count)
        if count <=0 or count > 500:
            count = 500

        # getWatchingAddressList(group)
        address_groups = WatchedAddrGroup.query.order_by(WatchedAddrGroup.id).filter_by(groupname=group).offset(cursor).limit(count)

        resp_data = {}
        resp_data['bitcoin.cursor'] = str(cursor+address_groups.count())
        resp_data['bitcoin'] = [address_group.address for address_group in address_groups]

        print resp_data
        return jsonify(resp_data)


def watch_addrtxs():
    system_cursor = SystemCursor.query.filter_by(cursor_name = 'watch_addrtx_cursor').first()
    if system_cursor is None:
        cursor_id = 0
    else:
        cursor_id = system_cursor.cursor_id

    new_cursors = []
    address_groups = WatchedAddrGroup.query.all()
    for address_group in address_groups:
        new_cursor = watch_addrtx(address_group.address, cursor_id)
        if new_cursor is not None:
            new_cursors.append(new_cursor)

    if len(new_cursors) == 0:
        return

    next_cursor =  min(new_cursors)
    print 'next_cursor:',next_cursor
    if system_cursor is None:
        system_cursor = SystemCursor()
        system_cursor.cursor_name = 'watch_addrtx_cursor'
        system_cursor.cursor_id = next_cursor
        db_session.add(system_cursor)
        db_session.flush()
        db_session.refresh(system_cursor)
    else:
        system_cursor.cursor_id = next_cursor
        db_session.flush()
        db_session.refresh(system_cursor)

def watch_addrtx(address, cursor_id):
    addr_id = Addr.query.with_entities(Addr.id).filter(Addr.address == address).first()
    if addr_id == None:
        return None
    print addr_id

    txidlist=AddrTx.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id == addr_id).filter(AddrTx.tx_id > cursor_id).all()
    if txidlist == None or len(txidlist) == 0:
        return None

    print "txidlist:", len(txidlist), txidlist

    txHashList = [(Tx.query.with_entities(Tx.hash).filter(Tx.id==txid[0]).first()) for txid in txidlist]

    txHashList = [hexlify(txHash[0]) for txHash in txHashList]
    print "txHashList:", txHashList
    for txHash in txHashList:
        missing = WatchedAddrTx.query.filter_by(address=address, tx=txHash).first()
        if missing is None:
            newRecord = WatchedAddrTx()
            newRecord.address = address
            newRecord.tx = txHash
            db_session.add(newRecord)
            db_session.flush()
            db_session.refresh(newRecord)

    max_txid =  max(txid[0] for txid in txidlist)
    return max_txid


@app.route('/queryapi/v1/watch/bitcoin/<group>/tx/list/', methods=['GET'])
def getWatchingTxList(group):
    if group is None or len(group) <= 0:
        return jsonify({"error":"not found"}), 404

    cursor = request.args.get('cursor') or 0
    cursor = int(cursor)

    count = request.args.get('count') or 0
    count = int(count)
    if count <=0 or count > 500:
        count = 500

    txHashlist = []

    watchedAddrTxs = WatchedAddrTx.query.order_by(WatchedAddrTx.id).offset(cursor).limit(count)
    
    resp_data = {}
    resp_data['bitcoin.cursor'] = str(cursor+watchedAddrTxs.count())
    for watchedAddrTx in watchedAddrTxs:
        address_group = WatchedAddrGroup.query.filter_by(groupname=group, address=watchedAddrTx.address).first()
        if address_group is not None:
            if watchedAddrTx.tx not in txHashlist:
                txHashlist.append(watchedAddrTx.tx)
    
    resp_data['bitcoin'] = txHashlist

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
    print len(addressList), addressList
    if len(addressList) <= 0:
        return jsonify({"error":"not found"}), 404

    print "count, cursor", count,cursor

    addridlist = Addr.query.with_entities(Addr.id).filter(Addr.address.in_(addressList)).all()
    if addridlist == None:
        resp_data={}
        return jsonify(resp_data)
    print addridlist

    txidlist=AddrTx.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id.in_(addridlist)).order_by(AddrTx.tx_id).offset(cursor).limit(count)

    resp_data={}
    resp_data['bitcoin.cursor'] = str(cursor+txidlist.count())

    txHashList = [(Tx.query.with_entities(Tx.hash).filter(Tx.id==txid[0]).first()) for txid in txidlist]
    txHashList = [hexlify(txHash[0]) for txHash in txHashList]
    print "txHashList:", txHashList

    resp_data['bitcoin'] = txHashList

    print resp_data
    return jsonify(resp_data)


@app.route('/queryapi/v1/tx/details', methods=['GET'])
def getTxDetails():
    txhash_params = request.args.get('bitcoin')
    
    txhashList = txhash_params.split(',')
    print len(txhashList),txhashList
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

from bitcoinrpc.authproxy import AuthServiceProxy
access = AuthServiceProxy(config.RPC_URL)

def sendrawtransaction(rawtx, allowhighfees = False):
    return json.loads(access.sendrawtransaction(rawtx,allowhighfees))
def decoderawtransaction(rawtx):
    return json.loads(access.decoderawtransaction(rawtx))

@app.route('/queryapi/v1/sendtx/bitcoin', methods=['GET', 'POST'])
def sendTx():
    if request.method == 'POST':
        rawtx = request.form['rawtx']
        print "rawtx:",rawtx
        try:
            r = decoderawtransaction(rawtx)
            txhash = r['txid']
            logging.INFO("txhash:%s", txhash) 
            tx = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
            if tx:
                logging.INFO("tx already exists in the blockchain")
                return jsonify({"code":"tx_exist", "error": "tx already exists in the blockchain"}), 400     
            else:
                txid = sendrawtransaction(rawtx, False)
                logging.INFO("txid:%s", txid)
                return jsonify({"txid":txid})
        except JSONRPCException,e:
            print "JSONRPCException:",e.error
            return jsonify({"error": e.error}), 400   
        except Exception, e:
            print "Exception:",e
            return jsonify({"error":"send Failed"}), 400      

if __name__ == '__main__':
    app.run(host=config.BLOCKSTORE_HOST, port=config.BLOCKSTORE_PORT, debug=config.DEBUG)
