import random
import socket
import time
import simplejson
import re
import traceback
import sys
import threading
import queue

class ThreadShuttingDown(Exception):
    def __init__(self, nameOfThread, time):
        self.name = nameOfThread
        self.time = time
    def __str__(self):
        return "{0} has been shut down! Tried to call readMsg at {1}".format(self.name, self.time) 

class IRC_reader(threading.Thread):
    def __init__(self, serverSock): #host, port):
        threading.Thread.__init__(self)
        #self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.conn.settimeout()
        #self.host = host
        #self.port = port
        self.sock = serverSock
        self.ready = True
        self.linebuffer = b""
        
        self.error = None
        
        self.buffer = queue.Queue()
        
    def run(self):
        #self.conn.connect(self.host, self.port)
        
            while self.ready == True:
                try:
                    data = self.sock.recv(1024)
                    time.sleep(0.01)
                except Exception as error:
                    print()
                    print("ERROR: "+str(error))
                    print()
                    self.error = traceback.format_exc()

                    self.ready = False
                    break
                else:
                    if data != b"":
                        # print("RAWIN: %s" % data)
                        self.linebuffer += data

                    lines = self.linebuffer.split(b"\n")
                    self.linebuffer = lines.pop()

                    for line in lines:
                        # print "IN: %s" % line
                        line = line.rstrip()  # Strip whitespace to the right
                        self.buffer.put(line.decode("utf-8", errors="replace"), True)
            print("ReadThread is down!")
        
    
    def readMsg(self):
        if self.ready == False:
            raise ThreadShuttingDown("readThread", time.time())
        else:
            return self.buffer.get_nowait()


class IRC_writer(threading.Thread):
    def __init__(self, serverSock):#, host, port):
        threading.Thread.__init__(self)
        
        #self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.conn.settimeout()
        #self.host = host
        #self.port = port
        self.sock = serverSock
        self.ready = True
        self.line = ""
        self.signal = False
        self.died = False
        
        self.error = None
        self.buffer = queue.Queue()
        
    def run(self):
        #self.conn.connect(self.host, self.port)
        
        while self.ready == True:
            try:
                toSend = self.buffer.get_nowait()
                send_away = toSend.encode("utf-8", "replace")

                self.sock.send(send_away)
                #print(len(send_away))

                if len(send_away) > 250:
                    time.sleep(3)
                else:
                    time.sleep(2)
                #print "SENT: "+toSend
                
                
            except queue.Empty:
                # an attempt to fix the bug that causes the writeThread to hang indefinitely because it receives no more data from the Queue
                if self.signal == False:
                    # it's empty? oh well, better luck next time
                    time.sleep(0.05) 
                else:
                    # the signal to turn the thread off has been set? Ok, time to break out of the loop
                    self.ready = False
                    break
                    
            except Exception as error:
                print()
                print("ERROR: "+str(error))
                print()
                self.error = traceback.format_exc()
                
                self.ready = False
                break
            else:
                if self.signal == True and self.buffer.empty():
                    self.ready = False
                    break
            #else:
            #    self.ready = False
            #    self.sock.close()
            #    print "SHIT GOES LOSE, WE CAN'T SEND ANYTHING TO SERVER"
        print("SendThread is down!")
    
    def waitUntilEmpty(self):
        self.buffer.join()
    
    def sendMsg(self, msg, priority = False):
        msg = msg.replace(chr(13), " ")
        msg = msg.replace(chr(10), " ")
        self.buffer.put(msg + "\r\n")