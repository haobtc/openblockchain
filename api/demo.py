#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for,redirect,request,jsonify
from flask_sqlalchemy import SQLAlchemy
import simplejson as json
import binascii
from database import *
from sqlalchemy import and_
from datetime import datetime
from util     import calculate_target, calculate_difficulty

app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')

page_size=10

pool_info=json.loads(open('pools.json','r').read())
def get_pool(blk_id):
    coinbase_txout_id = db_session.execute('select a.id from txout a join tx b on(b.id=a.tx_id) join blk_tx c on (c.tx_id=b.id and c.idx=0) where c.blk_id=%d' % blk_id).first()[0];
    if coinbase_txout_id==None:
        return ''
    coinbase_addr = VOUT.query.with_entities(VOUT.address).filter(VOUT.txout_id==coinbase_txout_id).first()
    if coinbase_addr==None:
        return ''
    pool= pool_info['payout_addresses'].get(coinbase_addr[0])
    if pool!=None:
        return  pool['name']
    else:
        return ''


@app.template_filter('datetime')
def _jinja2_filter_datetime(date):
    return datetime.utcfromtimestamp(date).ctime()

@app.template_filter('reward')
def _jinja2_filter_reward(blk):
    halvings = int(blk['height']) / 210000

    # Force block reward to zero when right shift is undefined.
    if halvings >= 64:
        return float(blk['fees'])/100000000

    # Subsidy is cut in half every 210,000 blocks which will occur approximately every 4 years.
    return float(blk['fees'])/100000000 + float(50)/(halvings+1) 

@app.template_filter('btc')
def _jinja2_filter_btc(value):
    if value=='':
       return 0
    return float(value)/100000000
 
@app.template_filter('target')
def _jinja2_filter_target(value):
    return calculate_target(value)

@app.template_filter('difficulty')
def _jinja2_filter_target(value):
    return calculate_difficulty(value)

def render_404(render_type='html'):
    if render_type=='html':
        return render_template('404.html'), 404
    elif render_type=='json':
        return jsonify({"error":"Not found"})

def lastest_data(render_type='html'):
    blks=[]
    res = Block.query.order_by(Block.id.desc()).limit(10).all()
    for blk in res:
        blk=blk.todict() 
        blk['pool'] = get_pool(blk['id'])
        blks.append(blk)

    txs=[]
    res = Tx.query.order_by(Tx.id.desc()).limit(10).all()
    for tx in res:
        tx= tx.todict()
        tx['in_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txin_tx_id==tx['id']).order_by(VOUT.in_idx).all()
        tx['out_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txout_tx_id==tx['id']).order_by(VOUT.out_idx).all()
        txs.append(tx)
    
    last_data={}
    last_data['blks'] = blks
    last_data['txs'] = txs
    
    if render_type == 'json':
        return jsonify(last_data)

    return render_template('home.html', blks=blks,txs=txs)
 
@app.route('/')
def home():
    render_type=request.args.get('type') or 'html'
    return lastest_data(render_type='html')

@app.route('/news')
def news():
    render_type=request.args.get('type') or 'html'
    return lastest_data(render_type='json')

@app.route('/tx/<txhash>', methods=['GET', 'POST'])
def tx_handle(txhash,tx=None):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 0
    if tx ==None:
        tx = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    if tx == None:
        return render_404(render_type)
    tx= tx.todict()

    txins = TxIn.query.filter(TxIn.tx_id==tx['id']).all()
    tx['vin'] = [txin.todict() for txin in txins ]
    txouts = TxOut.query.filter(TxOut.tx_id==tx['id']).all()
    tx['vout'] = [txout.todict() for txout in txouts]

    tx['in_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txin_tx_id==tx['id']).order_by(VOUT.in_idx).all()
    tx['out_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txout_tx_id==tx['id']).order_by(VOUT.out_idx).all()
    confirm = db_session.execute('select get_confirm(%d)' % tx['id']).first()[0];
    if confirm ==None:
        tx['confirm'] = u"未确认"
    else:
        tx['confirm'] = confirm
 
    if render_type == 'json':
        return jsonify(tx)

    return render_template("tx.html",tx=tx)

def render_blk(blk=None, page=0, render_type='html'):
 
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
           txins = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txin_tx_id==txid).order_by(VOUT.in_idx).all()
           tx['in_addresses'] = txins
           txouts = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txout_tx_id==txid).order_by(VOUT.out_idx).all()
           tx['out_addresses'] = txouts
           txs.append(tx)
    blk['tx']=txs

    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(blk['height'])+1)).first()
    if res!= None:
        blk['nextblockhash']=binascii.hexlify(res[0])

    if render_type == 'json':
        return jsonify(blk)

    return render_template("blk.html",blk=blk, page=page)

@app.route('/height/<height>', methods=['GET', 'POST'])
def blkheight_handle(height=0):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 0
    blk = Block.query.filter(Block.height == height).first()
    if blk== None:
        return render_404(render_type)

    return render_blk(blk, page, render_type)

@app.route('/blk/<blkhash>', methods=['GET', 'POST'])
def blk_handle(blkhash, blk=None):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 0
    if blk==None:
       blk = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    if blk== None:
        return render_404(render_type)

    return render_blk(blk, page, render_type)

def confirm(txs): 
     return txs['confirm'] 

@app.route('/addr/<address>', methods=['GET', 'POST'])
def address_handle(address):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 0
    addr = Addr.query.filter(Addr.address == address).first()
    if addr == None:
        return render_404(render_type)
    addr=addr.todict()

    page =int(page)
    if page <0:
        page = 0

    txs=[]
    txids=[]
    txout_tx_ids =[]
    txin_tx_ids = []
    txidlist = db_session.execute("select txid from ((select txout_tx_id as txid,addr_id from vout where address='%s')  union (select txin_tx_id as txid,addr_id from vout where address='%s')) as t where txid is not NULL order by txid desc offset %d limit %d;" % (address,address,page*page_size,page_size)).fetchall();

    in_value = 0 
    out_value = 0 
    for txid in txidlist:
        txid=txid[0]
        res = Tx.query.filter(Tx.id==txid).first()
        tx= res.todict()

        txins = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txin_tx_id==txid).order_by(VOUT.in_idx).all()
        tx['vin'] = txins
        for vin in txins:
            if vin.address==address:
                in_value = in_value - vin.value

        txouts = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txout_tx_id==txid).order_by(VOUT.out_idx).all()
        tx['vout'] = txouts
        for vout in txouts:
            if vout.address==address:
                out_value = out_value + vout.value

        tx['confirm'] = db_session.execute('select get_confirm(%d)' % tx['id']).first()[0];
        txs.append(tx)
    
    addr['txs']=sorted(txs,key = confirm)
    addr['address']=address
    addr['spent']= in_value + out_value

    if render_type == 'json':
        return jsonify(addr)

    return render_template("addr.html", addr=addr,page=page)

@app.route('/search', methods=['GET', 'POST'])
def search(sid=0):
    sid = request.args.get('sid') or sid
    render_type=request.args.get('type') or 'html'

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
               return render_404(render_type)
    elif slen <= 34 and slen >=26:
         return redirect("/addr/%s" % sid, code=302)
    elif slen <9:
        #as blk height
        return redirect("/height/%s" % sid, code=302)
    else:
        return render_404(render_type)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
