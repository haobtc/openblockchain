#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, url_for,redirect,request,jsonify
from flask_sqlalchemy import SQLAlchemy
import simplejson as json
import binascii
from database import *
from sqlalchemy import and_
from datetime import datetime
from util     import calculate_target, calculate_difficulty, decode_check_address
import re
import config
import logging

# logging.basicConfig(format='%(asctime)s %(message)s', filename=config.EXPLORER_API_LOG_FILE,level=logging.INFO)
# console = logging.StreamHandler()  
# console.setLevel(logging.DEBUG)  
# formatter = logging.Formatter('%(asctime)-12s: %(message)s')  
# console.setFormatter(formatter)  
# logging.getLogger('').addHandler(console) 

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)


app = Flask(__name__, static_url_path='/static')

page_size=10

from bitcoinrpc.authproxy import AuthServiceProxy

access = AuthServiceProxy(config.RPC_URL)

def getmininginfo():
  return json.loads(access.getmininginfo())

pool_info=json.loads(open('pools.json','r').read())
def save_pool():
    for addr in pool_info['payout_addresses'].keys():
      try:
        p=POOL()
        p.name=pool_info['payout_addresses'][addr]['name']
        db_session.add(p)
        db_session.flush()
        db_session.refresh(p)
      except:
        pass

    for tag in pool_info['coinbase_tags'].keys():
      try:
        p=POOL()
        p.name=pool_info['coinbase_tags'][tag]['name']
        db_session.add(p)
        db_session.flush()
        db_session.refresh(p)
      except:
        pass
 
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
        coinbase_str = db_session.execute('select a.script_sig from txin a join tx b on(b.id=a.tx_id) join blk_tx c on (c.tx_id=b.id and c.idx=0) where c.blk_id=%d' % blk_id).first()[0];
        for tag in pool_info['coinbase_tags'].keys():
            if re.search(tag, coinbase_str)!=None:
               return  pool_info['coinbase_tags'][tag]['name']
        return 'Unknown'


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
def _jinja2_filter_difficulty(value):
    return calculate_difficulty(value)

def render_404(render_type='html'):
    if render_type=='html':
        return render_template('404.html'), 404
    elif render_type=='json':
        return jsonify({"error":"Not found"}), 404

