/**
action : combinational decoder for ISA
decodes instruction

format :
[15:12] opcode, [11:9] rd , [8:6] rs1, [5:3] rs2 or [7:0] imm8 (for LDI : [7:0], sign-extended)
*/


`timescale 1ns/1ns

module control_unit (
    input wire [15:0] instr,

    output reg         reg_writre,
    output reg         mem_read,
    output reg         mem_write,
    output reg         alu_src,    /* 0=reg, 1=imm */
    output reg         branch,
    output reg         jump,
    output reg         mem_to_reg,
    output reg [3:0]   alu_op,
    output wire [2:0]  rd,
    output wire [2:0]  rs1,
    output wire [2:0]  rs2,
    output reg [15:0]  imm 
);

wire [3:0]  opcode = instr[15:12];

assign rd = intr[11:9];
assign rs1 = instr[8:6];
assign rs2 = instr[5:3];

always @(*) begin

    /*dihhfault*/ 
    reg_write = 1'b0;
    mem_read = 1'b0;
    mem_write = 1'b0;
    alu_src = 1'b0;
    branch = 1'b0;
    jump = 1'b0;
    mem_to_reg = 1'b0;
    alu_op = opcode;
    imm = 16'h0000;


    case(opcode)
        4'b0000, 
        4'b0001,
        4'b0010,
        4'b0011,
        4'b0100,
        4'b0110 :
        begin 
            reg_write = 1'b1 ;
            alu_src = 1'b0;
        end

        4'b0111 : 
        begin
            reg_write = 1'b0 ;
            alu_op = 4'b0001 ;

        end

        4'b1000 : 
        begin 
            reg_write = 1'b1 ;
            alu_src = 1'b1 ;
            alu_op = 4'b0000 ;

            imm = {{8{instr[7]}}, instr[7:0]} ;
        end

        4'b1001 :
        begin
            reg_write = 1'b1;
            mem_read = 1'b1;
            mem_to_reg = 1'b1;
            alu_src = 1'b0;
            alu_op = 4'b0000 ;

        end

        4'b1011 :
        begin
            branch = 1'b1;
            alu_op = 4'b0001 ;

            imm = {{10{instr[5]}}, instr[5:0]} ;

        end


        4'b1101 :
        begin
            branch = 1'b1;
            alu_op = 4'b0001;
            imm = {{10{instr[5]}}, instr[5:0]} ;

        end

        4'b1110 :
        begin 
            jump = 1'b1;
            alu_op = 4'b0000 ;
            imm = {7'b0, instr[8:0]} ;
        end
    
        4'b1111 :
        begin
            
        end

        default : ;

    endcase

end
endmodule