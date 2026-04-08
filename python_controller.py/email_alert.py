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

# sender

class EmailAlerter :
    '''
    SSMTP email alert sender with an async send queue
    runs sends in a bg thread 
    '''

    def __init__(self) -> None :
        self.queue : list =[]
        self.lock = threading.Lock()
        self.thread = threading.Thread(target = self.worker, 
                                       name = "email_worker", daemon = True)
        
        self.thread.start()
        self.sent_count = 0
        self.error_count = 0

        if not SMTP_USER or not SMTP_PASS :
            logger.warning(
                "SMTP_USER / SMTP_PASS not set."
                "Email alerts will be logged only."
                "Set SMTP_USER, SMTP_PASS, ALERT_TO in environment."

            )

        if not ALERT_TO :
            logger.warning("ALERT_TO not set - np recipients configured")

    
    def send(self, alert) -> None :
        """Enqueue an alert fro async email dispatch"""
        with self.lock :
            self.queue.append(alert)

    def worker(self) -> None :
        """bg thread : drain the queue and send emails"""

        while True :
            time.sleep(1)
            with self.lock :
                pending = list(self.queue)
                self.queue.clear()

            for alert in pending :
                self.do_send(alert)

    def do_send(self, alert) -> None :
        """ attempt to send one email via SMTP/TLS"""
        if not SMTP_USER or not SMTP_PASS or not ALERT_TO :
            logger.warning(" Email skipped ( no SMTP config) : %s", alert.message)
            return
        
        try :
            msg = build_email(alert)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout = 10) as server :
                server.ehlo()
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, ALERT_TO, msg.as_string())
            self.sent_count+=1
            logger.info("Email sent to %s", ALERT_TO)

        except smtplib.SMTPException as exc :
            self.error_count +=1
            logger.error("SMTP error :%s", exc)

        except Exception as exc :
            self.error_count +=1
            logger.error("Email send failed :%s", exc)

    def __call__(self, alert ) -> None :
        self.send(alert)

    @property
    def stats(self) -> dict :
        return { " sent" : self.sent_count, "errors" : self.error_count}
    
# module level 
emailer : Optional[EmailAlerter] =  None

def get_emailer() -> EmailAlerter :

    global emailer 
    if emailer is None :
        emailer = EmailAlerter()
    return emailer

def email_channel_handler (alert) -> None :
    """" drop in channel handler for AlertSystem.add_channel('email',...)"""
    get_emailer().send(alert)   


