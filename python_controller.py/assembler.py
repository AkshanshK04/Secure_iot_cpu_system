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

def parse_reg( token : str) -> int :
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

def parse_addr (token : str) -> int :
    """parse a bare address (decimal, hex, or alias)"""
    token = token.strip("[]\t")
    if token.lower().startswith("0x") :
        return aliases[token.upper()]
    
    if token.lower().startswith("0x") :
        return int(token, 16)
    return int(token)

# token cleanup
def tokenize(line: str) -> list[str] :
    """strip comments, split on whitespace/comma, return token list"""
    line = re.sub(r";.*", "", line).strip ()
    if not line :
        return []
    #split  on comma or whitespace
    return [t.strip() for t in re.split(r"[,\s]+", line) if t.strip()]

# pass 1 : collect labels and inst count

def pass1(lines : list[str]) -> tuple[dict[str, int], list[tuple[int, list[str]]]] :
    """
    returns :
        labels :       { label_name -> pc_value}
        instructions : [(src_lineno, tokens)]
        """
    
    labels :        dict[str, int]        = {}
    instructions:   list[tuple[int, list[str]]] = []
    pc =0

    for lineno, raw in enumerate(lines, 1 ) :
        tokens =  tokenize(raw)
        if not tokens :
            continue

        #label definition 
        if tokens[0].endswith(":") :
            lbl = tokens[0][:-1].upper()
            labels[lbl] = pc
            tokens = tokens[1:]
            if not tokens :
                continue


            mnemonic = tokens[0].upper()
            if mnemonic not in opcodes :
                raise SyntaxError(f" Line   {lineno} :  Unknown mnemonic  '{mnemonic}'")
            instructions.append((lineno, tokens))
            pc +=1

        return labels, instructions
    
# passs 2 = encode instr

def encode(tokens : list[str], pc : int,  labels: dict[str, int], lineno : int) -> int :
    mnemonic = tokens[0].upper()
    op = opcodes[mnemonic]

    def resolve_label_or_offset(tok: str, bits : int, relative : bool) -> int :
        tok = tok.strip()
        if tok.upper() in labels :
            target = labels[tok.upper()]
            if relative :
                offset = target - (pc +1)
                lo = - (1 << (bits - 1))
                hi = ( 1 << (bits -1)) -1
                if not ( lo <= offset <= hi) :
                    raise ValueError (
                        f"Line {lineno} : Branch target '{tok}' out of range "
                        f"({offset} not in [{lo}, {hi}])"
                    )
                return offset & (( 1 << bits) - 1)
            return target & (( 1 << bits) -1 )
        return parse_imm (tok, bits)
    
    word = op << 12
    try :
        if mnemonic in ("ADD", "SUB", "AND", "OR", "XOR", "SHL", "SHR") :
            #rd, rs1, rs2
            rd = parse_reg(tokens[1])
            rs1 = parse_reg(tokens[2])
            rs2 = parse_reg(tokens[3])
            word  |= (rd << 9) | (rs1 << 6) | (rs2 << 3)

        elif mnemonic == "CMP"  :
            rs1 = parse_reg(tokens[1])
            rs2 = parse_reg(tokens[2])
            word |= (rs1 << 6) | (rs2 << 3)

        elif mnemonic == "LDI" :
            rd = parse_reg(tokens[1])
            imm = parse_imm(tokens[2], 8)
            word |= (rd << 9) | (imm & 0xFF)
        
        elif mnemonic == "LD" :
            rd = parse_reg(tokens[1])
            rs1 = parse_reg(tokens[2])
            word |= (rd << 9) | (rs1 << 6)

        elif mnemonic == "ST" :
            addr = parse_addr(tokens[1])
            rs1 = parse_reg(tokens[2])
            word |= (rs1 << 6) | (addr & 0xFF)

        elif mnemonic in ("BEQ", "BNE", "BLT") :
            offset = resolve_label_or_offset(tokens[1], 6, relative=True)
            word |= (offset & 0x3F)
        
        elif mnemonic == "JMP" :
            addr = resolve_label_or_offset(tokens[1], 9, relative=False)
            word |= (addr & 0x1FF)

        else :
            raise SyntaxError(f"Line {lineno} : Cannot encode '{mnemonic}'")
    
    except (IndexError, ValueError) as exc :
        raise SyntaxError(f"Line {lineno} : {exc}") from exc
    
    return word & 0xFFFF 

# main assembler

def assemble ( source: str, verbose: bool = False) -> list[int] :
    lines = source.splitlines()
    labels, instructions = pass1(lines)

    if verbose :
        print(f"Labels : {labels}")

    machine_code : list[int] = []
    for pc, (lineno, tokens) in enumerate(instructions) :
        word = encode(tokens, pc, labels, lineno)
        machine_code.append(word)
        if verbose :
            print(f"   [{pc:03d}] 0x{word:04X} <- {' '.join(tokens)}")
    
    return machine_code

def write_hex ( words: list[int], path: str) -> None:
    """write verilog $readmemh compatible hex file"""
    p = Path(path)
    p.write_text("\n".join(f"{w:04X}" for w in words) + "\n")
    print(f"Wrote {len(words)} words -> {path}")


# ── Built-in example program ──────────────────────────────────────────────────
 
EXAMPLE_ASM = """\
; Secure IoT CPU — Default Alert Program
; Reads sensor, decrypts, compares to threshold, triggers alerts
 
        LDI  r0, #0        ; r0 ← sensor data (0x8000 special)
        LDI  r1, #0xA5     ; r1 ← XOR key byte 0
        XOR  r0, r0, r1    ; r0 ← decrypted sensor (lo-byte)
        LDI  r3, #0x0B     ; r3 ← threshold high byte
        CMP  r0, r3        ; flags ← r0 - r3
        BLT  NO_ALERT      ; if r0 < r3 → skip alerts
        LDI  r4, #1
        ST   [BUZZER], r4  ; buzzer ON
        ST   [BT],     r4  ; BT alert
        ST   [WIFI],   r4  ; WiFi alert
        HALT
NO_ALERT:
        LDI  r4, #0
        JMP  0x00           ; loop back to start
"""

#CLI

def main () -> None :
    parser = argparse.ArgumentParser(description="16-bit RISC Assembler")
    parser.add_argument ("input", nargs="?", help="Assembly source file (.asm)")
    parser.add_argument("-o", "--output", default="program.hex",
                        help="Output hex file (default : program.hex)")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--example", action="store_true",
                        help="Assemble the built-in example program ")
    args = parser.parse_args()

    if args.example :
        source = EXAMPLE_ASM
        print("==== Assembling built in example program====")
    elif args.input :
        source = Path(args.input).read_text()
    else :
        parser.print_help()
        sys.exit(1)

    try :
        words = assemble(source, verbose=args.verbose)
        write_hex(words, args.output)
    except SyntaxError as exc :
        print(f"Assembler error : {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__" :
    main ()
    





    
    