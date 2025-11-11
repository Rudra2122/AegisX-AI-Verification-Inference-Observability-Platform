
module fsm_buggy_tb();
  logic clk; logic rst; logic a; logic y;
  fsm_buggy dut(.clk(clk), .rst(rst), .a(a), .y(y));

  always begin #1 clk = ~clk; end
  initial begin clk=0; rst=1; a=0; #2 rst=0; end

  // Cover: eventually reach y==1
  cover property (@(posedge clk) y==1);

  // Assert: y must deassert when a=0 within 4 cycles (violated by bug)
  property p_clear; @(posedge clk) disable iff (rst) a==0 |=> ##[1:4] (y==0); endproperty
  assert property(p_clear);
endmodule
