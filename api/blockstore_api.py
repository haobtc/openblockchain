#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for,redirect,request,jsonify,Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text, func
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
from db2t import db2t_tx, db2t_block
import logging

# logging.basicConfig(format='%(asctime)s %(message)s', filename=config.BLOCKSTORE_API_LOG_FILE,level=logging.INFO)
# console = logging.StreamHandler()  
# console.setLevel(logging.DEBUG)  
# formatter = logging.Formatter('%(asctime)-12s: %(message)s')  
# console.setFormatter(formatter)  
# logging.getLogger('').addHandler(console)
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

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
        logging.info("watchAddresses length:%s %s", len(addressList),addressList)
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
                logging.info("watchAddresses newRecord: %s %s", address, group)
                watch_addrtx(address, 0, False)   
        return jsonify({"result": "ok"})
    else:
        cursor = request.args.get('cursor') or 0
        cursor = int(cursor)
        if cursor < 0:
            cursor = 0

        count = request.args.get('count') or 0
        count = int(count)
        if count <=0 or count > 500:
            count = 500
    
        logging.debug("watchAddresses cursor, count: %s,%s", cursor, count)
        address_groups = WatchedAddrGroup.query.order_by(WatchedAddrGroup.id).filter_by(groupname=group).offset(cursor).limit(count)

        resp_data = {}
        resp_data['bitcoin.cursor'] = str(cursor+address_groups.count())
        resp_data['bitcoin'] = [address_group.address for address_group in address_groups]

        logging.debug("watchAddresses resp_data: %s", resp_data)
        return jsonify(resp_data)


def watch_addrtxs(verify):
    system_cursor = SystemCursor.query.filter_by(cursor_name = 'watch_addrtx_cursor').first()
    if system_cursor is None:
        cursor_id = 0
    else:
        cursor_id = system_cursor.cursor_id

    logging.info("watch_addrtx_cursor:%s %s", verify, cursor_id)

    new_cursors = []
    address_groups = WatchedAddrGroup.query.all()
    for address_group in address_groups:
        new_cursor = watch_addrtx(address_group.address, cursor_id, verify)
        if new_cursor is not None:
            new_cursors.append(new_cursor)

    if len(new_cursors) == 0:
        return

    if verify:
        return

    next_cursor =  min(new_cursors)
    logging.info("watch_addrtx_cursor next_cursor:%s %s %s", next_cursor,len(new_cursors),new_cursors)
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

def watch_addrtx(address, cursor_id, verify):
    addr_id = Addr.query.with_entities(Addr.id).filter(Addr.address == address).first()
    if addr_id == None:
        return None

    logging.debug("watch_addrtx addr_id,cursor_id: %s %s,%s, %s", verify, address, addr_id, cursor_id)
    if verify:
        txidlist=AddrTx.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id == addr_id).filter(AddrTx.tx_id <= cursor_id).all()
    else:
        txidlist=AddrTx.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id == addr_id).filter(AddrTx.tx_id > cursor_id).all()
    if txidlist == None or len(txidlist) == 0:
        return None

    logging.debug("watch_addrtx txidlist: %s %s %s %s", verify, address, len(txidlist), txidlist)

    txHashList = [(Tx.query.with_entities(Tx.hash).filter(Tx.id==txid[0]).first()) for txid in txidlist]

    txHashList = [txHash[0] for txHash in txHashList]
    logging.debug("watch_addrtx txHashList: %s %s %s %s", verify, address, len(txHashList), txHashList)
    for txHash in txHashList:
        missing = WatchedAddrTx.query.filter_by(address=address, tx=txHash).first()
        if missing is None:
            logging.info("watch_addrtx new tx: %s %s %s", verify, address, txHash)

            newRecord = WatchedAddrTx()
            newRecord.address = address
            newRecord.tx = txHash
            db_session.add(newRecord)
            db_session.flush()
            db_session.refresh(newRecord)

    max_txid =  max(txid[0] for txid in txidlist)

    logging.info("watch_addrtx max_txid: %s %s %s", verify, address, max_txid)

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

    logging.debug("getWatchingTxList resp_data: %s", resp_data)

    return jsonify(resp_data)


