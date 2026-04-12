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

    #dispach alerts based on CPU output
    if cpu.alert_buzzer or cpu.alert_bt or cpu.alert_wifi :
        alert_sys.evaluate_n_dispatch(frame.sensor_val, frame.seq)

    # notify watchdog
    watchdog.notify_frame()
    return cpu

def run_pipeline (
        uart : UARTHandler,
        alert_sys : AlertSystem,
        watchdog : SystemWatchdog,
        stop_evt : Event,
) -> None :
    """main processing loop : read UART frames and process each through verilog cpu"""
    logger.info("Pipeline running - waiting for esp 32 frames")
    while not stop_evt.is_set() :
         frame = uart.get_frame(timeout=2.0)
         if frame is  None :
              logger.debug("No frame (UART timeout)")
              continue
         process_frame(frame, alert_sys, watchdog)
    logger.info("Pipeline stopped")

# ── Demo mode (no hardware) ───────────────────────────────────────────────────
 
def run_demo(alert_sys: AlertSystem, watchdog: SystemWatchdog) -> None:
    """
    Offline demo: synthetic sensor values, real Verilog CPU simulation.
    Generates one frame per second — every 10th frame is above threshold.
    """
    import random
    logger.info("=== DEMO MODE — synthetic frames, real Verilog CPU ===")
 
    seq   = 0
    cycle = 0
 
    from encryption import encrypt_16
    from crc        import compute_frame_crc
    from uart_handler import SensorFrame
 
    while True:
        # Synthetic sensor value
        if cycle % 10 == 9:
            raw = random.randint(0x0C00, 0xFFFF)   # spike above threshold
        else:
            raw = random.randint(0x0200, 0x0A00)   # normal below threshold
 
        # Build a fake SensorFrame (as if it came from UART)
        enc = encrypt_16(raw, seq)
        frame = SensorFrame(
            seq=seq,
            enc_raw=enc,
            sensor_val=raw,
        )
 
        process_frame(frame, alert_sys, watchdog)
 
        seq   = (seq + 1) & 0xFF
        cycle += 1
        time.sleep(1.0)

def main () -> None :
    parser = argparse.ArgumentParser(
        description="Secure IoT CPU System - Python Controller (verilog - driven)")
    
    parser.add_argument("--port", default="/dev/ttyUSB0")

    parser.add_argument("--baud", type=int, default=115200)
                
    parser.add_argument("--demo", action="store_true",
                        help="offline demo mode no esp32 needed)")
    
    parser.add_argument("--threshold", type=lambda x: int(x, 0), default=0x800,
                        help="Alert threshold ( default 0x0B00)")
    
    args = parser.parse_args()


    logger.info("====Secure IoT CPU System (Verilog - driven)====")
    logger.info("Port= %s Baud=%d  Demo=%s  Threshold=0x%04X",
                args.port, args.baud, args.demo, args.threshold)
    

    # Check Icarus Verilog availability
    if not check_iverilog():
        logger.error("Icarus Verilog not found. Please install it to run this program.")
        sys.exit(1)

    # Build alert program hex file for Verilog CPU
    write_program_hex(build_alert_program(threshold=args.threshold),
                      "program.hex")
    
    logger.info("program.hex written for Verilog instruction memory")

    #build subsystems
    uart     = UARTHandler(port=args.port, baud=args.baud)
    alert_sys = AlertSystem(threshold=args.threshold)
    watchdog  = SystemWatchdog(uart= uart, alert_system=alert_sys,
                               frame_timeout_s=5.0)
    
    #register alert output channels
    alert_sys.add_channel("log", log_channel)    # BT log stub
    alert_sys.add_channel("uart", email_channel_handler) #wifi email
    alert_sys.add_channel("uart", UARTAlertChannel(uart)) #ESP32 buzzer

    #graceful shutdown
    stop_evt = Event()

    def shutdown( sig ,frame) :
        logger.info("Shutdown signal - stopping ...")
        stop_evt.set()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    #start watchdog
    watchdog.start()

    # run
    if args.demo :
        try :
            run_demo(alert_sys, watchdog)
        except KeyboardInterrupt :
            pass
    else :
        if not uart.connect(retries=5) :
            logger.critical("Cannot connect to ESP32 on %s. Use --demo." , args.port)
            sys.exit(1)
        try :
            run_pipeline(uart, alert_sys, watchdog, stop_evt)
        finally :
            uart.disconnect()
    watchdog.stop()
    logger.info("Alert summary : %s" , alert_sys.summary() )
    logger.info("UART stats : %s", uart.stats())
    logger.info("Shutdown complete.")


if __name__ == "__main__":
    main()

    


