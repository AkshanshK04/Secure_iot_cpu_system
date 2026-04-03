module control_unit (
    
    input [3:0] opcode,
    output reg [2:0] alu_op 
);

always @(*) begin
    case(opcode)
        4'b0001 : alu_op = 3'b000; // add
        4'b0010 : alu_op = 3'b001; //sub
        4'b0011 : alu_op = 3'b010; // xor
        4'b0100 : alu_op = 3'b011;  // and
        default : alu_op = 3'b000;
    
    endcase

end
endmodule