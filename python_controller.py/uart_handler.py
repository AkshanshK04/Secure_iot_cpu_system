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

              
    
              


    
