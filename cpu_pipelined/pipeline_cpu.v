/* 
action : 6 stage pipelined 16 bit cpu
*/

`timescale 1ns/1ns

module pipeline_cpu (

    input wire clk,
    input  wire rst_n,

    /* mem mapped sensor port */
    input wire [15:0] sensor_data,
    input wire        sensor_valid,

    /* interrupt interface */
    input wire   irq,
    input wire [15:0]  irq_vector,
    output reg         irq_ack,

    /* alert ops ( mem mapped io at 0xF0-0xF2 ) */
    output reg    alert_buzzer,
    output reg    alert_bt,
    output reg    alert_wifi,


    /* debug */

    output wire [15:0]  dbg_pc,
    output wire [15:0] dbg_alu_out ,
    output wire        dbg_halted
);



    /* initialize */


    /* reg file signals first */
    reg [2:0]   rf_rs1, rf_rs2, rf_rd_w;
    reg [15:0]  rf_wdata;
    reg         rf_we;
    wire [15:0] rf_rdata1, rf_data2;



    reg_file u_rf (

        .clk (clk),
        .we (rf_we),
        .rs1 (rf_rs1),
        .rs2  (rf_rs2) ,
        .rd  (rf_rd_w ),
        .wdata  (rf_wdata) ,
        .rdata1 (rf_rdata1) ,
        .rdata2 (rf_rdata2)
    );

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