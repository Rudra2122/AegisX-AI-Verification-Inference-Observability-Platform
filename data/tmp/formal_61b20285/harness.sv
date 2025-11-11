
module fsm_buggy_tb;
    reg clk = 0;
    reg rst = 1;
    wire [1:0] state;
    wire out;

    fsm_buggy dut(.clk(clk), .rst(rst), .state(state), .out(out));

    // Hold reset only at init, then release
    always @(*) if ($initstate) assume(rst);

    always @(posedge clk) begin
        if ($past(rst)) assume(!rst); // deassert reset after step 0
        if (rst) begin
            assert(state == 0);
        end else begin
            // Choose a cover point that is guaranteed reachable (state==3)
            cover(state == 2'b11);
        end
    end
endmodule