@app.route('/queryapi/v2/tx/list/', methods=['GET'])
def getRelatedTxIdList():
    cursor = request.args.get('cursor') or 0
    cursor = int(cursor)

    count = request.args.get('count') or None
    if count is None or count <=0 or count > 50:
        count = 50

    addresses_params = request.args.get('addresses')

    addressList = addresses_params.split(',')
    logging.info("getRelatedTxIdList addressList:%s %s",len(addressList), addressList)
    if len(addressList) <= 0:
        return jsonify({"error":"not found"}), 404

    logging.info("getRelatedTxIdList tx count, cursor %s %s", count,cursor)

    addridlist = Addr.query.with_entities(Addr.id).filter(Addr.address.in_(addressList)).all()
    if  addridlist:
        txidlist=list(AddrTx.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id.in_(addridlist)).order_by(AddrTx.tx_id).offset(cursor).limit(count))
    else:
        txidlist=[]

    logging.info("getRelatedTxIdList addridlist:%s %s",len(addridlist), addridlist)

    resp_data={}
    resp_data['bitcoin.cursor'] = str(cursor+len(txidlist))

    txHashList = [(Tx.query.with_entities(Tx.hash).filter(Tx.id==txid[0]).first()) for txid in txidlist]
    txHashList = [txHash[0] for txHash in txHashList]

    resp_data['bitcoin'] = txHashList

    logging.info("getRelatedTxIdList resp_data: %s", resp_data)

    return jsonify(resp_data)


@app.route('/queryapi/v1/tx/details', methods=['GET'])
def getTxDetails():
    txhash_params = request.args.get('bitcoin')
    
    txhashList = txhash_params.split(',')
    logging.debug("getTxDetails:%s %s", len(txhashList),txhashList)
    if len(txhashList) <= 0:
        return jsonify({"error":"not found"}), 404

    t_txs = []
    for txhash in txhashList:
        tx = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
        if tx:
            t_tx = db2t_tx(tx)
            t_txs.append(t_tx)
        
    logging.info("getTxDetails: %s %s ,resp_data: %s %s", len(txhashList),txhashList, len(t_txs), t_txs)
    # return jsonify(t_txs)
    return Response(json.dumps(t_txs),  mimetype='application/json')

@app.route('/queryapi/v1/block/bitcoin/tip', methods=['GET'])
def getTipBlock():
    block = Block.query.order_by(Block.height.desc()).limit(1).first()
    # block = Block.query.order_by("height desc").limit(1).first()
    if block:
        t_block = db2t_block(block)
        logging.debug("tip: %s", t_block)
        return jsonify(t_block)
    else:
        return jsonify({"error":"not found"}), 404


def sendrawtransaction(rawtx, allowhighfees = False):
    return json.loads(access.sendrawtransaction(rawtx,allowhighfees))
def decoderawtransaction(rawtx):
    return json.loads(access.decoderawtransaction(rawtx))

@app.route('/queryapi/v1/sendtx/bitcoin', methods=['GET', 'POST'])
def sendTx():
    if request.method == 'POST':
        rawtx = request.form['rawtx']
        logging.info("rawtx:%s", rawtx)
        try:
            r = decoderawtransaction(rawtx)
            txhash = r['txid']
            logging.info("txhash:%s", txhash) 
            tx = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
            if tx:
                logging.info("tx already exists in the blockchain")
                return jsonify({"code":"tx_exist", "error": "tx already exists in the blockchain"}), 400     
            else:
                txid = sendrawtransaction(rawtx, False)
                logging.info("txid:%s", txid)
                return jsonify({"txid":txid})
        except JSONRPCException,e:
            logging.info("JSONRPCException: %s",e.error)
            return jsonify({"error": e.error}), 400   
        except:
            logging.info("exception send raw tx:", exc_info=True)
            # re-init the connection
            access = AuthServiceProxy(config.RPC_URL)
            return jsonify({"error":"rpc send exception"}), 400      

        return jsonify({"error":"send Failed"}), 400      

def new_watch_addrtxs(verify):
    if verify:
        return new_watch_addrtxs_verify()
    else:
        return new_watch_addrtxs_normal()

