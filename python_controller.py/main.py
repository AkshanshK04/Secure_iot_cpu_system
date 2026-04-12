"""
usage :
    python main.py                          # real hardware /dev/ttyUSB0
    python main.py --port COM3              # Windows
    python main.py --demo                   # offline demo, no ESP32 needed
    python main.py --demo --threshold 0x500 # custom threshold

"""
from __future__ import annotations 
import argparse
import logging
import signal
import sys
import time
from threading import Event

from uart_handler import UARTHandler, SensorFrame
from cpu_interface import run_verilog_cpu, check_iverilog, \
                            write_program_hex, build_alert_program, CPUResult

from alert_system import AlertSystem, Severity
from email_alert import email_channel_handler
from watchdog import SystemWatchdog

#logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s   %(levelname)-8s  %(name)-16s   %(message)s",
    datefmt="%H:%M:%S" ,
)
logger = logging.getLogger("main")

#alert channels
class UARTAlertChannel :
    """sends ALERT / RESET commands back to the esp 32 buzzer"""

    def __init__(self, uart : UARTHandler) -> None :
        self._uart = uart

    def __call__(self, alert) -> None :
        cmd = "ALERT" if alert.severity >= Severity.WARNING else "RESET"
        sent = self._uart.send_command(cmd)
        logger.info("-> ESP32 UART : %-6s  [%s]", cmd, "ok" if sent else "fail")

def log_channel (alert) -> None:
    """write alert to local log file (BT stub - swap for real BLE call)"""
    logger.warning("BT-LOG  |  %s", alert.message)
    with open("alerts.log", "a") as f:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(alert.timestamp))
        f.write(
            f"{ts}  | {alert.severity.name : 8s}  |"
            f"val=0x{alert.sensor_value:04X}  | {alert.message}\n"

        )

# core pipeline

def process_frame (
        frame :      SensorFrame,
        alert_sys :  AlertSystem,
        watchdog :   SystemWatchdog,
) -> CPUResult :
    """Run one sensor frame through the verilog CPU pipeline"""
    logger.info(
        ">> Frame seq=0x%02X  enc=0x%04X  val = 0x%04X",
        frame.seq, frame.enc_raw, frame.sensor_val,
    )

    # run actual verilog CPU simulation
    cpu = run_verilog_cpu(frame.sensor_val)
    if not cpu.success:
        logger.error("Verilog CPU error : %s", cpu.error)
        return cpu
    
    logger.info(
        " Verilog CPU → buzzer=%d  bt=%d  wifi=%d  "
        "halted=%s  cycles=%d  (%.0f ms)",
        int(cpu.alert_buzzer), int(cpu.alert_bt), int(cpu.alert_wifi),
        cpu.halted, cpu.cycles, cpu.sim_time_ms,
    )

    #

