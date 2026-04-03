module pipeline_cpu (

    input clk,
    input reset,
    input [15:0] ext_data,
    output [15:0] result 
);

    reg [15:0] pc;
    wire [15:0] instr;

    reg[15:0] if_id_instr;
    reg[15:0] id_ex1, id_exb;
    reg[3:0] id_ex_opcode;
    reg[15:0] ex_mem_out;
    reg[15:0] mem_wb_out ;

    instruction_memory imem( pc, instr );
    register_file rf(clk, if_id_instr[11:8], if_id_instr[7:4], if_id_instr[3:0], mem_wb_out, 1, id_exa , id_exb);
    alu alu_unit(id_ex1, id_exb, id_ex_opcode_ex_memout);

    always @(posedge clk or posedge reset ) begin
        if (reset) begin
            pc <= 0;

        end else begin
            //if
            if_id_instr <= instr :
            pc <= pc+1;

            //id
            id_ex_opcode <= if_id_instr[15:12] ;

            //ex
            ex_memout <= ex_memout ;

            //mem
            mem_wb_out <= ex_mem_out;

        end
    end

    assign result = mem_wb_out;

endmodule