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

def decrypt_16 ( enc: int, seq : int ) -> int :
    '''
    decrypt a 16b encrypted word
    '''

    return encrypt_16 (enc, seq)  # xor inverse = xor again

def encrypt_bytes ( data : bytes, seq :int) -> bytes :
    
    out = bytearray ( len(data))
    for i, b in enumerate(data) :
        out[i] = b ^ key_byte ( seq + i)
    return bytes(out)

def decrypt_bytes (data : bytes , seq : int ) -> bytes :
    return encrypt_bytes ( data, seq)

def gen_key_schedule ( length : int , seed : int =0 ) -> List[int] :
    schedule : List[int] = []
    state = seed & 0xFF
    for i in range ( length) :
        state = (state ^ xor_key[i % key_len] ^ (state >> 1)) & 0xFF
        schedule.append(state)
    return schedule

# self test
if __name__ == "__main__" :
    print ( " ecryption self test ")
    for seq in range (4) :
        raw = 0xABCD
        enc = encrypt_16(raw, seq)
        dec = decrypt_16(enc, seq)
        status = "OK" if dec == raw else "FAIL"
        print(f"  seq={seq:02d}   raw = 0x{raw:04X}   enc = 0x{enc:04X}"
              f" dec= 0x{dec:04X}   [{status}]")
        
    raw_bytes = b"Hello, esp32"
    enc_bytes = encrypt_bytes( raw_bytes, seq=0)
    dec_bytes = decrypt_bytes ( enc_bytes, seq = 0)
    print (f"\n   bytes round-trip : {'OK' if dec_bytes == raw_bytes else 'FAIL'}")
    print ("==done ==")
    