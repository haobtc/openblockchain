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
import time

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

app = Flask(__name__)

page_size=10

from bitcoinrpc.authproxy import AuthServiceProxy,JSONRPCException
access = AuthServiceProxy(config.RPC_URL)

#从0扫描到watch_addrtx_cursor位置，并使用自己的watch_addrtx_cursor_verify下标，这样可以重启多次使用
def new_watch_addrtxs_verify():
    normal_cursor_id = 159999409

    verify_cursor = SystemCursor.query.filter_by(cursor_name='watch_addrtx_cursor_verify').first()
    if not verify_cursor:
        verify_cursor_id = 0
    else:
        verify_cursor_id = verify_cursor.cursor_id

    logging.info("new_watch_addrtxs_verify cursor_id: %s", verify_cursor_id)

    #取所有地址
    addressList = WatchedAddrGroup.query.with_entities(WatchedAddrGroup.address).all()
    logging.info("new_watch_addrtxs_verify got addressList")

    #取所有地址的id
    addridList = Addr.query.with_entities(Addr.id).filter(Addr.address.in_(addressList)).all()
    logging.info("new_watch_addrtxs_verify got addridList")

    #最多只处理到watch_addrtx_cursor位置
    end_cursor_id = verify_cursor_id + 50000
    if end_cursor_id > normal_cursor_id:
        end_cursor_id = normal_cursor_id

    addrtxList = AddrTx.query.filter(AddrTx.tx_id > verify_cursor_id, AddrTx.tx_id <= end_cursor_id).filter(AddrTx.addr_id.in_(addridList)).all()
    logging.info("new_watch_addrtxs_verify got addrtxList")

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

if __name__ == '__main__':
    while True:
        new_watch_addrtxs_verify()
        import time
        time.sleep(20)
