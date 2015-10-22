#!/usr/bin/env python2.7

import os
import sys
_basedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _basedir)

DEBUG = False

HOST='127.0.0.1'
PORT=5000

SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@@127.0.0.1:5432/dbname'
RPC_URL = "http://bitcoinrpc:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX@127.0.0.1:8332"
DB_WARNING_FILE = "~/check_db.txt"

EMAIL_HOST = 'p.haobtc.com'
EMAIL_HOST_USER = 'notify@haobtc.com'
EMAIL_HOST_PASSWORD = 'xxx'
EMAIL_USE_TLS = True

EMAIL_RECEIVER = ['']