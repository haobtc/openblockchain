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

<<<<<<< HEAD
drop FUNCTION check_tx();
CREATE FUNCTION check_tx() RETURNS BOOL
=======
drop FUNCTION check_tx_count();
CREATE FUNCTION check_tx_count() RETURNS BOOL
>>>>>>> 5177f001d06c3e6421eef4a7a518f1082386c680
AS $$
    DECLARE tx_count bigint;        
    DECLARE utx_count bigint;   
    DECLARE blk_tx_count bigint;   
    DECLARE blk_tx_id_count bigint;   

    BEGIN
        blk_tx_count = (select sum(blk.tx_count) from blk);
        blk_tx_id_count = (select count(distinct(tx_id)) from blk_tx);
        IF blk_tx_count != blk_tx_id_count+2 THEN
            RAISE LOG 'blk_tx_count(%) != blk_tx_id_count(%) ', blk_tx_count, blk_tx_id_count;
            return FALSE;
        END IF;

        tx_count = (select count(1) from tx);
        utx_count = (select count(1) from utx);
        IF tx_count + 2 != utx_count + blk_tx_count
        THEN
            RAISE LOG 'tx_count(%) + 2 != utx_count(%) + blk_tx_count(%)', tx_count, utx_count, blk_tx_count;
            return FALSE;
        END IF;

        RAISE LOG 'pass tx check % % %', blk_tx_count, tx_count, utx_count;
        return TRUE;
    END;
$$
LANGUAGE plpgsql;



<<<<<<< HEAD
drop FUNCTION check_blk();
CREATE FUNCTION check_blk() RETURNS BOOL
=======
drop FUNCTION check_blk_count();
CREATE FUNCTION check_blk_count() RETURNS BOOL
>>>>>>> 5177f001d06c3e6421eef4a7a518f1082386c680
AS $$
    DECLARE blk_height bigint;        
    DECLARE blk_count bigint;   
    DECLARE blk_id_count bigint;   

    BEGIN
        blk_height = (select max(height) from blk);
        blk_count = (select count(1) from blk);
        blk_id_count = (select count(distinct(blk_id)) from blk_tx);
        IF blk_count != blk_id_count THEN
            RAISE LOG 'blk_count != blk_id_count ';
            return FALSE;
        END IF;

        IF blk_count != blk_height + 1
        THEN
            RAISE LOG 'blk_count != blk_height + 1';
            return FALSE;
        END IF;

        RAISE LOG 'pass blk check';
        return TRUE;
    END;
$$
LANGUAGE plpgsql;

drop FUNCTION check_db();
CREATE FUNCTION check_db() RETURNS BOOL
AS $$
    DECLARE blk_ok BOOL; 
    DECLARE tx_ok BOOL; 
    BEGIN
        blk_ok = (select check_blk_count());
        IF NOT blk_ok THEN
            return FALSE;
        END IF;

        tx_ok = (select check_tx_count());
        IF NOT tx_ok THEN
            return FALSE;
        END IF;

        return TRUE;
    END;
$$
LANGUAGE plpgsql;

