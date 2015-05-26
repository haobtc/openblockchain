from sqlalchemy import create_engine


class database:
    def __init__(self, netname):
        self.engine = create_engine(
            'postgresql://postgres@127.0.0.1:5432/webbtc')
        self.nettype = 1
        self.name = 'pq_bitcoin'
