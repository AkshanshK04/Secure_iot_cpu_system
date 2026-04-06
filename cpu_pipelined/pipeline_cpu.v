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

    /* pipeline registers */

    /* if/id */
    reg [15:0] IF_ID_pc , IF_ID_instr ;
    reg        IF_ID_valid ;

    /* id/ex */
    reg [15:0] ID_EX_pc, ID_EX_instr ;
    reg [15:0] ID_EX_rdata1, ID_EX_rdata2 , ID_EX_imm ;
    reg [3:0]  ID_EX_alu_op ;
    reg [2:0]  ID_EX_rs1, ID_EX_rs2, ID_EX_rd ;
    reg        ID_EX_reg_write, ID_EX_mem_read, ID_EX_mem_write ;
    reg        ID_EX_alu_src, ID_EX_branch, ID_EX_jump, ID_EX_mem_to_reg ;
    reg        ID_EX_valid ;
    

    /* ex/ mem */
    reg [15:0] EX_MEM_pc, EX_MEM_alu_result , EX_MEM_rdata2 ;
    reg [2:0]  EX_MEM_rd ;
    reg        EX_MEM_reg_write, EX_MEM_mem_read, EX_MEM_mem_write ;
    reg        EX_MEM_branch, EX_MEM_jump, EX_MEM_mem_to_reg ;
    reg        EX_MEM_zero , EX_MEM_neg ;
    reg        EX_MEM_valid ;


    /*   mem/ wb  */
    reg [15:0]  MEM_WB_alu_result , MEM_WB_mem_rdata ;
    reg [2:0]   MEM_WB_rd ;
    reg         MEM_WB_reg_write , MEM_WB_mem_to_reg ;
    reg         MEM_WB_valid ;

    /* pc reg */ 
    reg [15:0]  pc;
    reg         halted ;


    assign dbg_pc   = pc ;
    assign dbg_alu_out = EX_MEM_alu_result ;
    assign dbg_halted = halted ;

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