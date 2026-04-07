/*
action : top level module for pipelined cpu
instantiates all the 6 stages aand interrupt 
*/

`timescale 1ns/1ns

module top (

    input wire    clk '
    input wire    rst_n,

    /* sensor data ip */
    input wire [15:0] sensor_data_in ,
    input wire        sensor_valid ,

    /* alert op flags */
    output wire       alert_buzzer ,
    output wire       alert_bt ,
    output wire       alert_wifi,

    /* debug */
    output wire [15:0]  dbg_pc ,
    output wire [15:0]  dbg_alu_out ,
    output wire         dbg_halted
);

    /* internal wires */
    wire       irq_sensor ;
    wire       irq_vector ;
    wire [15:0] irq_vector ;

    /* interrupt controller */
    interrupt controller u_irq (

        .clk      (clk) ,
        .rst_n    (rst_n) ,
        .sensor_valid (sensor_valid) ,
        .irq_out (irq_sensor) ,
        .irq_vector (irq_vector)
        .irq_ack (irq_ack)
    );

    /* pipeline cpu */
    pipeline_cpu u_cpu (

        .clk        (clk) ,
        .rst_n      (rst_n) ,
        .sensor_data  (sensor_data_in) ,
        .sensor_valid (sensor_valid) ,
        .irq_vector (irq_vector) ,
        .irq        (irq_sensor) ,
        .irq_ack    (irq_ack) ,
        .alert_buzzer (alert_buzzer) ,
        .alert_bt (alert_bt) ,
        .alert_wifi (alert_wifi) ,
        .dbg_pc (dbg_pc) ,
        .dbg_alu_out (dbg_alu_out) ,
        .dbg_halted (dbg_halted)
    );


endmodule 
