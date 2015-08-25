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

change RPC_URL and app.config['SQLALCHEMY_DATABASE_URI'] by your bitcoind and postgres server config

python demo.py

