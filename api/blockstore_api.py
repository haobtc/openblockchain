#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for,redirect,request,jsonify
from flask_sqlalchemy import SQLAlchemy
import simplejson as json
import binascii
from database import *
from sqlalchemy import and_
from datetime import datetime
from util     import calculate_target, calculate_difficulty,work_to_difficulty
import re
import config
from check_db import check_db

app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')

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

@app.route('/queryapi/v2/tx/list', methods=['GET'])
def getRelatedTxIdList():
    # addresses  = request.args.get('addresses')
    pass

@app.route('/queryapi/v1/tx/details/<txid>', methods=['GET'])
def getTxDetails(txid):
    pass

@app.route('/queryapi/v1/block/bitcoin/tip', methods=['GET'])
def getTipBlock():
    pass

@app.route('/queryapi/v1/sendtx/bitcoin/<address>', methods=['GET', 'POST'])
def sendTx(address):
    pass


if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
