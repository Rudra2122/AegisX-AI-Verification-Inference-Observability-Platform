module fsm_buggy(input clk, input rst, output [1:0] state, output out);
  reg [1:0] s;
  reg o;
  assign state = s;
  assign out   = o;

  always @(posedge clk) begin
    if (rst) begin
      s <= 2'd0; o <= 1'b0;
    end else begin
      case (s)
        2'd0: begin s <= 2'd1; o <= 1'b0; end
        2'd1: begin s <= 2'd2; o <= 1'b1; end
        2'd2: begin s <= 2'd3; o <= 1'b0; end
        2'd3: begin s <= 2'd3; o <= 1'b0; end // stuck (intentional bug)
      endcase
    end
  end
endmodule
