#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import simplejson as json
import binascii
from bitcoinrpc.authproxy import AuthServiceProxy

RPC_URL = "http://bitcoinrpc:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX@127.0.0.1:8333"
access = AuthServiceProxy(RPC_URL)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://postgres@127.0.0.1/bitcoin'
db = SQLAlchemy(app)

blkColumns=('hash','height','version','prev_hash','mrkl_root','time','bits','nonce','blk_size','work')
txColumns=('hash','version','lock_time','coinbase','size')

def buffer_to_json(python_object):
    if isinstance(python_object, (buffer, )):
        return binascii.hexlify(python_object)
    raise TypeError(repr(python_object) + ' is not JSON serializable')

@app.route('/tx/<txhash>')
def tx(txhash):                                                                                                                                                                  
    txs = db.engine.execute('select hash, version, lock_time, coinbase, tx_size from tx where hash=%(x)s limit 1', x="\\x" + (txhash)).fetchall()
    tx = dict(zip(txColumns, txs[0]))
    return  json.dumps(tx, default=buffer_to_json, indent=4)

@app.route('/height/<height>')
def blkheight(height=0):
    blks = db.engine.execute('select id,hash,depth,version,prev_hash,mrkl_root,time,bits,nonce,blk_size,work from blk where depth=%(x)s limit 1', x=height).first()
    blkid =blks[0]
    txids = db.engine.execute('select tx.hash from blk,tx,blk_tx where blk.id=blk_tx.blk_id and blk_tx.tx_id=tx.id and blk.id=%(x)s', x=blkid).fetchall()
    txs=[]
    for txid in txids:
       txs.append(txid[0])
    blk = (dict(zip(blkColumns, blks[1:])))
    blk['tx'] = txs
    return  json.dumps(blk, default=buffer_to_json, indent=4)

@app.route('/blk/<blkhash>')
def blk(blkhash):
    blks = db.engine.execute('select id,hash,depth,version,prev_hash,mrkl_root,time,bits,nonce,blk_size,work from blk where hash=%(x)s limit 1', x="\\x" + (blkhash)).first()
    blkid =blks[0]
    txids = db.engine.execute('select tx.hash from blk,tx,blk_tx where blk.id=blk_tx.blk_id and blk_tx.tx_id=tx.id and blk.id=%(x)s', x=blkid).fetchall()
    txs=[]
    for txid in txids:
       txs.append(txid[0])
    blk = (dict(zip(blkColumns, blks[1:])))
    blk['tx'] = txs
    return  json.dumps(blk, default=buffer_to_json, indent=4)

@app.route('/addr/<address>')
def address(address, num=10):
    return "todo"
 
@app.route('/mempool/<txhash>')
def getrawmempool():                                                                                                                                                                  
    return access.getrawmempool()
    
@app.route('/nodeinfo')
def getaddednodeinfo (node):
    return access.getaddednodeinfo('dns', node)

@app.route('/mininginfo')
def getmininginfo():
    return json.dumps(access.getmininginfo())
 
@app.route('/blockchaininfo')
def getblockchaininfo():
    return access.getblockchaininfo()

@app.route('/info')
def getinfo():
    return access.getinfo()

@app.route('/networkinfo')
def getnetworkinfo():
    return access.getnetworkinfo()
 
@app.route('/peerinfo')
def getpeerinfo():
    return access.getpeerinf()

@app.route('/txoutsetinfo')
def gettxoutsetinfo():
    return access.gettxoutsetinfo()
 
@app.route('/orphantx')
def orphantx():                                                                                                                                                                  
    return "todo"
 
@app.route('/orphanblk')
def orphanblk():                                                                                                                                                                  
    return "todo"

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
