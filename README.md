# openblockchain

get a clean copy from github

git clone --recursive https://github.com/haobtc/openblockchain.git

or if you already cloned to local disk, 

git clone https://github.com/haobtc/openblockchain.git

then go to sub directory, update the submodule.

cd openblockchain/bitcoin

git submodule update --init --recursive

# create db

sudo apt-get install postgresql-client
sudo apt-get install postgresql

root#mkdir /usr/local/pgsql/data
root#chown postgres /usr/local/pgsql/data
root#su postgres
postgres$/usr/lib/postgresql/9.3/bin/initdb -D /usr/local/pgsql/data

You can now start the database server using:

    /usr/lib/postgresql/9.3/bin/postgres -D /data/chaindb/
or
    /usr/lib/postgresql/9.3/bin/pg_ctl -D /data/chaindb/ -l logfile start
or 
    /etc/init.d/postgresql start
    /etc/init.d/postgresql stop
    /etc/init.d/postgresql restart
    /etc/init.d/postgresql status


psql -U postgres -c "create database dbname"
or
createdb -U postgres dbname

psql -U postgres dbname < schema.sql

vi ~/.bitcoin/bitcoin.conf

server=1
rpcallowip=0.0.0.0/0
rpcuser=bitcoinrpc
rpcpassword=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
txindex=1
daemon=1


# build bitcoind

apt-get install build-essential libtool autotools-dev autoconf libssl-dev libboost-all-dev libdb-dev libdb++-dev pkg-config libpq-dev 

./autogen.sh

./configure  --disable-wallet --without-gui --disable-tests

make -j

./bitcoind -datadir=<bitcoin data directory> -daemon

#install for demo

apt-get install libleveldb1 libleveldb-dev

sudo pip install plyvel

#run api demo

cd api 

change RPC_URL and engine = create_engine('postgresql://postgres:c1u2u9z@@127.0.0.1:5433/test', echo=True) by your bitcoind and postgres server config

python demo.py



