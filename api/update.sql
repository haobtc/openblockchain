drop view balance;
drop view vout;

create view vout as
SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    a.value,
    a.tx_idx as out_idx,
    c.tx_idx as in_idx
   FROM txout a
     LEFT JOIN tx b ON b.id = a.tx_id
     LEFT JOIN txin c ON c.prev_out = b.hash AND c.prev_out_index = a.tx_idx
     LEFT JOIN tx e ON e.id = c.tx_id
     LEFT JOIN addr_txout f ON f.txout_id = a.id
     LEFT JOIN addr g ON g.id = f.addr_id;

create view balance as SELECT vout.addr_id, sum(vout.value) AS value FROM vout WHERE vout.txin_id IS NULL GROUP BY vout.addr_id;

Drop view vtx;
ALTER TABLE tx DROP COLUMN ip;
ALTER TABLE tx ADD COLUMN ip text;

create view vtx as select a.*,b.idx,c.height,c.time from tx a left join blk_tx b on(b.tx_id=a.id) left join blk c on (c.id=b.blk_id);

CREATE TABLE addr_tx (addr_id integer NOT NULL, tx_id integer NOT NULL, constraint u_constrainte unique (addr_id, tx_id));

CREATE RULE "addr_tx_on_duplicate_ignore" AS ON INSERT TO "addr_tx"  WHERE EXISTS(SELECT 1 FROM addr_tx  WHERE (addr_id, tx_id)=(NEW.addr_id, NEW.tx_id))  DO INSTEAD NOTHING;


DROP FUNCTION update_addr_balance(txid integer);
CREATE FUNCTION update_addr_balance(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE o RECORD;
BEGIN

    FOR o IN select addr_id, value from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance - o.value), spent_value=(spent_value+o.value) where id=o.addr_id;
    END LOOP;

    FOR o IN select addr_id, value from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance + o.value), recv_value=(recv_value+o.value)  where id=o.addr_id;
    END LOOP;


    FOR o IN select distinct addr_id from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set spent_count=(spent_count+1) where id=o.addr_id;
       insert into addr_tx (addr_id,tx_id) values(o.addr_id, txid);
    END LOOP;

    FOR o IN select distinct addr_id from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set recv_count=(recv_count+1) where id=o.addr_id;
       insert into addr_tx (addr_id,tx_id) values(o.addr_id, txid);
    END LOOP;
END;
$$;

drop FUNCTION rollback_addr_balance(txid integer);
CREATE FUNCTION rollback_addr_balance(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE o RECORD;
BEGIN
    FOR o IN select addr_id, value from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance + o.value), spent_value=(spent_value-o.value) where id=o.addr_id;
    END LOOP;

    FOR o IN select addr_id, value from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set balance=(balance - o.value), recv_value=(recv_value-o.value)  where id=o.addr_id;
    END LOOP;


    FOR o IN select distinct addr_id from vout where txin_tx_id=txid and addr_id is not NULL LOOP
       update addr set spent_count=(spent_count-1) where id=o.addr_id;
       delete from addr_tx where addr_id=o.addr_id and tx_id=txid;
    END LOOP;

    FOR o IN select distinct addr_id from vout where txout_tx_id=txid and addr_id is not NULL LOOP
       update addr set recv_count=(recv_count-1) where id=o.addr_id;
       delete from addr_tx where addr_id=o.addr_id and tx_id=txid;
    END LOOP;
END;
$$;

ALTER TABLE addr DROP COLUMN recv_value ;
ALTER TABLE addr DROP COLUMN recv_count ;
ALTER TABLE addr DROP COLUMN spent_value;
ALTER TABLE addr DROP COLUMN spent_count;

ALTER TABLE addr ADD COLUMN recv_value bigint    default 0;
ALTER TABLE addr ADD COLUMN recv_count integer   default 0;
ALTER TABLE addr ADD COLUMN spent_value bigint   default 0;
ALTER TABLE addr ADD COLUMN spent_count integer  default 0;

CREATE MATERIALIZED VIEW vvout as SELECT g.address, g.id as addr_id, a.id AS txout_id, c.id AS txin_id, e.id AS txin_tx_id, b.id AS txout_tx_id, a.value FROM txout a LEFT JOIN tx b ON b.id = a.tx_id left join txin c on (c.prev_out=b.hash and c.prev_out_index=a.tx_idx) left JOIN tx e ON e.id = c.tx_id left JOIN addr_txout f on f.txout_id=a.id left JOIN addr g on g.id=f.addr_id;
CREATE INDEX vvout_address on vvout USING btree (addr_id);

insert into addr_tx select distinct addr_id,txout_tx_id as tx_id from vvout where addr_id is not NULL;
insert into addr_tx select distinct addr_id,txin_tx_id as tx_id from vvout where addr_id is not NULL and txin_tx_id is not NULL;

CREATE MATERIALIZED VIEW addr_recv as SELECT vvout.addr_id, sum(vvout.value) AS recv_value, count(distinct vvout.txout_tx_id) as txout_count, count(distinct txin_tx_id) as txin_count FROM vvout GROUP BY vvout.addr_id;
CREATE INDEX addr_recv_address on addr_recv USING btree (addr_id);
CREATE MATERIALIZED VIEW addr_spent as SELECT vvout.addr_id, sum(vvout.value) AS spent_value, count(distinct vvout.txout_tx_id) as spent_txout_count, count(distinct txin_tx_id) as spent_txin_count FROM vvout where vvout.txin_tx_id is not NULL GROUP BY vvout.addr_id;
CREATE INDEX addr_spent_address on addr_spent USING btree (addr_id);

update addr set recv_value=a.recv_value, recv_count=a.txout_count from addr_recv a where addr.id=a.addr_id;
update addr set spent_value=a.spent_value, spent_count=a.spent_txin_count from addr_spent a where addr.id=a.addr_id;

DROP MATERIALIZED VIEW addr_recv;
DROP MATERIALIZED VIEW addr_spent;
DROP MATERIALIZED VIEW vvout;

create view addr_tx_confirmed as select a.tx_id,a.addr_id from addr_tx a join blk_tx b on (b.tx_id=a.tx_id);
create view addr_tx_unconfirmed as select a.tx_id,a.addr_id from addr_tx a join utx b on (b.id=a.tx_id);

CREATE RULE "utx_on_duplicate_ignore" AS ON INSERT TO "utx"  WHERE EXISTS(SELECT 1 FROM utx WHERE (id)=(NEW.id))  DO INSTEAD NOTHING;

CREATE RULE "addr_txout_on_duplicate_ignore" AS ON INSERT TO "addr_txout"  WHERE EXISTS(SELECT 1 FROM addr_txout WHERE (addr_id,txout_id)=(NEW.addr_id, NEW.txout_id))  DO INSTEAD NOTHING;

DROP FUNCTION delete_tx(txid integer);
CREATE FUNCTION delete_tx(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE ntx RECORD;
BEGIN
     FOR ntx IN select txin_tx_id from vout where txout_tx_id=$1 LOOP
         perform delete_tx(ntx.txin_tx_id);
     END LOOP;
     perform  rollback_addr_balance($1);
     delete from addr_txout where txout_id in (select id from txout where tx_id=$1);
     delete from txin where tx_id=$1;
     delete from txout where tx_id=$1;
     delete from tx where id=$1;
     delete from utx where id in ($1);
END;
$$;
