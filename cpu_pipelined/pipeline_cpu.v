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

    /* imem signals */
    reg [15:0]  imem_addr;
    wire [15:0] imem_instr;

    instruction_memory u_imem( 
        
        .clk (clk) ,
        .addr (imem_addr) ,
        .instr (imem_instr)
     );
    
    /* data mem signals */
    reg [15:0] dmem_addr ,  dmem_wdata ;
    reg        dmem_we;
    wire [15:0] dmem_rdata ;

    data_memory u_dmem (
        .clk (clk) ,
        .we (dmem_we) ,
        .addr (dmem_addr) ,
        .wdata (dmem_wdata) ,
        .rdata (dmem_rdata)
    );


    /* alu signals */
    reg [3:0]  alu_op ;
    reg [15:0] alu_a, alu_b;
    wire [15:0] alu_result;
    wire        alu_zero , alu_neg , alu_carry ;


    alu u_alu (
        .op (alu_op),
        .a (alu_a) ,
        .b (alu_b) ,
        .result (alu_result) ,
        .zero (alu_zero) ,
        .neg (alu_neg) ,
        .carry (alu_carry)
     );
    

    /* control unit signals */
    reg [5:0] cu_instr;
    wire      cu_reg_write, cu_mem_read, cu_mem_write;
    wire      cu_alu_src, cu_branch, cu_jump;
    wire      cu_mem_to_reg ;
    wire [3:0] cu_alu_op ;
    wire [2:0] cu_rd , cu_rs1 , cu_rs2 ;
    wire [15:0] cu_imm;

    control_unit u_cu (

        .instr (cu_instr) ,
        .reg_write (cu_reg_write) ,
        .mem_read (cu_mem_read) ,
        .mem_write (cu_mem_write) ,
        .alu_src (cu_alu_src) ,
        .branch (cu_branch) ,
        .jump (cu_jump) ,
        .mem_to_reg (cu_mem_to_reg) ,
        .alu_op (cu_alu_op) ,
        .rd (cu_rd) ,
        .rs1 (cu_rs1) ,
        .rs2 (cu_rs2) ,
        .imm (cu_imm)
    );

    /* hazard unit signals */
    reg [2:0]  hu_id_rs1, hu_id_rs2 ;
    reg [2:0]  hu_ex_rd , hu_mem_rd ;
    reg        hu_ex_mem_read ;
    wire       hu_stall , hu_flush ;
    wire [1:0] hu_fwd_a , hu_fwd_b ;

    hazard_unit u_hu (
        .id_rs1 (hu_id_rs1) ,
        .id_rs2 (hu_id_rs2) ,
        .ex_rd (hu_ex_rd) ,
        .mem_rd (hu_mem_rd) ,
        .ex_mem_read (hu_ex_mem_read) ,
        .stall (hu_stall) ,
        .flush (hu_flush) ,
        .fwd_a (hu_fwd_a) ,
        .fwd_b (hu_fwd_b)
    );

    
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