module counter(input clk, input rst, output logic [3:0] q);
  always_ff @(posedge clk) begin
    if (rst) q <= 4'd0;
    else     q <= q + 1;
  end
endmodule
