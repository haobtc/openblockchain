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