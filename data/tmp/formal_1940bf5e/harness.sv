
// Coverage/bug demo harness for fsm_buggy (no SVA property blocks)
module fsm_buggy_tb;
    reg clk = 0;
    reg rst = 1;

    // DUT I/O
    wire [1:0] state;
    wire out;

    fsm_buggy dut(.clk(clk), .rst(rst), .state(state), .out(out));

    always @(*) if ($initstate) assume(rst);

    // Simple safety: during reset, state is 0
    always @(posedge clk) begin
        if (rst) begin
            assert(state == 0);
        end else begin
            // make at least one interesting transition reachable
            cover(state == 2);
        end
        if ($past(rst)) assume(!rst);
    end
endmodule
