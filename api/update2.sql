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
            END IF;   
        END LOOP;                                                                                                     
    END;                                                                                                                  
$$;