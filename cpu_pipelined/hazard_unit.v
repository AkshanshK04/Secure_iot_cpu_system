module hazard_unit (
    
    input [3:0] rs1, rs2, rd_ex,
    output reg stall
);

always @(*) begin
    if (rd_ex == rs1 || rd_ex == rs2)
        stall =1 ;
    else 
        stall = 0;
end
endmodule