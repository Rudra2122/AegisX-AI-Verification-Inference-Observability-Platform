module counter(input clk, input rst, output [3:0] q);
  reg [3:0] r;
  assign q = r;

  always @(posedge clk) begin
    if (rst) r <= 4'd0;
    else     r <= r + 1;
  end
endmodule
