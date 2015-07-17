#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import simplejson as json
import binascii
from bitcoinrpc.authproxy import AuthServiceProxy
from deserialize import extract_public_key
from base58 import bc_address_to_hash_160
from database import *

RPC_URL = "http://bitcoinrpc:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX@127.0.0.1:8333"
access = AuthServiceProxy(RPC_URL)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://postgres@127.0.0.1/bitcoin'
db = SQLAlchemy(app)

txColumns=('hash','version','lock_time','coinbase','size')
txinColumns=('sequence', 'script_sig', 'prev_out', 'prev_out_index' )
txoutColumns=('scriptPubKey', 'value', 'type')
blkColumns=('hash','height','version','prev_hash','mrkl_root','time','bits','nonce','blk_size','work')
addr=('address', 'hash160', 'tx_in_sz', 'tx_out_sz', 'btc_in', 'btc_out', 'balance' , 'tx_sz')


def buffer_to_json(python_object):
    if isinstance(python_object, (buffer, )):
        return binascii.hexlify(python_object)
    raise TypeError(repr(python_object) + ' is not JSON serializable')

@app.route('/tx/<txhash>')
def tx(txhash):                                                                                                                                                                  
    """
    """
    #txhash = "\\x".join(txhash)
    txhash = txhash.decode('hex')
    res = Tx.query.filter(Tx.hash == txhash).first()
    tx= res.todict()
    tx_id = tx['id']

    txins = []
    txins = TxIn.query.filter(TxIn.tx_id==tx_id).all()
    tx['in'] = [txin.todict() for txin in txins ]
    txouts = TxOut.query.filter(TxOut.tx_id==tx_id).all()
    tx['out'] = [txout.todict() for txout in txouts]
    return json.dumps(tx, default=buffer_to_json, indent=4)

@app.route('/height/<height>')
def blkheight(height=0):

    res = Block.query.filter(Block.height == height).first()
    blk = res.todict()
    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id == blk['id']).limit(10);
    txs=[]
    for txid in res:
       res = Tx.query.filter(Tx.id==txid).first()
       tx= res.todict()
       txins = []
       txins = TxIn.query.filter(TxIn.tx_id==tx['id']).all()
       tx['in'] = [txin.todict() for txin in txins ]
       txouts = TxOut.query.filter(TxOut.tx_id==tx['id']).all()
       tx['out'] = [txout.todict() for txout in txouts]
       txs.append(tx)
    blk['tx']=txs
    return  json.dumps(blk, default=buffer_to_json, indent=4)

@app.route('/blk/<blkhash>')
def blk(blkhash):
    """
    """

    res = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    blk = res.todict()
    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id ==  blk['id']).limit(10);
    txs=[]
    for txid in res:
       res = Tx.query.filter(Tx.id==txid).first()
       tx= res.todict()
       txins = []
       txins = TxIn.query.filter(TxIn.tx_id==tx['id']).all()
       tx['in'] = [txin.todict() for txin in txins ]
       txouts = TxOut.query.filter(TxOut.tx_id==tx['id']).all()
       tx['out'] = [txout.todict() for txout in txouts]
       txs.append(tx)
    blk['tx']=txs
    return  json.dumps(blk, default=buffer_to_json, indent=4)

@app.route('/addr/<address>')
def address(address, num=10):
    hash160 = bc_address_to_hash_160( address).encode('hex')
    res = Addr.query.filter(Addr.hash160 == hash160).first()
    addr=res.todict()
    txidlist = UTXO.query.with_entities(UTXO.txout_tx_id).filter(UTXO.hash160 == hash160 and UTXO.txin_id == None).limit(10).all()
    if txidlist ==None:
        txidlist = UTXO.query.with_entities(UTXO.txout_tx_id).filter(UTXO.hash160 == hash160).limit(10).all()

    txs=[]
    for txid in txidlist:
        res = Tx.query.filter(Tx.id==txid).first()
        tx= res.todict()
        txins = []
        txins = TxIn.query.filter(TxIn.tx_id==tx['id']).all()
        tx['in'] = [txin.todict() for txin in txins ]
        txouts = TxOut.query.filter(TxOut.tx_id==tx['id']).all()
        tx['out'] = [txout.todict() for txout in txouts]
        txs.append(tx)
 
    addr['tx']=txs
    addr['address']=address

    return  json.dumps(addr, default=buffer_to_json, indent=4)


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
