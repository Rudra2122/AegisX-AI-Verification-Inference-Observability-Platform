// data/rtl_samples/fsm_buggy.sv (intentional bug for FAIL + VCD)
module fsm_buggy(input clk, input rst, input a, output logic y);
  typedef enum logic [1:0] {S0=2'b00,S1=2'b01,S2=2'b10} state_t;
  state_t s, ns;

  always_ff @(posedge clk) begin
    if (rst) s <= S0;
    else     s <= ns;
  end

  // BUG: missing transition out of S2 when a=0 (latch-like)
  always_comb begin
    ns = s;
    case (s)
      S0: ns = a ? S1 : S0;
      S1: ns = a ? S2 : S0;
      S2: ns = a ? S2 : S2; // stuck
    endcase
  end

  assign y = (s==S2);
endmodule
