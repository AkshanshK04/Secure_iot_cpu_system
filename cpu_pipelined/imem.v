module instruction_memory ( 
    
    input [15:0] addr, 
    output [15:0] instr 
);

   reg [15:0] mem[0:255];

   initial begin
    $readmemh("program.hex", mem);

   end

   assign instr = mem[addr] ;
endmodule