# backend/formal_verifier/templates.py
from pathlib import Path

def write_file(path: Path, text: str):
    path.write_text(text)

# -------- harnesses (no SVA property blocks) --------
def harness_sva(top_module="counter", clk="clk", rst="rst"):
    return f"""
module {top_module}_tb;
    reg {clk} = 0;
    reg {rst} = 1;
    wire [3:0] q;

    {top_module} dut(.{clk}({clk}), .{rst}({rst}), .q(q));

    always @(*) if ($initstate) assume({rst});

    always @(posedge {clk}) begin
        if ($past({rst})) assume(!{rst});
        if ({rst}) begin
            assert(q == 0);
        end else begin
            assert(q == $past(q) + 1);
        end
    end
endmodule
"""

def harness_sva_fsm(top_module="fsm_buggy", clk="clk", rst="rst"):
    return f"""
module {top_module}_tb;
    reg {clk} = 0;
    reg {rst} = 1;
    wire [1:0] state;
    wire out;

    {top_module} dut(.{clk}({clk}), .{rst}({rst}), .state(state), .out(out));

    // Hold reset only at init, then release
    always @(*) if ($initstate) assume({rst});

    always @(posedge {clk}) begin
        if ($past({rst})) assume(!{rst}); // deassert reset after step 0
        if ({rst}) begin
            assert(state == 0);
        end else begin
            // Choose a cover point that is guaranteed reachable (state==3)
            cover(state == 2'b11);
        end
    end
endmodule
"""


# -------- SBY files (no [prove]/[cover] sections) --------
def sby_file(top_tb="counter_tb", design_sv="design.sv", harness_sv="harness.sv"):
    return f"""
[options]
mode prove
depth 20

[engines]
smtbmc z3

[script]
read -formal -sv {design_sv} {harness_sv}
prep -top {top_tb}
flatten
setundef -zero
clk2fflogic

[files]
{design_sv}
{harness_sv}
"""

def sby_file_cover(top_tb="fsm_buggy_tb", design_sv="design.sv", harness_sv="harness.sv"):
    return f"""
[options]
mode cover
depth 20

[engines]
smtbmc z3

[script]
read -formal -sv {design_sv} {harness_sv}
prep -top {top_tb}
flatten
setundef -zero
clk2fflogic

[files]
{design_sv}
{harness_sv}
"""
