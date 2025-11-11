
module counter_tb;
    reg clk = 0;
    reg rst = 1;
    wire [3:0] q;

    counter dut(.clk(clk), .rst(rst), .q(q));

    always @(*) if ($initstate) assume(rst);

    always @(posedge clk) begin
        if ($past(rst)) assume(!rst);
        if (rst) begin
            assert(q == 0);
        end else begin
            assert(q == $past(q) + 1);
        end
    end
endmodule
