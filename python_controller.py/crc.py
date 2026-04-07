'''
description : CRC-8 polynomial 0x07
also provides CRC-16 for longer payloads

'''

from __future__ import annotations
from typing import Union

#   CRC-8 polynomial 0x07 , init 0x00 
_CRC8_TABLE : list[int] =  []

def build_crc8_table () -> None :
    for i in range (256) :
        crc = i
        for _ in range (8) :
            crc = (( crc <<1 ) ^ 0x07 ) & 0xFF if (crc & 0x80) else ( crc << 1) & 0xFF 
        _CRC8_TABLE.append(crc)

build_crc8_table()


def crc8 ( data : Union[ bytes, bytearray]) -> int :
    '''
    compute crc 8 over data (poly = 0x07 , init = 0x00)
    
    returns : single byte (0-255) checksum.
    '''

    crc = 0x00
    for b in data :
        crc  = _CRC8_TABLE[crc ^ b]
    return crc


# CRC-16 poly 0x1021 , init 0xFFFF
_CRC16_TABLE : list[int] = []

def build_crc16_table () -> None :
    for i in range (256) :
        crc = i << 8 
        for _ in range (8) :
            crc = (( crc << 1 ) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else ( crc << 1 ) & 0xFFFF
        _CRC16_TABLE.append( crc )

build_crc16_table()

def crc16 ( data : Union[bytes, bytearray ]) -> int :
    '''
    compute CRC-16 over data (poly = 0x1021 , init 0xFFFF) 
    used for longer payloads 

    returns : 16b checksum (0-65535) 

    '''
    crc = 0xFFFF
    for b in data :
        crc = (( crc << 8) ^ _CRC16_TABLE[ (( crc >> 8 ) ^ b )& 0xFF]) & 0xFFFF
    return crc

# frame verification 
def  verify_frame ( seq : int, enc_hi : int, enc_lo : int, received_crc : int) -> bool :
    '''
    verify a receive UART frame using crc 8
    frame payload : [seq, enc_hi, enc_lo] ( 3 bytes)

    args : seq : sequence counter byte 
           enc_hi : high byte of encrypted sensor value
           enc_lo : low byte of encrypted sensor value
           received_crc : crc byte extracted from the frame 

    returns : true if crc matches , false otw
    '''
