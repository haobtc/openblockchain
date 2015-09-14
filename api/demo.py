#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for,redirect,request
from flask_sqlalchemy import SQLAlchemy
import simplejson as json
import binascii
from database import *
from sqlalchemy import and_

app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')

def buffer_to_json(python_object):
    if isinstance(python_object, (buffer, )):
        return binascii.hexlify(python_object)
    raise TypeError(repr(python_object) + ' is not JSON serializable')

@app.route('/')
def home():                                                                                                                                                                  
    return render_template('home.html')

@app.route('/tx/<txhash>')
def tx(txhash):
    txhash = txhash.decode('hex')
    res = Tx.query.filter(Tx.hash == txhash).first()
    tx= res.todict()
    tx_id = tx['id']

    txins = TxIn.query.filter(TxIn.tx_id==tx_id).all()
    tx['vin'] = [txin.todict() for txin in txins ]
    for txin in tx['vin']:
        txin['address']=VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txin_tx_id==txin['id']).all()
    txouts = TxOut.query.filter(TxOut.tx_id==tx_id).all()
    tx['vout'] = [txout.todict() for txout in txouts]
    for txout in tx['vin']:
        txout['address'] = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txout_tx_id==txout['id']).all()
    return render_template("tx.html",tx=tx)

@app.route('/height/<height>')
def blkheight(height=0):
    res = Block.query.filter(Block.height == height).first()
    blk = res.todict()
    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(height)-1)).first()
    blk['previousblockhash']=binascii.hexlify(res[0])
    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(height)+1)).first()
    blk['nextblockhash']=binascii.hexlify(res[0])
    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id == blk['id']).limit(10)

    txs=[]
    for txid in res:
       res = Tx.query.filter(Tx.id==txid).first()
       tx= res.todict()
       txins = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txin_tx_id==txid).all()
       tx['in'] = txins
       txouts = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txout_tx_id==txid).all()
       tx['out'] = txouts
       txs.append(tx)


    blk['tx']=txs
    return render_template("blk.html",blk=blk)

@app.route('/blk/<blkhash>')
def blk(blkhash):
    res = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    blk = res.todict()
    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(blk['height'])-1)).first()
    blk['previousblockhash']=binascii.hexlify(res[0])
    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(blk['height'])+1)).first()
    blk['nextblockhash']=binascii.hexlify(res[0])
    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id == blk['id']).limit(10)

    txs=[]
    for txid in res:
       res = Tx.query.filter(Tx.id==txid).first()
       tx= res.todict()
       txins = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txin_tx_id==txid).all()
       tx['in'] = txins
       txouts = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txout_tx_id==txid).all()
       tx['out'] = txouts
       txs.append(tx)

    blk['tx']=txs
    return render_template("blk.html",blk=blk)
 
@app.route('/addr/<address>')
@app.route('/addr/<address>/<int:page>')
def address(address, page=0, page_size=10):
    res = Addr.query.filter(Addr.address == address).first()
    addr=res.todict()
    txidlist = VOUT.query.with_entities(VOUT.txout_tx_id).filter(VOUT.address == address)
    if page_size:
        txidlist = txidlist.limit(page_size)

    if page <0:
        page = 0

    if page: 
        txidlist = txidlist.offset(page*page_size)

    #txidlist = VOUT.query.with_entities(VOUT.txout_tx_id).filter(and_(VOUT.address == address, VOUT.txin_tx_id==None )).limit(10)
    #if txidlist == None:

    txs=[]
    for txid in txidlist:
        res = Tx.query.filter(Tx.id==txid).first()
        tx= res.todict()
        txins = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txin_tx_id==txid).all()
        tx['vin'] = txins
        txouts = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txout_tx_id==txid).all()
        tx['vout'] = txouts
        txs.append(tx)
 
    addr['txs']=txs
    addr['address']=address
    print addr

    return render_template("addr.html", addr=addr,page=page)

@app.route('/search', methods=['GET', 'POST'])
def search(sid=0):                                                                                                                                                                  

    sid = sid or request.args.get('sid')

    slen = len(sid)
    if slen == 64:
        #should be tx hash or blk hash
        try:
            return redirect("/tx/%s" % sid, code=302)
        except:
            try:
               return redirect("/blk/%s" % sid, code=302)
            except:
               return redirect("/", code=302)
    if slen <= 34 and slen >=26:
         return redirect("/addr/%s" % sid, code=302)
    elif slen <9:
        #as blk height
        return redirect("/height/%s" % sid, code=302)
    else:
        return redirect("/", code=302)
 

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
