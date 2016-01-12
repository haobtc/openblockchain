ALTER TABLE blk ADD COLUMN recv_time BIGINT;
ALTER TABLE blk ADD COLUMN pool_id int;
ALTER TABLE blk ADD COLUMN orphan bool;

CREATE TABLE rtx ( id integer NOT NULL);

CREATE OR REPLACE FUNCTION check_blk_count() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE blk_count1 integer;
    DECLARE blk_count2 integer;
BEGIN
    blk_count1 = (select count(1) from blk where orphan=false);
    blk_count2 = (select max(height)+1 from blk where orphan=false);
    if blk_count1 != blk_count2 then return false; end if;
    return true;
END;
$$;


CREATE OR REPLACE FUNCTION check_tx_count() RETURNS boolean
    LANGUAGE plpgsql
    AS $$
    DECLARE tx_count1 integer;
    DECLARE tx_count2 integer;
    DECLARE tx_count3 integer;
    DECLARE max_blk_id integer;
    DECLARE max_id record;
BEGIN
    max_blk_id = (select max(id) from blk);
    for max_id in (select blk_id,tx_id from blk_tx where blk_id<(max_blk_id-6) and orphan=false order by tx_id desc limit 1) loop
    tx_count1 = (select sum(tx_count) from blk where id<=max_id.blk_id);
    tx_count2 = (select count(1) from tx a join blk_tx b on (b.tx_id=a.id) join blk c on (c.id=b.blk_id and c.orphan=false) left join utx d on(d.id=a.id) where d.id is NULL and a.id<=max_id.tx_id and b.blk_id<=max_id.blk_id);

    tx_count3 = (select count(a.tx_id) from blk_tx a join blk b on (b.id=a.blk_id and b.orphan=false)  where a.blk_id<=max_id.blk_id);
    if tx_count1 != tx_count2 then return false; end if;
    if tx_count3 != tx_count2 then return false; end if;
    end loop;
    return true;
END;
$$;


CREATE OR REPLACE FUNCTION delete_blk(blkhash bytea) RETURNS void
    LANGUAGE plpgsql
    AS $$
    declare blkid integer;
    declare txid integer;
    BEGIN
    blkid=(select id from blk where hash=blkhash);
    txid=(select tx_id from blk_tx where blk_id=blkid and idx=0);
    insert into utx select tx_id from blk_tx where blk_id=blkid;
    update blk set orphan=true where id=blkid;
    perform delete_tx(txid);
    END
$$;

CREATE OR REPLACE FUNCTION get_confirm(txid integer) RETURNS integer
    LANGUAGE plpgsql
    AS $_$
    DECLARE tx_height integer;
    DECLARE max_height integer;
BEGIN
    tx_height=(select c.height from tx a join blk_tx b on(b.tx_id=a.id) join blk c on (c.id=b.blk_id and c.orphan=false) where a.id=$1 order by c.height asc limit 1);
    max_height=(select max(height) from blk);
    return (max_height-tx_height+1);
END;
$_$;



CREATE OR REPLACE VIEW utxo AS
 SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    b.hash AS txout_txhash,
    a.value,
    a.tx_idx,
    blk.height,
    blk."time",
    a.pk_script
   FROM (((((((txout a
     LEFT JOIN tx b ON ((b.id = a.tx_id)))
     LEFT JOIN txin c ON (((c.prev_out = b.hash) AND (c.prev_out_index = a.tx_idx))))
     LEFT JOIN tx e ON ((e.id = c.tx_id)))
     LEFT JOIN addr_txout f ON ((f.txout_id = a.id)))
     LEFT JOIN addr g ON ((g.id = f.addr_id)))
     LEFT JOIN rtx h ON ((h.id = b.id)))
     JOIN blk_tx ON ((blk_tx.tx_id = a.tx_id)))
     JOIN blk ON ((blk.id = blk_tx.blk_id and blk.orphan=false))
  WHERE (c.id IS NULL) and (h.id is NULL);


CREATE OR REPLACE VIEW vtx AS
 SELECT a.id,
    a.hash,
    a.version,
    a.lock_time,
    a.coinbase,
    a.tx_size,
    a.in_count,
    a.in_value,
    a.out_count,
    a.out_value,
    a.fee,
    a.recv_time,
    a.ip,
    b.idx,
    c.height,
    c."time"
   FROM ((tx a
     LEFT JOIN blk_tx b ON ((b.tx_id = a.id)))
     LEFT JOIN blk c ON ((c.id = b.blk_id and c.orphan=false)));


CREATE OR REPLACE FUNCTION delete_tx(txid integer) RETURNS void
    LANGUAGE plpgsql
    AS $_$
    DECLARE ntx RECORD;
BEGIN
     FOR ntx IN select txin_tx_id from vout where txout_tx_id=$1 LOOP
         perform delete_tx(ntx.txin_tx_id);
     END LOOP;
     perform  rollback_addr_balance($1);
     delete from addr_txout where txout_id in (select id from txout where tx_id=$1);
     delete from utx where id in ($1);
     insert into rtx (id) values($1);
END;
$_$;

CREATE OR REPLACE RULE "rtx_on_duplicate_ignore" AS ON INSERT TO "rtx"  WHERE EXISTS(SELECT 1 FROM utx WHERE (id)=(NEW.id))  DO INSTEAD NOTHING; 



ALTER TABLE tx ADD COLUMN flag INT; 
