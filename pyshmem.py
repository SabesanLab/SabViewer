import mmap
import numpy as np
import socket
import time
import sys

from threading import Thread
    
def do_listen(fn_callback):
   #fn_callback=args[0]

   listen_address=('localhost',50000); #('127.0.0.1',27015);
   done=False

   while done==False:# Allow connect/reconnect forever

     print('Waiting for connection')
            
     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # prevent address in use error
        s.bind(listen_address)
        s.listen(1)
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while done==False:
                data = conn.recv(1024) # Don't think this number matters too much

                if len(data)==0:
                    time.sleep(0.1)
                    continue
                    
                print(data)

                if data==b'reset':
                    done=False
                    break
          
                elif data==b'quit':
                    done=True
                    sys.exit()
                    break
                    
                elif b'next' in data:
                    amt=int(data[5:])
                    fn_callback('next',amt)
                    
                elif data[0:4]==b"send":
                    str_dim=data[5:]
                    dims=str_dim.split(b',');
                    dims = np.array( [int(dim1) for dim1 in dims] )
                    #print (dims)

                    size_single = 4
                    size_total=np.prod(dims)*size_single
                    
                    shmem = mmap.mmap(-1, size_total ,"shm")
                    shmem.seek(0)
                    buf = shmem.read(size_total)
                    data = np.frombuffer(buf, dtype=np.float32).reshape(dims)
                    shmem.close()
                    
                    fn_callback('data',data)
                    
                    break
            
     
def tester(data):
    print( np.shape(data), data )

if __name__ == '__main__':
    listener_thread = Thread(target=do_listen, args=[tester] )
    listener_thread.start()
    print('Running ok')