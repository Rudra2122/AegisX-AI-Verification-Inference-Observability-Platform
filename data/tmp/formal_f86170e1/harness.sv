
// Formal harness for counter: immediate assertions only (no SVA property blocks)
module counter_tb;
    // symbolic clock/reset
    reg clk = 0;
    reg rst = 1;

    // DUT outputs
    wire [3:0] q;

    // DUT
    counter dut(.clk(clk), .rst(rst), .q(q));

    // Drive a symbolic clock: in formal, posedges define steps; no #delays.
    // We don't need to constrain toggling; sby advances on posedges.

    // Reset held high at init, then released after first step.
    always @(*) begin
        if ($initstate) assume(rst);
    end

    // Basic correctness: on reset -> q==0; after reset released -> q increments each cycle
    always @(posedge clk) begin
        if ($past(rst)) begin
            // after cycle 0, we can choose to drop reset
            assume(!rst);
        end

        if (rst) begin
            assert(q == 0);
        end else begin
            assert(q == $past(q) + 1);
        end
    end
endmodule
