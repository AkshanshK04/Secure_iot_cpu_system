/*
action : monitors sensor valid to generate IRQs to cpu
implements a minimal vectored interrupt with ACK handshake 

IRQ vector : 0x00F0
*/

`timescale 1ns/1ns

module interrupt_controller (

    input wire clk,
    input wire rst_n,
    input wire sensor_valid,
    output reg irq_out,
    input wire irq_ack,
    output wire [15:0] irq_vector
);

    assign irq_vector = 16'h00F0;

    reg prev_sensor_valid ;
    always @(posedge clk or negedge rst_n ) begin
        if (!rst_n ) begin
            prev_sensor_valid <= 1'b0 ;
            irq_out <= 1'b0;
        end else begin 
            prev_sensor_valid <= sensor_valid ;

            if (sensor_valid && !prev_sensor_valid)
                irq_out <= 1'b1;

            if (irq_ack)
                irq_out <= 1'b0;
        end
        
    end



endmodule