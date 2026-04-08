'''
action : email alert sender using smtplib

env variables :
    SMTP_HOST      SMTP server hostname (def : smtp.gmail.com)
    SMTP_PORT      SMTP port (def : 587)
    SMTP_USER      Sender email address
    SMTP_PAss      App password/ credentials
    Alert_TO       Recipient email address

'''

from __future__ import annotations

import os
import smtplib
import logging  
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import    MIMEMultipart
from typing import Optional

logger = logging.getLogger("email_alert")

# configuration from environment
def env ( key: str, default : str ="") -> str :
    return os.environ.get(key, default).strip ()

SMTP_HOST = env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER")
SMTP_PASS = env("SMTP_PASS")
ALERT_TO = [a.strip() for a in env("ALERT_TO", "").split(",") if a.strip()]

# email builder
def build_email (alert) -> MIMEMultipart :
    """build a html + text MIME email for given alert"""

    severity_clr ={
        0 : "#2196F3", #info
        1 : "#FF9800", #warning
        2 : "#F44336", #critical
    }.get(int(alert.severity), "#9E9E9E")

    ts = time.strftime( " %Y-%m-%d %H : %M:%S UTC", time.gmtime(alert.timestamp))

    html_body = f"""
    <html><body style="font-family:monospace;background:#111;color:#eee;padding:20px">
      <h2 style="color:{severity_clr}">
        🚨 IoT Alert — {alert.severity.name}
      </h2>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:6px;color:#aaa">Timestamp</td>
            <td style="padding:6px">{ts}</td></tr>
        <tr><td style="padding:6px;color:#aaa">Severity</td>
            <td style="padding:6px;color:{severity_clr}">
              <b>{alert.severity.name}</b></td></tr>
        <tr><td style="padding:6px;color:#aaa">Sensor Value</td>
            <td style="padding:6px">
              0x{alert.sensor_val:04X} ({alert.sensor_val})</td></tr>
        <tr><td style="padding:6px;color:#aaa">Sequence</td>
            <td style="padding:6px">0x{alert.seq:02X}</td></tr>
        <tr><td style="padding:6px;color:#aaa">Message</td>
            <td style="padding:6px">{alert.message}</td></tr>
      </table>
      <p style="color:#555;font-size:0.8em;margin-top:20px">
        Secure IoT CPU System — Automated Alert
      </p>
    </body></html>
    """
    text_body = (
        f" [{ alert.severity.name}] Sensor Alert\n"
        f" Timestamp : {ts}\n"
        f" Value : 0x{alert.sensor_val:04X} ({alert.sensor_val}) \n"
        f" Sequence : 0x{alert.seq:02X}\n"
        f" Message : {alert.message}\n"
        
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"[IoT - Alert ] {alert.severity.name} - "
        f" Sensor 0x{alert.sensor_val: 04X}"

    )

    msg["From"] = SMTP_USER
    msg["TO"] = ",".join(ALERT_TO)
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    return msg


