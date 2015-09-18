#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for,redirect,request,jsonify
from flask_sqlalchemy import SQLAlchemy
import simplejson as json
import binascii
from database import *
from sqlalchemy import and_
from datetime import datetime

app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')

@app.template_filter('datetime')
def _jinja2_filter_datetime(date, fmt=None):
    return datetime.utcfromtimestamp(date).ctime()

@app.route('/')
def home():                                                                                                                                                                  
    return render_template('home.html')

@app.route('/tx/<txhash>')
@app.route('/tx/<txhash>/<render_type>')
def tx(txhash,render_type='html'):
    res = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    # if res== None:
    #     return render_template('404.html'), 404
    tx= res.todict()

    txins = TxIn.query.filter(TxIn.tx_id==tx['id']).all()
    tx['vin'] = [txin.todict() for txin in txins ]
    txouts = TxOut.query.filter(TxOut.tx_id==tx['id']).all()
    tx['vout'] = [txout.todict() for txout in txouts]

    tx['in_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txin_tx_id==tx['id']).all()
    tx['out_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txout_tx_id==tx['id']).all()
    tx['confirm'] = db_session.execute('select get_confirm(%d)' % tx['id']).first()[0];
 
    if render_type == 'json':
        return jsonify(tx)

    return render_template("tx.html",tx=tx)


@app.route('/height/<height>')
@app.route('/height/<height>/<render_type>')
def blkheight(height=0,render_type='html'):
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

    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(height)+1)).first()
    if res!= None:
        blk['nextblockhash']=binascii.hexlify(res[0])

    if render_type == 'json':
        return jsonify(blk)

    return render_template("blk.html",blk=blk)

@app.route('/blk/<blkhash>')
@app.route('/blk/<blkhash>/<render_type>')
def blk(blkhash,render_type='html'):
    res = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    if res== None:
        return render_template('404.html'), 404

    blk = res.todict()

    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id == blk['id']).order_by(BlockTx.tx_id.asc()).limit(10)
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

    if render_type == 'json':
        return jsonify(blk)

    return render_template("blk.html",blk=blk)

@app.route('/addr/<address>')
@app.route('/addr/<address>/<int:page>')
@app.route('/addr/<address>/<render_type>')
@app.route('/addr/<address>/<int:page>/<render_type>')
def address(address, page=0, page_size=10,render_type='html'):
    res = Addr.query.filter(Addr.address == address).first()
    if res== None:
        return render_template('404.html'), 404
    addr=res.todict()

    page =int(page)
    if page <0:
        page = 0

    txidlist = VOUT.query.with_entities(VOUT.txout_tx_id).filter(VOUT.address == address).order_by(VOUT.txout_tx_id.desc()).offset(page*page_size).limit(page_size)

    txs=[]
    for txid in txidlist:
        res = Tx.query.filter(Tx.id==txid).first()
        tx= res.todict()
        txins = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txin_tx_id==txid).all()
        tx['vin'] = txins
        txouts = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txout_tx_id==txid).all()
        tx['vout'] = txouts
        tx['confirm'] = db_session.execute('select get_confirm(%d)' % tx['id']).first()[0];
        txs.append(tx)
 
    addr['txs']=txs
    addr['address']=address

    if render_type == 'json':
        return jsonify(addr)

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
