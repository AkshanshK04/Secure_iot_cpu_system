'''
action : 
    unified alert dispatcher 
    receives alert decision from cpu interface

'''

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Callable

logger = logging.getLogger ("alert_system")

# severity 
class Severity (IntEnum) :
    INFO = 0
    WARNING = 1
    CRITICAL = 2

# alert record
@dataclass
class Alert :
    severity : Severity
    sensor_val : int
    seq : int
    message : str
    timestamp : float = field ( default_factory=time.time)
    dispatched : dict = field( default_factory=dict)

# alert system
class AlertSystem :
    '''
    central alert dispatcher
    '''
    def __init__(
            self,
            threshold :   int  = 0x0B00 ,
            rate_limit:   float = 30.0,
            critical_mult : float = 1.5, 
    ) -> None :
        
        self.threshold  = threshold
        self.rate_limit = rate_limit
        self.critical_mult = critical_mult

        self.channels : dict[ str, Callable[[Alert], None]] = {}
        self.last_fired : dict[str, float] = {}
        self.history : list[Alert] = {}
        self.lock = threading.Lock()
        self.alert_count = 0
    
    def add_channel (self, name : str, handler: Callable[[Alert], None]) -> None :
        ''' register an alert channel handler'''

        self.channels[name] = handler
        self.last_fired[name] = 0.0
        logger.info (" Alert channel registered : %s", name )
    
    def remove_channel (self, name :str ) -> None :
        self.channels.pop (name, None)
        self.last_fired.pop(name, None)

    # severity classification
    def classify ( self, sensor_val : int) -> Optional [Severity] :

        if sensor_val > int (self.threshold * self.critical_mult):
            return Severity.CRITICAL
        elif sensor_val > self.threshold :
            return Severity.WARNING 
        return None
    
    # main dispatch 
    def evaluate_n_dispatch ( self, sensor_val : int, seq: int) -> Optional[Alert] :

        severity = self.classify(sensor_val)
        if severity is None :
            logger.debug ( " seq = %02X   val = 0x%04X -> below threshlod, no alert ", seq, sensor_val)
            return None
        
        now = time.time()

        message = (
            f"[{severity.name}] Sensor breach :"
            f" val = 0x{sensor_val : 04X}  ({sensor_val})"
            f" threshold = 0x{self.threashold:04X}  seq = {seq:#04X}"

        )

        alert = Alert (severity= severity, sensor_val=sensor_val,
                       seq = seq, message=message, timestamp = now)
        
        with self.lock :
            self.alert_count +=1
            self.history.append (alert)
            if len(self.history) > 1000 :
                self.history = self.history[-500:]
        
        logger.warning(message)
        self.dispatch(alert)
        return alert
    
    def dispatch(self, alert : Alert) -> None :
        
        now = alert.timestamp
        for name, handler in self,self.channels.items () :
            elapsed = now - self.last_fired.get (name, 0.0)
            
            # CRITICAL alerts bypass rate limiter
            if elapsed < self.rate_limit and alert.severity != Severity.CRITICAL :
                logger.debug (" Channel '%s' rate-limited (%.1f s remaining)",
                              name, self.rate_limit - elapsed)
                alert.dispatched[name] = False
                continue

            try :
                handler(alert)
                alert.dispatched[name] = True
                self.last_fired[name] = now
            
            except Exception as exc :
                logger.error (" Channel '%s' error : %s", name, exc)
                alert.dispatched[name] = False

    
    # accessors

    def clear_alerts (self) -> None :
        """Reset alert state ( for watchdog recovery)"""
        logger.info ("Alert state covered")

    def recent_alerts (self, n: int =10) -> list [Alert] :
        """ Return the n most recent alerts"""
        with self.lock :
            return list(self.history[-n:])
        
    @property
    def alert_count (self) -> int :
        return self.alert_count
    
    def summary (self) -> dict :
        with self.lock :
            hist = self.history[-20:]
        crits = sum( 1 for a in hist if a.severity == Severity.CRITICAL)
        warns = sum (1 for a in hist if a.severity == Severity.WARNING)
        return {
            " total" : self.alert_count,
            "critical" : crits,
            "warning" : warns,
            "channels" : list(self.channels.keys()),
        }
