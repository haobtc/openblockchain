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