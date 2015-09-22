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
def _jinja2_filter_datetime(date):
    return datetime.utcfromtimestamp(date).ctime()

@app.template_filter('reward')
def _jinja2_filter_reward(blk):
    i = int(blk['height']) / 210000
    return float(blk['fees'])/100000000 + float(50)/(i+1)

@app.template_filter('btc')
def _jinja2_filter_btc(value):
    if value=='':
       return 0
    return float(value)/100000000
 
def lastest_data(render_type='html'):                                                                                                                                                                  
    res = Block.query.order_by(Block.id.desc()).limit(10).all()
    blks=[blk.todict() for blk in res]

    txs=[]
    res = Tx.query.order_by(Tx.id.desc()).limit(10).all()
    for tx in res:
        tx= tx.todict()
        tx['in_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txin_tx_id==tx['id']).all()
        tx['out_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value).filter(VOUT.txout_tx_id==tx['id']).all()
        txs.append(tx)
 
    if render_type == 'json':
        return jsonify(last_data)

    return render_template('home.html', blks=blks,txs=txs)
 
@app.route('/')
def home():                                                                                                                                                                  
    return lastest_data(render_type='html')

@app.route('/tx/<txhash>')
@app.route('/tx/<txhash>/<render_type>')
def tx_handle(txhash,tx=None,render_type='html'):
    if tx ==None:
        tx = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    if tx == None:
        return render_template('404.html'), 404
    tx= tx.todict()

    txins = TxIn.query.filter(TxIn.tx_id==tx['id']).all()
    tx['vin'] = [txin.todict() for txin in txins ]
    txouts = TxOut.query.filter(TxOut.tx_id==tx['id']).all()
    tx['vout'] = [txout.todict() for txout in txouts]

    tx['in_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txin_tx_id==tx['id']).all()
    tx['out_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txout_tx_id==tx['id']).all()
    confirm = db_session.execute('select get_confirm(%d)' % tx['id']).first()[0];
    if confirm ==None:
        tx['confirm'] = u"未确认"
    else:
        tx['confirm'] = confirm
 
    if render_type == 'json':
        return jsonify(tx)

    return render_template("tx.html",tx=tx)

def render_blk(blk=None, page=0, page_size=10, render_type='html'):
 
    blk = blk.todict()

    page =int(page)
    if page <0:
        page = 0
 
    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id == blk['id']).order_by(BlockTx.idx).offset(page*page_size).limit(page_size)
    if res!= None:
        txs=[]
        for txid in res:
           res = Tx.query.filter(Tx.id==txid).first()
           tx= res.todict()
           txins = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txin_tx_id==txid).all()
           tx['in_addresses'] = txins
           txouts = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txout_tx_id==txid).all()
           tx['out_addresses'] = txouts
           txs.append(tx)
    blk['tx']=txs

    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(blk['height'])+1)).first()
    if res!= None:
        blk['nextblockhash']=binascii.hexlify(res[0])

    if render_type == 'json':
        return jsonify(blk)

    return render_template("blk.html",blk=blk, page=page)

@app.route('/height/<height>')
@app.route('/height/<height>/<render_type>')
def blkheight_handle(height=0, page=0, page_size=10, render_type='html'):
    blk = Block.query.filter(Block.height == height).first()
    if blk== None:
        return render_template('404.html'), 404

    return render_blk(blk, page, page_size, render_type)

@app.route('/blk/<blkhash>')
@app.route('/blk/<blkhash>/<int:page>')
@app.route('/blk/<blkhash>/<render_type>')
@app.route('/blk/<blkhash>/<int:page>/<render_type>')
def blk_handle(blkhash, blk=None, page=0, page_size=10, render_type='html'):
    if blk==None:
       blk = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    if blk== None:
        return render_template('404.html'), 404

    return render_blk(blk, page, page_size, render_type)

@app.route('/addr/<address>')
@app.route('/addr/<address>/<int:page>')
@app.route('/addr/<address>/<render_type>')
@app.route('/addr/<address>/<int:page>/<render_type>')
def address_handle(address, page=0, page_size=10,render_type='html'):
    addr = Addr.query.filter(Addr.address == address).first()
    if addr == None:
        return render_template('404.html'), 404
    addr=addr.todict()

    page =int(page)
    if page <0:
        page = 0

    txidlist = VOUT.query.with_entities(VOUT.txout_tx_id).filter(VOUT.address == address).order_by(VOUT.txout_tx_id.desc()).offset(page*page_size).limit(page_size)

    txs=[]
    for txid in txidlist:
        res = Tx.query.filter(Tx.id==txid).first()
        tx= res.todict()
        txins = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txin_tx_id==txid).all()
        tx['vin'] = txins
        txouts = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txout_tx_id==txid).all()
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
          hash = sid.decode('hex')
        except:
          return redirect("/", code=302)
          
        tx = Tx.query.filter(Tx.hash ==hash ).first()
        if tx!=None:
            return tx_handle(sid,tx)
        else:
            blk = Block.query.filter(Block.hash == hash).first()
            if blk!=None:
               return blk_handle(sid,blk)
            else:
               return redirect("/", code=302)
    elif slen <= 34 and slen >=26:
         return redirect("/addr/%s" % sid, code=302)
    elif slen <9:
        #as blk height
        return redirect("/height/%s" % sid, code=302)
    else:
        return redirect("/", code=302)
 

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
