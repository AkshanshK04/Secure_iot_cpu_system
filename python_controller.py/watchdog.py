""""
desc : software watchdog for the python controller process
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass   , field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING :
    from uart_handler import UARTHandler
    from alert_system import AlertSystem

logger = logging.getLogger("watchdog")

# health report
@dataclass
class HealthReport :
    timestamp : float = field (default_factory= time.time)
    uart_ok   : bool = True
    crc_ok    : bool = True
    alert_ok  : bool = True
    frame_rate_hz : float = 0.0
    crc_fail_rate : float = 0.0
    recovery_level : int = 0
    message    : str = "nominal"

#watchdog
class SystemWatchdog :
    """
    self healing watchdog for python controller
    """
    MAX_RECOVERY_LEVEL = 4
    
    def __init__(
            self,
            uart :        " UARTHandler",
            alert_system: "AlertSystem",
            frame_timeout_s: float = 5.0,
            crc_fail_thresh : float = 0.20,
            poll_interval_s : float = 1.0,
            )-> None:
        self.uart            = uart
        self.alert_system    = alert_system
        self.frame_timeout_s = frame_timeout_s
        self.crc_fail_thresh = crc_fail_thresh
        self.poll_interval_s = poll_interval_s

        self.last_frame_time  = time.time()
        self.prev_received    = 0
        self.prev_crc_fail    = 0
        self.recovery_level   = 0
        self.health           = HealthReport()
        self.stop_evt         = threading.Event()
        self.thread           = threading.Thread(
                                     target=self.run,
                                     name= " sys_watchdog",
                                     daemon = True
                                )
        
        def start(self) -> None :
            self.thread.start()
            logger.info ("System watchdog started (timeout = %1.f s)", self.frame_timeout_s)

        def stop (self) -> None :
            self.stop_evt.set()

        def notify_frame(self) -> None:
            """call this every time a valid frame is received"""
            self.last_frame_time  = time.time()
            self.recovery_level = 0

        @property
        def health(self) -> HealthReport :
            return self.health
        
        # main loop
        def run(self) -> None :
            while not self.stop_evt.is_set() :
                time.sleep(self.poll_interval_s)
                self.check()

        def check(self) -> None :
            now = time.time()
            stats = self.uart.stats()

            # frame rate
            new_frames = stats["received"] - self.prev_received
            frame_rate = new_frames / self.poll_interval_s
            self.prev_received = stats["received"]

            # crc fail rate
            new_fail  = stats["crc_fail"]
            self.prev_crc_fail = stats["crc_fail"]
            total = new_frames + new_fail
            crc_rate = (new_fail / total ) if total > 0 else 0.0

            # frame timeout
            silent_s = now - self.last_frame_time
            uart_ok  = silent_s < self.frame_timeout_s
            crc_ok   = crc_rate < self.crc_fail_thresh

            self.health = HealthReport(

                timestamp     = now,
                uart_ok       = uart_ok,
                crc_ok        = crc_ok,
                alert_ok      = True,
                frame_rate_hz = frame_rate,
                crc_fail_rate = crc_rate ,
                recovery_level= self.recovery_level,
                message       = "nominal" if (uart_ok and crc_ok ) else "degraded"

            )


            if uart_ok and crc_ok :
                if self.recovery_level > 0 :
                    logger.info (" System nominal - recovery level reset")
                    self.recovery_level = 0
                return
            
            # fault detected -> escalating recovery
            self.recovery_level = min (
                self.recovery_level +1 , self.MAX_RECOVERY_LEVEL

            )
            level  = self.recovery_level
            logger.warning (
                "WDT fault : uart_ok = %s   crc_ok = %s  silent=%.1fs  crc_rate=%.1f%% "
            "-> recovery level %d",
            uart_ok, crc_ok, silent_s, crc_rate*100, level
            )

            if level == 1:
                self.recover_l1()
            elif level == 2 :
                self.recover_l2()
            elif level == 3:
                self.recover_l3()
            elif level >= 4 :
                self.recover_l4()

        # recovery actions
        def recover_l1 ( self) -> None :
            """level 1 :  send STATUS probe to esp32"""
            logger.info("WDT L1 : sending STATUS probe")
            self.uart.send_command("STATUS")

        def recover_l2 ( self) -> None :
            """level 2 : clear alert state and flush UART buffers"""
            logger.warning("WDT L2 : clearing alert state + flushing UART")
            self.alert_system.clear_alerts()
            self.uart.send_command("RESET")
            #attempt UART port flush
            try :
                if self.uart.ser and self.uart.ser.is_open :
                    self.uart.ser.reset_input_buffer()
                    self.uart.ser.reset_output_buffer()
            except Exception as exc :
                logger.error("WDT L2 flush error : %s", exc)
        
        def recover_l3(self) -> None :
            """level 3 : reconnect UART"""
            logger.error("WDT L3: reconnecting UART")
            try :
                self.uart.disconnect()
                time.sleep(1.0)
                success = self.uart.connect (retries = 3, retry_delay=1.0)
                if success :
                    self.last_frame_time = time.time()
                    logger.info("WDT L3: UART reconnected")
                else :
                    logger.error("WDT L3: UART reconnect failed")
            except Exception as exc :
                logger.error("WDT L3 error : %s", exc)
                


