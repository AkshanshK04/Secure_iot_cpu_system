"""
desc: UART communication handler for esp 32 sensor node
"""
from __future__ import annotations

import threading
import time
import queue
import logging
from dataclasses import dataclass, field
from typing import  Optional

import serial 
import serial.tools.list_ports

from crc import verify_frame
from encrypt import decrypt_16

logger = logging.getLogger(" uart_handler")

# data model

@dataclass
class SensorFrame :
    """ A fully encoded and verified sensor frame"""
    seq :       int     #sequence counter 0-255
    enc_raw :   int     #Encrypted 16-b value (for audit)
    sensor_val: int     #decrypted 16-b sensor value
    timestamp : float = field(default_factory=time.time)
    crc_ok :    bool = True

# UART Handler 
class UARTHandler :
    """ thread safe UART handler"""
    FRAME_START = b'$'
    FRAME_END   = b'\n'

    def __init__(
            self,
            port :    str = "/dev/ttyUSB0",
            baud :    int = 115200,
            q_size:   int = 128,
            timeout_s: float = 1.0,
    ) -> None :
            self.port   = port
            self.baud   = baud
            self.timeout_s = timeout_s

            self.ser :    Optional[serial.Serial] = None
            self.rx_queue : queue.Queue[SensorFrame] = queue.Queue (maxsize= q_size)
            self.stop_evt = threading.Event ()
            self.rx_thread = threading.Thread( target = self.rx_loop, 
                                              name = " uart_rx", daemon = True)
            self.lock  = threading.Lock()

            #stats
            self.frames_received = 0
            self.frames_crc_fail = 0
            self.frames_parse_err = 0

     # connection management 
    def connect ( self, retries :int =5, retry_delay : float = 2.0) -> bool :
         """
         Open the serial port with retry logic
         """       
         for attempt in range (1, retries+1 ) :
            try :
                self.ser = serial.Serial (
                    port= self.port,
                    baudrate=   self.baud,
                    bytesize= serial.EIGHTBITS,
                    parity= serial.PARITY_NONE,
                    stopbits= serial.STOPBITS_ONE,
                    timeout = self.timeout_s,
                   )

                logger.info ("Connected to %s @ %d baud ", self.port, self.baud)
                self.rx_thread.start ()
                return True
            except serial.SerialException as exc :
                 logger.warning (" Attempt %d / %d failed : %s", attempt, retries, exc)
                 time.sleep(retry_delay)

         logger.error ("Could not open serial post %s after %d attempts",
                      self.port, retries)
         return False
    
    def disconnect (self) -> None :
         """signal the RX thread to stop and colse the port """
         self.stop_evt.set()
         if self.rx_thread.is_alive() :
              self.rx_thread.join(timeout=3.0)
         if self.ser and self.ser.is_open :
              self.ser.close()
              logger.info("UART port closed")

              
     # frame parsing
    @staticmethod
    def parse_frame (line: str) -> Optional[tuple[int,int,int,int]] :
         """" parse an ASCII frmae line into ( seq, enc_hi, enc_lo, crc)"""

         line = line.strip().lstrip('$').strip()
         parts = line.split(',')
         if len(parts) != 4 :
              return None
         
         try :
              seq    = int(parts[0], 16)
              enc_hi = int(parts[1], 16)
              enc_lo = int(parts[2], 16)
              crc    = int(parts[3], 16)
              return seq, enc_hi, enc_lo, crc
         except ValueError :
              return None
         
     # RX thread
    def rx_loop (self) -> None :
         """ bg thread : continuously read frames from the serial port """
         logger.info(" RX thread started")
         buf = b""

         while not self.stop_evt.is_set(0) :
              if not self.ser or not self.ser.is_open :
                   time.sleep(0.1)
                   continue
              
              try :
                   chunk = self.ser.readline() 

              except serial.SerialException as exc :
                   logger.error (" Serial read error : %s", exc)
                   time.sleep(0.5)
                   continue
              
              if not chunk :
                   continue
              
              line = chunk.decode ("ascii", errors = "ignore" ).strip()
              if not line.startswith("$") :
                   # could be a debug log line from esp 32
                   logger.debug("ESP32 log : %s", line) 
                   continue
              
              parsed = self.parse_frame(line)
              if parsed is None :
                   self.frames_parse_err += 1
                   logger.warning("Parse error : '%s'", line)
                   continue
              
              seq, enc_hi, enc_lo , recv_crc = parsed

              #crc verification
              if not verify_frame ( seq, enc_hi, enc_lo, recv_crc) :
                   self.frames_crc_fail += 1
                   logger.warning ("CRC fail seq = %02X enc = %02X%02X  crc = %02X",
                                   seq, enc_hi, enc_lo, recv_crc)
                   continue
              
              #decrypt
              enc_word = ( enc_hi << 8) | enc_lo
              sensor_16 = decrypt_16(enc_word, seq)

              frame = SensorFrame (
                   seq = seq,
                   enc_raw= enc_word,
                   sensor_val = sensor_16 ,
              )

              self.frames_received +=1

              try :
                   self.rx_queue.put_nowait(frame)
              except queue.Full :
                   #discard oldest to make room
                   try :
                        self.rx_queue.get_nowait() 
                   except queue.Empty :
                        pass
                   self.rx_queue.put_nowait(frame)
                   logger.warning("RX queue full - oldest frame discarded")

         logger.info ("RX thread stopped")

     # public api
    def get_frame ( self, timeout: float = 2.0) -> Optional[SensorFrame] :
          """
          block until a decoded frame is available 
          returns :
               SensorFrame 
          """
          try :
               return self.rx_queue.get (timeout=timeout)
          except queue.Empty :
               return None
          
    def send_command ( self, cmd : str) -> bool :
         """
         send a command string to the esp32

         """
         with self.lock :
              if not self.ser or not self.ser.is_open :
                   logger.error (" Cannot send command - port not open")
                   return False
              
              try :
                   payload = (cmd.strip() + "\r\n").encode("ascii")
                   self.ser.write(payload)
                   logger.debug("->ESP32 : %s", cmd.strip())
                   return True
              
              except serial.SerialException as exc :
                   logger.error("Send failed : %s", exc)
                   return False
              
              
    def stats( self) -> dict :
         return {
              "received" : self.frames_received,
              "crc_fail" : self.frames_crc_fail,
              "parse_err" : self.frames_parse_err,
              "queue_len" : self.rx_queue.qsize(),
         }
    
    @staticmethod
    def list_ports () -> list[str] :
         """
         return a list of available serial port names
         """
         return [p.device for p in serial.tools.list_ports.comports()]
    
         
              
                                



         

     
              


    
