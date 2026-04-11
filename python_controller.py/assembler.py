"""
desc: two pass assembler for the custom isa defined in pipeline_cpu.v

Supported syntax
────────────────
  ; comment
  LABEL:
  ADD  rd, rs1, rs2
  SUB  rd, rs1, rs2
  AND  rd, rs1, rs2
  OR   rd, rs1, rs2
  XOR  rd, rs1, rs2
  SHL  rd, rs1, rs2
  SHR  rd, rs1, rs2
  CMP  rs1, rs2
  LDI  rd, #imm8           ; imm8 decimal or 0xNN hex
  LD   rd, [rs1]
  ST   [addr], rs1          ; addr is a 8-bit hex constant (I/O or DMEM)
  BEQ  label_or_offset6
  BNE  label_or_offset6
  BLT  label_or_offset6
  JMP  label_or_addr9
  HALT
  NOP                       ; alias for HALT
 
Registers: r0 – r7
I/O addresses: BUZZER=0xF0  BT=0xF1  WIFI=0xF2
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

#opcode table
opcodes = {
    "ADD" : 0x0, "SUB" : 0x1, "AND" : 0x2, "OR" : 0x3 ,
    "XOR" : 0x4, "SHL" : 0x5, "SHR" : 0x6, "CMP": 0x7,
    "LDI" : 0x8, "LD"  : 0x9, "ST"  : 0xA,
    "BEQ" : 0xB, "BNE" : 0xC, "BLT" : 0xD,
    "JMP" : 0xE, "HALT": 0xF, "NOP" : 0xF,
    }


# pre defined
aliases = {"BUZZER" : 0xF0, "BT" : 0xF1, "WIFI" : 0xF2}

# helpers

def pares_reg( token : str) -> int :
    token = token.strip().lower()
    if re.fullmatch(r" r[0-7]", token) :
        return int(token[1])
    raise ValueError(f"Invalid register : '{token}")

def parse_imm ( token: str, bits: int) -> int :
    """parse an imm value (#N or 0xN or N) and range check to bits"""
    token = token.strip().lstrip("#").strip()
    if token.upper() in aliases :
        val = aliases[token.upper()]
    elif token.lower().startswith("0x") :
        val = int(token, 16)
    else :
        val = int(token)

    #sign extend neg values
    lo = -(1 << (bits-1))
    hi = (1 << (bits) -1)
    if not ( lo <= val <= hi ) :
        raise ValueError(f" Immediate {val} out of range for {bits}-bit field")
    return val & (( 1 << bits)-1)

def pares_addr