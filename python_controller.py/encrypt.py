''''
action : encrypt, decrypt and key-schedule utilities

'''

from __future__ import annotations
from typing import List

# key material 
xor_key : List [int] = [0xA5, 0x3c, 0x7F, 0x11, 0xDE, 0x9B, 0x42, 0x68]
key_len = len(xor_key)

def key_byte ( seq : int, offset : int =0) -> int :
    """ returns rolling key byte At positoin ( seq + off) % key_len"""
    return xor_key [( seq + offset) % key_len]

def encrypt_16 ( raw : int, seq : int) -> int :
    '''
    encrypt a 16b sensor word using rolling xor schedule

    args :
        raw : raw 16b sensor value ( 0-65535)
        seq : sequence counter ( 0-255)
    returns : encrypted 16b int
    '''

    if not ( 0 <= raw <= 0xFFFF) :
        raise ValueError ( f" raw value { raw} out of 16-bit range")
    
    lo = (raw & 0x00FF ) ^ key_byte(seq, 0)
    hi = (( raw >> 8 ) & 0xFF) ^ key_byte (seq, 1)
    return (( hi <<8) | lo) & 0xFFFF

