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
    payload = bytes ([ seq & 0xFF, enc_hi & 0xFF, enc_lo & 0xFF])
    computed = crc8 ( payload)
    return computed == ( received_crc & 0xFF)

def compute_frame_crc ( seq: int, enc_hi : int, enc_lo : int) -> int :
    '''
    compute expected crc-8 for a frame payload
    '''
    payload = bytes ([ seq & 0xFF, enc_hi & 0xFF, enc_lo & 0xFF])
    return crc8(payload)


# self test
if __name__ == " __main__ " :
    print("=== CRC self test ===")

    # crc-8 known vector
    data = bytes ([0x05, 0x3A, 0x7F])
    c8 = crc8(data)
    print(f" CRC-8 of {data.hex().upper()} = 0x{c8:02X}")

    # crc-16 known vector : "123456789" -> 0x29B1
    c16 = crc16 (b"123456789")
    status = "OK" if c16 == 0x29B1 else f"FAIL  ( got 0x{c16:04X})"
    print(f"    CRC-16 of '123456789' = 0x{c16:04X}   [{status}]")

    # Frame verify round-trip
    seq, hi, lo = 0x05, 0x3A, 0x7F
    crc_val = compute_frame_crc(seq, hi, lo)
    ok = verify_frame(seq, hi, lo, crc_val )
    print(f"   Frame verify round trip : { 'OK' if ok else 'FAIL'}")


    #tamper test
    tampered = verify_frame( seq, hi ^ 0xFF, lo, crc_val)
    print (f"   Tampered frame rejected : { 'OK' if not tampered else 'FAIL'}")

    print ( " == done == ")