def lastest_data(render_type='html'):
    blks=[]
    res = Block.query.order_by(Block.height.desc()).limit(10).all()
    for blk in res:
        blk=blk.todict() 
        blk['pool'] = get_pool(blk['id'])
        blks.append(blk)

    txs=[]
    res = Tx.query.order_by(Tx.id.desc()).limit(5).all()
    for tx in res:
        tx= tx.todict()
        tx['in_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txin_tx_id==tx['id']).order_by(VOUT.in_idx).all()
        tx['out_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id).filter(VOUT.txout_tx_id==tx['id']).order_by(VOUT.out_idx).all()
        if tx['recv_time'] == 0:
            tx['recv_time'] = tx['time']
        txs.append(tx)
    
    last_data={}
    last_data['blks'] = blks
    last_data['txs'] = txs
    # last_data['unconfirmed_txs'] = UTX.query.count()

    # mininginfo = getmininginfo()
    # last_data['difficulty'] = mininginfo['difficulty']
    # last_data['networkhashps'] = mininginfo['networkhashps']
    
    if render_type == 'json':
        return jsonify(last_data)

    return render_template('home.html', blks=blks,txs=txs)
 
@app.route('/')
def home():
    return lastest_data(render_type='html')

@app.route('/news')
def news():
    render_type=request.args.get('type') or 'html'
    return lastest_data(render_type)

@app.route('/checkdb')
def checkdb():
    file = open(config.DB_WARNING_FILE)
 
    for line in file:
        return line
        pass # do something
    return "checking"

    # level= request.args.get('level') or 3
    # return check_db(level)

def render_tx(tx=None, render_type='html'):
    tx= tx.todict()

    txins = TxIn.query.filter(TxIn.tx_id==tx['id']).order_by(TxIn.tx_idx.asc()).all()
    tx['vin'] = [txin.todict() for txin in txins ]
    txouts = TxOut.query.filter(TxOut.tx_id==tx['id']).order_by(TxOut.tx_idx.asc()).all()
    tx['vout'] = [txout.todict() for txout in txouts]
    tx['in_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id, VOUT.txout_tx_hash).filter(VOUT.txin_tx_id==tx['id']).order_by(VOUT.in_idx).all()

    tx['out_addresses'] = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id, VOUT.txin_tx_hash).filter(VOUT.txout_tx_id==tx['id']).order_by(VOUT.out_idx).all()
    
    confirm = db_session.execute('select get_confirm(%d)' % tx['id']).first()[0];
    if confirm ==None:
        tx['confirm'] = 0
    else:
        tx['confirm'] = confirm
 
    if render_type == 'json':
        return jsonify(tx)

    return render_template("tx.html",tx=tx)

@app.route('/tx/<txhash>', methods=['GET', 'POST'])
def tx_handle(txhash,tx=None):
    render_type=request.args.get('type') or 'html'
    if tx ==None:
        tx = Tx.query.filter(Tx.hash == txhash.decode('hex')).first()
    if tx == None:
        return render_404(render_type)

    return render_tx(tx, render_type)

def render_blk(blk=None, page=1, render_type='html'):
    blk = blk.todict()

    total_page = blk['tx_count']/page_size
    if blk['tx_count']%page_size:
        total_page+=1
    blk['total_page'] = total_page

    page =int(page)
    if page <1:
        page = 1
    if page > total_page:
        page = total_page

    blk['page'] = page

    res = BlockTx.query.with_entities(BlockTx.tx_id).filter(BlockTx.blk_id == blk['id']).order_by(BlockTx.idx).offset((page-1)*page_size).limit(page_size)
    if res!= None:
        txs=[]
        for txid in res:
           res = Tx.query.filter(Tx.id==txid).first()
           tx= res.todict()
           txins = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id, VOUT.txout_tx_hash).filter(VOUT.txin_tx_id==txid).order_by(VOUT.in_idx).all()
           tx['in_addresses'] = txins
           txouts = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id, VOUT.txin_tx_hash).filter(VOUT.txout_tx_id==txid).order_by(VOUT.out_idx).all()
           tx['out_addresses'] = txouts
           txs.append(tx)
    blk['tx']=txs

    res = Block.query.with_entities(Block.hash).filter(Block.height == (int(blk['height'])+1)).first()
    if res!= None:
        blk['nextblockhash']=res[0]

    if render_type == 'json':
        return jsonify(blk)

    return render_template("blk.html",blk=blk, page=page)

@app.route('/height/<height>', methods=['GET', 'POST'])
def blkheight_handle(height=0):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 1
    blk = Block.query.filter(Block.height == height).first()
    if blk== None:
        return render_404(render_type)

    return render_blk(blk, page, render_type)

@app.route('/blk/<blkhash>', methods=['GET', 'POST'])
def blk_handle(blkhash, blk=None):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 1

    if blk==None:
       blk = Block.query.filter(Block.hash == blkhash.decode('hex')).first()
    if blk== None:
        return render_404(render_type)

    return render_blk(blk, page, render_type)

def confirm(txs): 
     return txs['confirm'] 

