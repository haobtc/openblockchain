DROP FUNCTION delete_height(blkheight integer);
CREATE FUNCTION delete_height(blkheight integer) RETURNS void
    LANGUAGE plpgsql
    AS $$                                                                                                                     
    declare blkhash bytea;                                                                                                
    BEGIN
    blkhash = (select hash from blk where height=blkheight);                                                                                                                                                                                                                                                                                       
    perform delete_blk(blkhash);                                                                                                  
    END                                                                                                                       
$$;

CREATE FUNCTION delete_all_utx() RETURNS void                                                                                 
    LANGUAGE plpgsql                                                                                                          
    AS $$                                                                                                                     
    DECLARE txid integer;                                                                                                     
BEGIN                                                                                                                         
     FOR txid IN select id from utx LOOP                                                                                      
         perform delete_tx(txid);                                                                                             
     END LOOP;                                                                                                                
END;                                                                                                                          
$$; 

DROP FUNCTION delete_height_from(blkheight integer);
CREATE FUNCTION delete_height_from(blkheight integer) RETURNS void
    LANGUAGE plpgsql
    AS $$                                                                                                                     
    DECLARE blkhash bytea;
    DECLARE max_height integer;     
    DECLARE curheight integer;                                                                                              
    BEGIN
        max_height = (select max(height) from blk);   
        LOOP                                                                          
            IF blkheight <= max_height THEN
                curheight=max_height;
                blkhash = (select hash from blk where height=curheight);                                                                                                                                                                                                                                                                                       
                perform delete_blk(blkhash); 
                max_height = max_height - 1;
            ELSE
                return;
            END IF;   
        END LOOP;                                                                                                     
    END;                                                                                                                  
$$;

-- select count(id) from tx where id not in (select tx_id from blk_tx);

-- select id from utx order by id limit 5;
-- select id from tx where NOT EXISTS (select tx_id from blk_tx where blk_tx.tx_id = tx.id) limit 5;
-- select id from tx where NOT EXISTS (select tx_id from blk_tx where blk_tx.tx_id = tx.id) and EXISTS (select id from utx where utx.id = tx.id) order by id limit 5;
-- select * from tx where NOT EXISTS (select tx_id from blk_tx where blk_tx.tx_id = tx.id) and not EXISTS (select id from utx where utx.id = tx.id) order by id limit 5;


-- select count(id) from utx;
-- select count(id) from tx where NOT EXISTS (select tx_id from blk_tx where blk_tx.tx_id = tx.id);
-- select count(id) from tx where NOT EXISTS (select tx_id from blk_tx where blk_tx.tx_id = tx.id) and not EXISTS (select id from utx where utx.id = tx.id);
-- select count(id) from tx where NOT EXISTS (select tx_id from blk_tx where blk_tx.tx_id = tx.id) and EXISTS (select id from utx where utx.id = tx.id);
-- explain analyze select id from tx where NOT EXISTS (select tx_id from blk_tx where blk_tx.tx_id = tx.id);

drop FUNCTION fix_utx();
CREATE FUNCTION fix_utx() RETURNS void
AS $$
    DECLARE txid integer;        
    BEGIN
        FOR txid IN select id from tx where NOT EXISTS (select tx_id from blk_tx where blk_tx.tx_id = tx.id) and not EXISTS (select id from utx where utx.id = tx.id)  LOOP
            perform delete_tx(txid);
        END LOOP;
    END;
$$
LANGUAGE plpgsql;
