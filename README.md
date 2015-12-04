# openblockchain

get a clean copy from github

git clone --recursive https://github.com/haobtc/openblockchain.git

or if you already cloned to local disk, 

git clone https://github.com/haobtc/openblockchain.git

then go to sub directory, update the submodule.

cd openblockchain/bitcoin

git submodule update --init --recursive

# create db

#http://www.postgresql.org/download/linux/ubuntu/

sudo apt-get install postgresql-9.4

root#mkdir /chain/pg/
root#chown postgres /chain/pg/
root#su postgres
postgres$/usr/lib/postgresql/9.4/bin/initdb -D /chain/pg/

You can now start the database server using:

    /usr/lib/postgresql/9.4/bin/postgres -D /chain/pg/
or
    /usr/lib/postgresql/9.3/bin/pg_ctl -D /chain/pg/ -l logfile start
or 
    /etc/init.d/postgresql start
    /etc/init.d/postgresql stop
    /etc/init.d/postgresql restart
    /etc/init.d/postgresql status

sudo adduser dbuser
in postgres command:
CREATE USER dbuser WITH PASSWORD 'xxxxx';
CREATE DATABASE btcdb OWNER dbuser;
GRANT ALL PRIVILEGES ON DATABASE btcdb to dbuser;

pg_restore -j 3 -d btcdb btcdb.file

vi ~/.bitcoin/bitcoin.conf

server=1
rpcuser=bitcoinrpc
rpcpassword=xxxx
daemon=1
txindex=1


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

cp config_sample.py config.py 

modify config.py as server setting

gunicorn -w 4 -k gevent -b 0.0.0.0:5000 explorer_api:app
gunicorn -w 4 -k gevent -b 0.0.0.0:9005 blockstore_api:app





