# openblockchain

git clone --recursive https://github.com/haobtc/openblockchain.git

# create db
psql -U postgres -c "create database bitcoin"

psql -U postgres bitcoin <schema.sql

# build bitcoind

apt-get install build-essential libtool autotools-dev autoconf libssl-dev libboost-all-dev libdb-dev libdb++-dev pkg-config libpq-dev 

./autogen.sh
./configure  --disable-wallet --without-gui --disable-tests
make -j

./bitcoind -datadir=<bitcoin data directory> -daemon

#run api demo

cd api 

change RPC_URL and engine = create_engine('postgresql://postgres:c1u2u9z@@127.0.0.1:5433/test', echo=True) by your bitcoind and postgres server config

python demo.py

#install

apt-get install libleveldb1 libleveldb-dev
sudo pip install plyvel

