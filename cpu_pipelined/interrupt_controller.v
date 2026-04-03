module interrupt_controller (

    input clk,
    input interrupt_signal,
    output reg interrupt_ack
);

always @(posedge clk ) begin
    if (interrupt_signal ) 
        interrupt_ack <= 1;
    
    else 
        interrupt_ack <= 0 ;

end

endmodule