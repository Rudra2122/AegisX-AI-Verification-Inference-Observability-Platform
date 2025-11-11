
module fsm_buggy_tb;
    reg clk = 0;
    reg rst = 1;
    wire [1:0] state;
    wire out;

    fsm_buggy dut(.clk(clk), .rst(rst), .state(state), .out(out));

    always @(*) if ($initstate) assume(rst);

    always @(posedge clk) begin
        if ($past(rst)) assume(!rst);
        if (rst) begin
            assert(state == 0);
        end else begin
            cover(state == 2);
        end
    end
endmodule
