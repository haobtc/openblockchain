#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import simplejson as json
import binascii
from bitcoinrpc.authproxy import AuthServiceProxy
from deserialize import extract_public_key
from base58 import bc_address_to_hash_160

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
    txs = db.engine.execute('select id, hash, version, lock_time, coinbase, tx_size from tx where hash=%(x)s limit 1', x="\\x" + (txhash)).fetchall()
    tx_id = txs[0][0]
    tx = dict(zip(txColumns, txs[0][1:]))

    txins = []
    txinlist = db.engine.execute('select sequence, script_sig, prev_out, prev_out_index from txin where tx_id=%d order by tx_idx' % tx_id).fetchall()
    for vin in txinlist:
        txin = {}
        if tx['coinbase']:
            txin['coinbase'] = vin[1]
        else:
            txin =dict(zip(txinColumns, vin))
            prev_tx = db.engine.execute('select id from tx where hash=%(x)s limit 1', x="\\x" + binascii.hexlify(txin['prev_out'][::-1])).first()
            tx_id = prev_tx[0]
            vout = db.engine.execute('select pk_script, value, type from txout where tx_id=%d and tx_idx=%d' % (tx_id,txin['prev_out_index'])).first()
            prev_txout =dict(zip(txoutColumns, vout))
            txin['value'] = prev_txout['value'] 
            txin['addr'] =extract_public_key(prev_txout['scriptPubKey'])
        txins.append(txin)
    tx['in'] = txins

    txoutlist = db.engine.execute('select pk_script, value, type from txout where tx_id=%d' % tx_id)
    txouts = []
    for vout in txoutlist:
        txout = dict(zip(txoutColumns, vout))
        txout['addrs']=extract_public_key(txout['scriptPubKey'])
        txouts.append(txout)
 
    tx['vin_sz'] = len(txins)
    tx['vout_sz'] = len(txouts)
    tx['out'] = txouts
    return  json.dumps(tx, default=buffer_to_json, indent=4)

@app.route('/height/<height>')
def blkheight(height=0):

    blks = db.engine.execute('select id,hash,height,version,prev_hash,mrkl_root,time,bits,nonce,blk_size,work from blk where height=%(x)s limit 1', x=height).first()
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
    """
    """
    blks = db.engine.execute('select id,hash,height,version,prev_hash,mrkl_root,time,bits,nonce,blk_size,work from blk where hash=%(x)s limit 1', x="\\x" + (blkhash)).first()
    txids = db.engine.execute('select tx.hash from blk,tx,blk_tx where blk.id=blk_tx.blk_id and blk_tx.tx_id=tx.id and blk.id=%(x)s', x=blkid).fetchall()
    txs=[]
    for txid in txids:
       txs.append(txid[0])
    blk = (dict(zip(blkColumns, blks[1:])))
    blk['tx'] = txs
    return  json.dumps(blk, default=buffer_to_json, indent=4)

@app.route('/addr/<address>')
def address(address, num=10):
    hash160 = bc_address_to_hash_160( address).encode('hex')
    import pdb
    pdb.set_trace()
    #hash160 = (address)
    #get addr

    addr={}
    addr['tx']=[]
    txidlist = db.engine.execute("select c.tx_id from addr a  join addr_txout b on (a.id=b.addr_id) join txout c on (c.id=b.txout_id)  where a.hash160='%s' order by c.id desc limit 10" %   hash160).fetchall()

    for res in txidlist:
        tx_id = res[0]
        txs = db.engine.execute('select hash, version, lock_time, coinbase, tx_size from tx where id=%d limit 1' % tx_id).first()
        tx = dict(zip(txColumns, txs))
        txinlist = db.engine.execute('select sequence, script_sig, prev_out, prev_out_index from txin where tx_id=%d order by tx_idx' % tx_id).fetchall()
        txins = []
        for vin in txinlist:
            txin = {}
            if tx['coinbase']:
                txin['coinbase'] = vin[1]
            else:
                txin =dict(zip(txinColumns, vin))
                prev_tx = db.engine.execute('select id from tx where hash=%(x)s limit 1', x="\\x" + binascii.hexlify(txin['prev_out'][::-1])).first()
                tx_id = prev_tx[0]
                vout = db.engine.execute('select pk_script, value, type from txout where tx_id=%d and tx_idx=%d' % (tx_id,txin['prev_out_index'])).first()
                prev_txout =dict(zip(txoutColumns, vout))
                txin['value'] = prev_txout['value'] 
                txin['addr'] =extract_public_key(prev_txout['scriptPubKey'])
            txins.append(txin)
        tx['in'] = txins

        txoutlist = db.engine.execute('select pk_script, value, type from txout where tx_id=%d' % tx_id)
        txouts = []
        for vout in txoutlist:
            txout = dict(zip(txoutColumns, vout))
            txout['addrs']=extract_public_key(txout['scriptPubKey'])
            txouts.append(txout)
 
        tx['vin_sz'] = len(txins)
        tx['vout_sz'] = len(txouts)
        tx['out'] = txouts
        addr['tx'].append(tx)
    addr['addr']=address
    addr['hash160']=hash160

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
