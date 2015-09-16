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

@app.route('/')
def home():                                                                                                                                                                  
    return render_template('home.html')

@app.route('/tx/<txhash>')
def tx(txhash):
    res = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    if res== None:
        return render_template('404.html'), 404
    tx= res.todict()

    txins = TxIn.query.filter(TxIn.tx_id==tx['id']).all()
    tx['vin'] = [txin.todict() for txin in txins ]
    txouts = TxOut.query.filter(TxOut.tx_id==tx['id']).all()
    tx['vout'] = [txout.todict() for txout in txouts]

    tx['in_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txin_tx_id==tx['id']).all()
    tx['out_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txout_tx_id==tx['id']).all()
 
    return render_template("tx.html",tx=tx)

@app.route('/height/<height>')
def blkheight(height=0):
    res = Block.query.filter(Block.height == height).first()
    if res== None:
        return render_template('404.html'), 404

    blk = res.todict()

    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id == blk['id']).limit(10)
    if res!= None:
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

    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(height)-1)).first()
    if res!= None:
        blk['previousblockhash']=binascii.hexlify(res[0])
    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(height)+1)).first()
    if res!= None:
        blk['nextblockhash']=binascii.hexlify(res[0])

    return render_template("blk.html",blk=blk)

@app.route('/blk/<blkhash>')
def blk(blkhash):
    res = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    if res== None:
        return render_template('404.html'), 404

    blk = res.todict()

    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id == blk['id']).limit(10)
    if res!= None:
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

    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(blk['height'])+1)).first()
    if res!= None:
        blk['nextblockhash']=binascii.hexlify(res[0])

    return render_template("blk.html",blk=blk)
 
@app.route('/addr/<address>')
@app.route('/addr/<address>/<page>')
def address(address, page=0, num=10):
    page =int(page)
    res = Addr.query.filter(Addr.address == address).first()
    if res== None:
        return render_template('404.html'), 404
    addr=res.todict()
    txidlist = VOUT.query.with_entities(VOUT.txout_tx_id).filter(VOUT.address == address).offset(page*10).limit(10)
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
