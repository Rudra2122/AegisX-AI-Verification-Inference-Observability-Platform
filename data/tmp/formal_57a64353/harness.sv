
module counter_tb();
  logic clk; logic rst;
  logic [3:0] q;
  counter dut(.clk(clk), .rst(rst), .q(q));

  always begin #1 clk = ~clk; end
  initial begin clk=0; rst=1; #2 rst=0; end

  // Assertions
  property p_inc; @(posedge clk) disable iff (rst) q == $past(q) + 1; endproperty
  assert property(p_inc);
  assert property(@(posedge clk) !$isunknown(q));
endmodule
