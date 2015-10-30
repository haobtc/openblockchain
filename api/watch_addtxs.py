#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division 
import os 
import sys
import simplejson as json
import binascii
from BCDataStream import *
from deserialize import *
from util import double_sha256, get_ip_address
import time

import requests
from database import *
from sqlalchemy import and_
import logging

from config import *
from blockstore_api import watch_addrtxs

logging.basicConfig(format='%(asctime)s %(message)s', filename=config.CHECK_LOG_FILE,level=logging.INFO)
console = logging.StreamHandler()  
console.setLevel(logging.DEBUG)  
formatter = logging.Formatter('%(asctime)-12s: %(message)s')  
console.setFormatter(formatter)  
logging.getLogger('').addHandler(console) 

if __name__ == '__main__':
    start_time = time.time()
    watch_addrtxs()
    end_time = time.time()
    if end_time - start_time < 5:
        time.sleep(5 - end_time + start_time)

   

