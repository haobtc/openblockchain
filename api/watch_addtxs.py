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

if __name__ == '__main__':
    start_time = time.time()
    watch_addrtxs(False)
    end_time = time.time()
    if end_time - start_time < 300:
        time.sleep(300 - end_time + start_time)

   

