/* 
action : 8 x 16-bit register file
r0 is sensor data reg
r7 is sp
*/

`timescale 1ns/1ns

module reg_file (

    input wire clk,
    input wire we ,
    input wire [2:0] rs1,
    input wire [2:0] rs2 ,
    input wire [2:0] rd ,
    input wire [15:0] wdata,
    input wire [15:0] rdata1,
    input wire [15:0] rdata2
);


    reg [15:0] regs [0:7] ;
    integer i ;

    initial begin 
        for ( i =0 ; i<8 ; i=i+1 )
            regs[i] = 16'h0000;
    end

    always @(posedge clk ) begin 
        if (we) 
            regs[rd] <= wdata ;
    end

    assign rdata1 = regs[rs1];
    assign rdata2 = regs[rs2];

endmodule
    