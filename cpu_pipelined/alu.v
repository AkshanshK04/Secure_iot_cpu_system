/*
 action : combinational logic
    performs ALU operations

*/

`timescale 1ns/1ns

module alu (

    input wire [3:0]    op,
    input wire [15:0]   a,
    input wire [15:0]   b ,
    output reg [15:0]   result ;
    output wire         zero;
    output wire         neg ;
    output wire         carry 
);

reg [16:0] full_result ;   /*17 b to capture carry */

always @(*) begin
    
    full_result = 17'd0;
    case(op)
        4'b0000 : full_result = {1'b0,a} + {1'b0,b} ;       /*add*/
        4'b0001 : full_result = {1'b0,a} - {1'b0,b} ;       /*sub*/
        4'b0010 : full_result = {1'b0, a& b};               /*and*/   
        4'b0011 : full_result = {1'b0, a| b };              /*or*/
        4'b0100 : full_result = {1'b0, a ^b} ;              /*xor*/
        4'b0101 : full_result = {1'b0, a<<b[3:0]} ;         /*shl*/
        4'b0110 : full_result = {1'b0, a>>b[3:0]};          /*shr*/
        4'b0111 : full_result = {1'b0, a} - {1'b0, b};      /*cmp (sub , no WB)*/
        default : full_result = 17'd0;

    endcase
    result = full_result[15:0] ;

end
    assign zero = (result == 16'h0000 );
    assign neg = result[15];
    assign carry = full_result[16];

endmodule
