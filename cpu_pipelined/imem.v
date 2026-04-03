/*

    action : 256 x 16-bit instruction memory
    loads sensor data --- special opcode 0x8000 --intercepted by pipeline
    xor decrypt with key const
    compare against threshold
    branch to alert routine if above threshold
    store 0 to i/o
    jump back to start

    alert routine :
        store 1 to 0xF0 (buzzer )
        store 1 to 0xF1 (bt)
        store 1 to 0xF2 (wifi)
        halt

    
    */
`timescale 1ns/1ns

module instruction_memory ( 
    
    input wire          clk,
    input wire [15:0]   addr, 
    output reg [15:0]   instr 
);

   reg [15:0] mem[0:255];

   /* embedded program ------
    addr ---- encoding ---- mnemonic 
    0x00 ---- 0x8000 ---- LD_SENSOR r0 (special)
    0x01 ---- 0x40A5 ---- XOR r0, r0, #0xA5 (decrypt )
    0x02 ---- 0x70B0 ---- CMP r0, r3    (vs threshold )
    0x03 ---- 0xB004 ---- BEQ +4  ( if equal, skip alert)
    0x04 ---- 0xD003 ---- BLT +3  ( if less , skip alert )
    0x05 ---- 0xA0F0 ---- ST [0xF0] , r0  (buzz =1 if alert )
    */


    initial begin
        /* zero all */
        integer k ;
        for (k = 0 : k<256 ; k=k+1 )
            mem[k] = 16'hFFFF;    /*nop / halt */
        
        $readmemh("program.hex", mem);

        /* fall back if file read fails */
        mem[8'h00] = 16'h8000 ;   /* LD_SENSOR -- r0 */

        mem[8'h01] = 16'h4008 ; 

        mem[8'h02] = 16'h7018 ;
        
        mem[8'h03] = 16'hD003 ;

        mem[8'h04] = 16'h8201 ;

        mem[8'h05] = 16'hAF0;

        mem[8'h06] = 16'hA8F1 ;

        mem[8'h07] = 16'hB0F2 ;

        mem[8'h08] = 16'hFFFF ;   /*halt */

        mem[8'h09] = 16'h8200 ;

        mem[8'h0A] = 16'hE000 ;

   end

   always @(posedge clk) begin
        instr <= mem[addr[7:0]];
   end
endmodule