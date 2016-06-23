#spent txout table
CREATE TABLE stxo (
    address text NOT NULL,
    addr_id integer,
    txout_id      integer,
    txin_id       integer,
    txin_tx_id    integer,
    txout_tx_id   integer,
    value         bigint ,
    out_idx       integer,
    in_idx        integer,
    txout_tx_hash bytea,
    txin_tx_hash  bytea,
    height        integer,
    time          bigint
);

#spent txout view
CREATE or REPLACE VIEW v_stxo AS
 SELECT g.address,
    g.id AS addr_id,
    a.id AS txout_id,
    c.id AS txin_id,
    e.id AS txin_tx_id,
    b.id AS txout_tx_id,
    a.value,
    a.tx_idx AS out_idx,
    c.tx_idx AS in_idx,
    b.hash AS txout_tx_hash,
    e.hash AS txin_tx_hash,
    blk.height,
    blk.time
   FROM (((((((txout a
     LEFT JOIN tx b ON ((b.id = a.tx_id)))
     LEFT JOIN txin c ON (((c.prev_out = b.hash) AND (c.prev_out_index = a.tx_idx))))
     LEFT JOIN tx e ON ((e.id = c.tx_id)))
     LEFT JOIN addr_txout f ON ((f.txout_id = a.id)))
     LEFT JOIN addr g ON ((g.id = f.addr_id)))
     JOIN blk_tx ON ((blk_tx.tx_id = a.tx_id)))
     JOIN blk ON ((blk.id = blk_tx.blk_id)))
  WHERE (c.id IS NOT NULL);

#update spent txout table
CREATE or REPLACE FUNCTION update_stxo() RETURNS void
    LANGUAGE plpgsql
    AS $$
    DECLARE max_blk_height integer;
    DECLARE max_saved_height integer;
BEGIN
    max_blk_height = (select max(height) from blk);
    max_saved_height = (select max(height) from stxo);
    insert into stxo SELECT * from v_stxo where height<=(max_blk_height - 10) and height>max_saved_height;
END;
$$;

CREATE TABLE addr_tag (
    id integer,
    addr text,
    name text,
    url text);
CREATE  TABLE walletexplorer_tag (id serial primary key, addr text, tag text, link text, group_id integer);

CREATE INDEX addr_group_id_index ON addr USING btree (group_id);
