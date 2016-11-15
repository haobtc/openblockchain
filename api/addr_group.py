import binascii
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData
from sqlalchemy.dialects.postgresql import BIGINT, BIT, BOOLEAN, BYTEA, INTEGER, BOOLEAN, TEXT
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref
import config
import logging
import time
import pickle

class AddrGroup:

    def __init__(self, n):
        self._id = list(range(n))
        self._sz = [1] * n

    def _root(self, i):
        j = i
        while (j != self._id[j]):
            self._id[j] = self._id[self._id[j]]
            j = self._id[j]
        return j

    def find(self, p, q):
        return self._root(p) == self._root(q)

    def union(self, p, q):
        i = self._root(p)
        j = self._root(q)
        if (self._sz[i] < self._sz[j]):
            self._id[i] = j
            self._sz[j] += self._sz[i]
        else:
            self._id[j] = i
            self._sz[i] += self._sz[j]

def addr_group():

    session=Session()
    r = session.execute('select max(addr_id) as addr_id from addr_send').fetchone()
    maxSize = (r.addr_id + 1)
    session.close()

    uf = AddrGroup(maxSize)

    import csv
    with open(config.ADDRESS_SET_CSV, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader, None) #skip header
        for p, q, z in reader:
            uf.union(int(p), int(q))

    f=open(config.ADDRESS_SET_UPDATE_SQL, 'w')
    f.write('DROP TABLE addr_g;\n')
    f.write('CREATE TABLE addr_g(id integer, group_id integer);\n')
    f.write('COPY  addr_g(id,	group_id)	FROM	stdin;\n')
    for pos, val in enumerate(uf._id):
        f.write('%d	%d\n' % (pos,val))
    f.write('\.\n')
 
    pickle.dump(uf,file(config.ADDR_GROUP,'w')) 
 
def addr_group_update():

    session=Session()
    r = session.execute('select max(addr_id) as addr_id from addr_send').fetchone()
    maxSize = (r.addr_id + 1)
    print maxSize
    session.close()


    uf = pickle.load(file(config.ADDR_GROUP))
    l = len(uf._id)
    uf._id += list(range(l,maxSize,1))
    uf._sz += [1] *(maxSize-l) 

    print len(uf._id) 

    try:
        import csv
        with open(config.ADDRESS_SET_UPDATE_CSV, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            for p, q in reader:
                uf.union(int(p), int(q))
    except:
         print p, q
         print len 

    f=open(config.ADDRESS_SET_UPDATE_SQL, 'w')
    f.write('DROP TABLE addr_g cascade;\n')
    f.write('CREATE TABLE addr_g(id integer, group_id integer);\n')
    f.write('COPY  addr_g(id,	group_id)	FROM	stdin;\n')
    for pos, val in enumerate(uf._id):
        f.write('%d	%d\n' % (pos,val))
    f.write('\.\n')
 
    pickle.dump(uf,file(config.ADDR_GROUP,'w')) 
 