def render_addr(address=None, page=1, render_type='html', filter=0):
    addr = Addr.query.filter(Addr.address == address).first()
    if addr == None:
        ver,hash160=decode_check_address(address)
        if hash160==None or (ver !='\x00' and ver != '\x05'):
            return render_404(render_type)
        else:
            addr = {}
            addr['hash160'] = ''
            addr['txs']=[]
            addr['txs_len']= 0
            addr['page_size'] = 0
            addr['address']=address
            addr['total_page'] = 0
            addr['tx_count']=0
            addr['page'] = 0
            addr['recv_value'] = 0
            addr['spent_value'] = 0
            addr['balance'] = 0

        if render_type == 'json':
            return jsonify(addr)

        return render_template("addr.html", addr=addr,page=page)
 

    addr=addr.todict()
    addr['tx_count']=AddrTx.query.filter(AddrTx.addr_id==int(addr["id"])).count();

    total_page = addr['tx_count']/page_size
    if addr['tx_count']%page_size:
        total_page+=1
    addr['total_page'] = total_page

    page =int(page)
    if page <1:
        page = 1

    addr['page'] = page

    txs=[]
    txids=[]
    txout_tx_ids =[]
    txin_tx_ids = []
    txidlist=None
    if filter==0:   #all
        txidlist = AddrTx.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id==int(addr["id"])).order_by(AddrTx.tx_id.desc()).offset((page-1)*page_size).limit(page_size)
    elif filter==1: #spent
        txidlist = VOUT.query.with_entities(VOUT.txin_tx_id).distinct(VOUT.txin_tx_id).filter(and_(VOUT.addr_id==int(addr["id"]),VOUT.txin_tx_id!=None)).order_by(VOUT.txin_tx_id.desc()).offset((page-1)*page_size).limit(page_size)
    elif filter==2: #recv
        txidlist = VOUT.query.with_entities(VOUT.txout_tx_id).distinct(VOUT.txout_tx_id).filter(VOUT.addr_id==int(addr["id"])).order_by(VOUT.txout_tx_id.desc()).offset((page-1)*page_size).limit(page_size)
    elif filter==3: #utxo
        txidlist = VOUT.query.with_entities(VOUT.txout_tx_id).distinct(VOUT.txout_tx_id).filter(and_(VOUT.addr_id==int(addr["id"]),VOUT.txin_tx_id==None)).order_by(VOUT.txout_tx_id.desc()).offset((page-1)*page_size).limit(page_size)
    elif filter==4: #unconfirm
        txidlist =  AddrTxUC.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id==int(addr["id"])).order_by(AddrTx.tx_id.desc()).offset((page-1)*page_size).limit(page_size)
    elif filter==5: #confirm
        txidlist = AddrTxC.query.with_entities(AddrTx.tx_id).filter(AddrTx.addr_id==int(addr["id"])).order_by(AddrTx.tx_id.desc()).offset((page-1)*page_size).limit(page_size)
    else:
        return render_404(render_type)

    if txidlist==None:
        return render_404(render_type)

    in_value = 0 
    out_value = 0 
    for txid in txidlist:
        tx_in_value = 0 
        tx_out_value = 0 

        txid=txid[0]
        res = Tx.query.filter(Tx.id==txid).first()
        tx= res.todict()

        txins = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id, VOUT.txout_tx_hash).filter(VOUT.txin_tx_id==txid).order_by(VOUT.in_idx).all()
        for vin in txins:
            if vin.address==address:
                tx_in_value = tx_in_value - vin.value
                in_value = in_value - vin.value
        tx['vin'] = txins

        txouts = VOUT.query.with_entities(VOUT.address, VOUT.value, VOUT.txin_tx_id, VOUT.txin_tx_hash).filter(VOUT.txout_tx_id==txid).order_by(VOUT.out_idx).all()
        for vout in txouts:
            if vout.address==address:
                tx_out_value = tx_out_value + vout.value
                out_value = out_value + vout.value
        tx['vout'] = txouts

        tx['confirm'] = db_session.execute('select get_confirm(%d)' % tx['id']).first()[0];
        tx['spent']= tx_in_value + tx_out_value
        txs.append(tx)
    
    addr['txs']=txs
    addr['txs_len']=len(txs)
    addr['page_size'] =page_size
    addr['address']=address

    if render_type == 'json':
        return jsonify(addr)

    return render_template("addr.html", addr=addr,page=page)

@app.route('/addr/<address>', methods=['GET', 'POST'])
def address_handle(address):
    render_type=request.args.get('type') or 'html'
    page= request.args.get('page') or 1
    filter= request.args.get('filter') or 0

    return render_addr(address, page, render_type, int(filter))

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
            return render_404(render_type)
          
        tx = Tx.query.filter(Tx.hash ==hash ).first()
        if tx!=None:
            return render_tx(tx, render_type)
        else:
            blk = Block.query.filter(Block.hash == hash).first()
            if blk!=None:
               return render_blk(blk, 1, render_type)
            else:
               return render_404(render_type)
    elif slen <= 34 and slen >=26:
        addr = sid
        return render_addr(addr,1, render_type)
    elif slen <9:
        #as blk height
        height = sid
        blk = Block.query.filter(Block.height == height).first()
        if blk== None:
            return render_404(render_type)

        return render_blk(blk, 1, render_type)
    else:
        return render_404(render_type)

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
