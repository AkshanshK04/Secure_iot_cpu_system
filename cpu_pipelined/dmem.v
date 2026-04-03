
`timescale 1ns/1ns

module data_memory (

    input wire clk,
    input wire we,
    input wire [15:0] addr,
    input wire [15:0] wdata,
    output reg [15:0] rdata
);


    reg [15:0] mem [0:255];

    integer i ;
    initial begin 
        for (i=0 ; i<256 ; i=i+1)
            mem[i] = 16'h0000;
    end

    always @(posedge clk) begin
        if ( we && addr [15:8] == 8'h00) 
            mem[addr[7:0]] <= wdata ;
        rdata <= mem[addr[7:0]];
    end

endmodule
