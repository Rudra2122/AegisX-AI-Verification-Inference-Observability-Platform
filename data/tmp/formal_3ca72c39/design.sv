module fsm_buggy(input clk, input rst, output logic [1:0] state, output logic out);
  always_ff @(posedge clk) begin
    if (rst) begin
      state <= 2'd0; out <= 0;
    end else begin
      case (state)
        2'd0: begin state <= 2'd1; out <= 0; end
        2'd1: begin state <= 2'd2; out <= 1; end
        2'd2: begin state <= 2'd3; out <= 0; end
        2'd3: begin state <= 2'd3; out <= 0; end // stuck bug
      endcase
    end
  end
endmodule
