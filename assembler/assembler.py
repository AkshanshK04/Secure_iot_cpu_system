opcode_map ={
    "ADD" : "0001" ,
    "SUB" : "0010" ,
    "MUL" : "0011" ,
    "AND" : "0100" 
}


def assemble_line( line) :
    parts = line.split()
    opcode = opcode_map[parts[0]]
    r1 = format(int(parts[1][1]), '04b')
    r2 = format(int(parts[2][1]), '04b')
    r3 = format(int(parts[3][1]), '04b')
    return opcode + r1 + r2+ r3

def assemble_file (input_file, output_file) :
    with open(input_file) as f, open(output_file, 'w' ) as out :
        for line in f :
            binary = assemble_line(line.strip()) 
            out.write(hex(int(binary, 2 ))[2:] + "\n")


assemble_file( "program.asm", "program.hex")