#从0扫描到watch_addrtx_cursor位置，并使用自己的watch_addrtx_cursor_verify下标，这样可以重启多次使用
def new_watch_addrtxs_verify():
    normal_cursor = SystemCursor.query.filter_by(cursor_name='watch_addrtx_cursor').first()
    if not normal_cursor:
        return False
    normal_cursor_id = normal_cursor.cursor_id

    verify_cursor = SystemCursor.query.filter_by(cursor_name='watch_addrtx_cursor_verify').first()
    if not verify_cursor:
        verify_cursor_id = 0
    else:
        verify_cursor_id = verify_cursor.cursor_id

    logging.info("new_watch_addrtxs_verify cursor_id: %s", verify_cursor_id)

    #取所有地址
    addressList = WatchedAddrGroup.query.with_entities(WatchedAddrGroup.address).all()

    #取所有地址的id
    addridList = Addr.query.with_entities(Addr.id).filter(Addr.address.in_(addressList)).all()

    #最多只处理到watch_addrtx_cursor位置
    end_cursor_id = verify_cursor_id + config.ONCE_WATCH_TXID_COUNT
    if end_cursor_id > normal_cursor_id:
        end_cursor_id = normal_cursor_id

    addrtxList = AddrTx.query.filter(AddrTx.tx_id > verify_cursor_id, AddrTx.tx_id <= end_cursor_id).filter(AddrTx.addr_id.in_(addridList)).all()

    for addrtx in addrtxList:
        address = Addr.query.with_entities(Addr.address).filter_by(id=addrtx.addr_id).first()
        if not address:
            logging.error("new_watch_addrtxs_verify addr id %d not found addr", addrtx.addr_id)
            continue
        address = address[0]

        txHash = Tx.query.with_entities(Tx.hash).filter_by(id=addrtx.tx_id).first()
        if not txHash:
            logging.error("new_watch_addrtxs_verify tx id %d not found tx", addrtx.tx_id)
            continue
        txHash = txHash[0]

        w_addrtx = WatchedAddrTx.query.filter_by(address=address, tx=txHash).first()
        if not w_addrtx:
            logging.info("new_watch_addrtxs_verify add WatchedAddrTx address:%s  tx:%s", address, txHash)
            newRecord = WatchedAddrTx()
            newRecord.address = address
            newRecord.tx = txHash
            db_session.add(newRecord)
            db_session.flush()
            db_session.refresh(newRecord)

    if end_cursor_id < normal_cursor_id:
        next_cursor = end_cursor_id
        is_continue = True
    else:
        next_cursor = normal_cursor_id
        is_continue = False

    logging.info("new_watch_addrtxs_verify next watch_addrtx_cursor_verify:%s is_continue:%s", next_cursor, is_continue)
    if not verify_cursor:
        verify_cursor = SystemCursor()
        verify_cursor.cursor_name = 'watch_addrtx_cursor_verify'
        verify_cursor.cursor_id = next_cursor
        db_session.add(verify_cursor)
        db_session.flush()
        db_session.refresh(verify_cursor)
    else:
        verify_cursor.cursor_id = next_cursor
        db_session.flush()
        db_session.refresh(verify_cursor)

    return is_continue

def new_watch_addrtxs_normal():
    cursor_name = 'watch_addrtx_cursor'

    #cursor_id 表明上次已经扫描过的txid
    system_cursor = SystemCursor.query.filter_by(cursor_name=cursor_name).first()
    if not system_cursor:
        cursor_id = 0
    else:
        cursor_id = system_cursor.cursor_id

    logging.info("new_watch_addrtxs_normal cursor_id: %s", cursor_id)

    #取所有地址
    addressList = WatchedAddrGroup.query.with_entities(WatchedAddrGroup.address).all()
    logging.info("new_watch_addrtxs_normal got addressList")

    #取所有地址的id
    addridList = Addr.query.with_entities(Addr.id).filter(Addr.address.in_(addressList)).all()
    logging.info("new_watch_addrtxs_normal got addridList")

    #取当前最大的tx_id
    max_txid = db_session.query(func.max(Tx.id)).all()[0][0] or 0
    logging.info("new_watch_addrtxs_normal got max_txid")

    #分批处理AddrTx表中的记录，类似单次1000条
    addrtxList = AddrTx.query.filter(AddrTx.tx_id > cursor_id, AddrTx.tx_id <= cursor_id + config.ONCE_WATCH_TXID_COUNT).filter(AddrTx.addr_id.in_(addridList)).all()
    logging.info("new_watch_addrtxs_normal got addrtxList")

    for addrtx in addrtxList:
        address = Addr.query.with_entities(Addr.address).filter_by(id=addrtx.addr_id).first()
        if not address:
            logging.error("new_watch_addrtxs_normal addr id %d not found addr", addrtx.addr_id)
            continue
        address = address[0]

        txHash = Tx.query.with_entities(Tx.hash).filter_by(id=addrtx.tx_id).first()
        if not txHash:
            logging.error("new_watch_addrtxs_normal tx id %d not found tx", addrtx.tx_id)
            continue
        txHash = txHash[0]

        w_addrtx = WatchedAddrTx.query.filter_by(address=address, tx=txHash).first()
        if not w_addrtx:
            logging.info("new_watch_addrtxs_normal add WatchedAddrTx address:%s  tx:%s", address, txHash)
            newRecord = WatchedAddrTx()
            newRecord.address = address
            newRecord.tx = txHash
            db_session.add(newRecord)
            db_session.flush()
            db_session.refresh(newRecord)


    logging.info("new_watch_addrtxs_normal compare %d %d", max_txid, cursor_id + config.ONCE_WATCH_TXID_COUNT)
    if max_txid > cursor_id + config.ONCE_WATCH_TXID_COUNT:
        next_cursor = cursor_id + config.ONCE_WATCH_TXID_COUNT
        is_continue = True
    else:
        next_cursor = max_txid
        is_continue = False

    logging.info("new_watch_addrtxs_normal next watch_addrtx_cursor:%s is_continue:%s", next_cursor, is_continue)
    if not system_cursor:
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

    return is_continue

if __name__ == '__main__':
    app.run(host=config.BLOCKSTORE_HOST, port=config.BLOCKSTORE_PORT, debug=config.DEBUG)
