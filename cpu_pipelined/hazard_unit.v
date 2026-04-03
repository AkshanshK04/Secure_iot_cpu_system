/* 
action : detects and resolves hazards 

*/

`timescale 1ns/1ns

module hazard_unit (
    
    input wire [2:0] id_rs1,
    input wire [2:0] id_rs2,
    input wire [2:0] ex_rd ,
    input wire [2:0] mem_rd ,
    input wire ex_mem_read ,
    
    output reg stall,
    input wire flush ,
    output reg [1:0] fwd_a,
    output reg [1:0] fwd_b
);

always @(*) begin
    stall = 1'b0;
    flush = 1'b0;
    fwd_a = 2'b00;
    fwd_b = 2'b00 ;

    /* load-use hazard */
    if ( ex_mem_read && ((ex_rd == id_rs1) || (ex_rd == id_rs2 ))) begin
        stall = 1'b1 ;
        flush = 1'b1;
    end
    
    /* ex fprwarding */
    if (ex_rd != 3'b000 ) begin
        if ( ex_rd == id_rs1) fwd_a = 2'b10 ;
        if ( ex_rd == id_rs2 ) fwd_b = 2'b10;

    end

    /* mem forwarding */
    if (mem_rd != 3'b000 ) begin
        if (( mem_rd == id_rs1) && (fwd_a != 2'b10)) fwd_a = 2'b01;
        if (( mem_rd == id_rs2 ) && (fwd_b != 2'b10)) fwd_b =2'b01;
        
    end
end
endmodule