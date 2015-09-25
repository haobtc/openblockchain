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

create view vtx as select a.*,b.idx,c.height,c.time from tx a left join blk_tx b on(b.tx_id=a.id) left join blk c on (c.id=b.blk_id);