#!/usr/bin/env python3
r"""
Build NFAs for selected token classes from CC Assignment 1.

Generated token NFAs:
- single-line comments: ##[^\n]*
- boolean literals: (true|false)
- identifiers: [A-Z][a-z0-9_]{0,30}
- floating-point literals: [+-]?[0-9]+\.[0-9]{1,6}([eE][+-]?[0-9]+)?
- integer literals: [+-]?[0-9]+
- punctuators: [(){}[\],;:]
- single-character operators: [+\-*/%<>=!]

Usage:
  python3 nfa_builder.py --run-tests
  python3 nfa_builder.py --output-dir nfa_output --render-png
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

Predicate = Callable[[str], bool]


@dataclass
class Transition:
    src: int
    dst: int
    label: str
    predicate: Optional[Predicate] = None  # None means epsilon


class NFA:
    def __init__(self, name: str) -> None:
        self.name = name
        self._next_state = 0
        self.start_state = self.new_state()
        self.accept_states: Set[int] = set()
        self.transitions: Dict[int, List[Transition]] = defaultdict(list)

    def new_state(self) -> int:
        sid = self._next_state
        self._next_state += 1
        return sid

    def add_transition(
        self,
        src: int,
        dst: int,
        label: str,
        predicate: Predicate,
    ) -> None:
        self.transitions[src].append(
            Transition(src=src, dst=dst, label=label, predicate=predicate)
        )

    def add_epsilon(self, src: int, dst: int) -> None:
        self.transitions[src].append(Transition(src=src, dst=dst, label="λ"))

    def set_accept(self, *states: int) -> None:
        self.accept_states.update(states)

    def epsilon_closure(self, states: Iterable[int]) -> Set[int]:
        closure = set(states)
        stack = list(states)
        while stack:
            state = stack.pop()
            for t in self.transitions.get(state, []):
                if t.predicate is None and t.dst not in closure:
                    closure.add(t.dst)
                    stack.append(t.dst)
        return closure

    def move(self, states: Iterable[int], ch: str) -> Set[int]:
        out: Set[int] = set()
        for state in states:
            for t in self.transitions.get(state, []):
                if t.predicate is not None and t.predicate(ch):
                    out.add(t.dst)
        return out

    def accepts(self, text: str) -> bool:
        current = self.epsilon_closure({self.start_state})
        for ch in text:
            current = self.epsilon_closure(self.move(current, ch))
            if not current:
                return False
        return bool(current & self.accept_states)

    def all_states(self) -> List[int]:
        return list(range(self._next_state))

    def transition_rows(self) -> List[Tuple[int, str, int]]:
        rows: List[Tuple[int, str, int]] = []
        for src in self.all_states():
            for t in self.transitions.get(src, []):
                rows.append((src, t.label, t.dst))
        return rows

    def to_dot(self) -> str:
        lines = [
            "digraph NFA {",
            "  rankdir=LR;",
            "  node [shape=circle];",
            "  qi [shape=point];",
            f"  qi -> q{self.start_state};",
        ]

        for state in self.all_states():
            shape = "doublecircle" if state in self.accept_states else "circle"
            lines.append(f'  q{state} [shape={shape}, label="{state}"];')

        for src in self.all_states():
            for t in self.transitions.get(src, []):
                label = _escape_dot_label(t.label)
                lines.append(f'  q{src} -> q{t.dst} [label="{label}"];')

        lines.append("}")
        return "\n".join(lines)


COMBINED_PRIORITY = [
    "single_line_comment",
    "boolean_literal",
    "identifier",
    "floating_point_literal",
    "integer_literal",
    "single_char_operator",
    "punctuator",
]


def _escape_dot_label(label: str) -> str:
    return label.replace("\\", "\\\\").replace('"', '\\"')


def _one_of(chars: str) -> Predicate:
    char_set = set(chars)
    return lambda c: c in char_set


def _exact(ch: str) -> Predicate:
    return lambda c: c == ch


def _is_digit(c: str) -> bool:
    return c.isdigit()


def _is_upper(c: str) -> bool:
    return "A" <= c <= "Z"


def _is_identifier_tail(c: str) -> bool:
    return ("a" <= c <= "z") or c.isdigit() or c == "_"


def _not_newline(c: str) -> bool:
    return c != "\n"


def _add_literal_path(nfa: NFA, src: int, literal: str) -> int:
    current = src
    for ch in literal:
        nxt = nfa.new_state()
        nfa.add_transition(current, nxt, ch, _exact(ch))
        current = nxt
    return current


def build_integer_nfa() -> NFA:
    # Regex: [+-]?[0-9]+
    nfa = NFA("integer_literal")
    s0 = nfa.start_state
    s1 = nfa.new_state()  # after optional sign
    s2 = nfa.new_state()  # first/next digit

    nfa.add_transition(s0, s1, "[+-]", _one_of("+-"))
    nfa.add_transition(s0, s2, "[0-9]", _is_digit)
    nfa.add_transition(s1, s2, "[0-9]", _is_digit)
    nfa.add_transition(s2, s2, "[0-9]", _is_digit)
    nfa.set_accept(s2)
    return nfa


def build_floating_point_nfa() -> NFA:
    # Regex: [+-]?[0-9]+\.[0-9]{1,6}([eE][+-]?[0-9]+)?
    nfa = NFA("floating_point_literal")
    s0 = nfa.start_state
    s1 = nfa.new_state()  # after optional sign
    s2 = nfa.new_state()  # integer part (at least one digit)
    s3 = nfa.new_state()  # dot

    nfa.add_transition(s0, s1, "[+-]", _one_of("+-"))
    nfa.add_transition(s0, s2, "[0-9]", _is_digit)
    nfa.add_transition(s1, s2, "[0-9]", _is_digit)
    nfa.add_transition(s2, s2, "[0-9]", _is_digit)
    nfa.add_transition(s2, s3, ".", _exact("."))

    # Fractional part: 1..6 digits
    frac_states: List[int] = []
    prev = s3
    for _ in range(6):
        st = nfa.new_state()
        frac_states.append(st)
        nfa.add_transition(prev, st, "[0-9]", _is_digit)
        prev = st

    # Accept after 1..6 fraction digits (without exponent)
    nfa.set_accept(*frac_states)

    # Optional exponent: [eE][+-]?[0-9]+ from any accepted frac length
    s_exp_mark = nfa.new_state()
    s_exp_sign = nfa.new_state()
    s_exp_digits = nfa.new_state()
    for fs in frac_states:
        nfa.add_transition(fs, s_exp_mark, "[eE]", _one_of("eE"))

    nfa.add_transition(s_exp_mark, s_exp_sign, "[+-]", _one_of("+-"))
    nfa.add_transition(s_exp_mark, s_exp_digits, "[0-9]", _is_digit)
    nfa.add_transition(s_exp_sign, s_exp_digits, "[0-9]", _is_digit)
    nfa.add_transition(s_exp_digits, s_exp_digits, "[0-9]", _is_digit)
    nfa.set_accept(s_exp_digits)
    return nfa


def build_identifier_nfa() -> NFA:
    # Regex: [A-Z][a-z0-9_]{0,30}
    nfa = NFA("identifier")
    s0 = nfa.start_state
    s1 = nfa.new_state()  # first uppercase char
    nfa.add_transition(s0, s1, "[A-Z]", _is_upper)

    # Total max length is 31 => up to 30 tail chars
    nfa.set_accept(s1)
    prev = s1
    for _ in range(30):
        nxt = nfa.new_state()
        nfa.add_transition(prev, nxt, "[a-z0-9_]", _is_identifier_tail)
        nfa.set_accept(nxt)
        prev = nxt
    return nfa


def build_single_line_comment_nfa() -> NFA:
    # Regex: ##[^\n]*
    nfa = NFA("single_line_comment")
    s0 = nfa.start_state
    s1 = nfa.new_state()
    s2 = nfa.new_state()

    nfa.add_transition(s0, s1, "#", _exact("#"))
    nfa.add_transition(s1, s2, "#", _exact("#"))
    nfa.add_transition(s2, s2, "[^\\n]", _not_newline)
    nfa.set_accept(s2)
    return nfa


def build_boolean_nfa() -> NFA:
    # Regex: (true|false)
    nfa = NFA("boolean_literal")
    s0 = nfa.start_state
    s_true_start = nfa.new_state()
    s_false_start = nfa.new_state()
    nfa.add_epsilon(s0, s_true_start)
    nfa.add_epsilon(s0, s_false_start)

    s_true_end = _add_literal_path(nfa, s_true_start, "true")
    s_false_end = _add_literal_path(nfa, s_false_start, "false")
    nfa.set_accept(s_true_end, s_false_end)
    return nfa


def build_punctuator_nfa() -> NFA:
    # Regex: [(){}[\],;:]
    punctuators = "(){}[],;:"
    nfa = NFA("punctuator")
    s0 = nfa.start_state
    s1 = nfa.new_state()
    nfa.add_transition(s0, s1, "[(){}[],;:]", _one_of(punctuators))
    nfa.set_accept(s1)
    return nfa


def build_single_char_operator_nfa() -> NFA:
    # Single-char subset from operators: [+\-*/%<>=!]
    operators = "+-*/%<>=!"
    nfa = NFA("single_char_operator")
    s0 = nfa.start_state
    s1 = nfa.new_state()
    nfa.add_transition(s0, s1, "[+\\-*/%<>=!]", _one_of(operators))
    nfa.set_accept(s1)
    return nfa


def build_all_nfas() -> Dict[str, NFA]:
    return {
        "single_line_comment": build_single_line_comment_nfa(),
        "boolean_literal": build_boolean_nfa(),
        "identifier": build_identifier_nfa(),
        "floating_point_literal": build_floating_point_nfa(),
        "integer_literal": build_integer_nfa(),
        "punctuator": build_punctuator_nfa(),
        "single_char_operator": build_single_char_operator_nfa(),
    }


def build_combined_nfa(
    nfas: Dict[str, NFA],
    priority: Optional[List[str]] = None,
) -> Tuple[NFA, Dict[int, List[str]]]:
    """
    Combine token NFAs into one NFA with a fresh start state and epsilon fan-out.

    Returns:
      - combined NFA
      - mapping: accept_state -> token type list (priority ordered)
    """
    order = priority[:] if priority else list(nfas.keys())
    combined = NFA("combined_nfa")
    accept_labels: Dict[int, List[str]] = defaultdict(list)

    for token_name in order:
        sub = nfas[token_name]
        state_map: Dict[int, int] = {}

        for st in sub.all_states():
            state_map[st] = combined.new_state()

        combined.add_epsilon(combined.start_state, state_map[sub.start_state])

        for src in sub.all_states():
            for t in sub.transitions.get(src, []):
                new_src = state_map[src]
                new_dst = state_map[t.dst]
                if t.predicate is None:
                    combined.add_epsilon(new_src, new_dst)
                else:
                    combined.add_transition(new_src, new_dst, t.label, t.predicate)

        for acc in sub.accept_states:
            new_acc = state_map[acc]
            combined.set_accept(new_acc)
            accept_labels[new_acc].append(token_name)

    return combined, dict(accept_labels)


def combined_accept_tokens(
    combined: NFA,
    accept_labels: Dict[int, List[str]],
    text: str,
) -> Set[str]:
    current = combined.epsilon_closure({combined.start_state})
    for ch in text:
        current = combined.epsilon_closure(combined.move(current, ch))
        if not current:
            return set()

    tokens: Set[str] = set()
    for state in current:
        if state in combined.accept_states:
            tokens.update(accept_labels.get(state, []))
    return tokens


SAMPLE_TESTS: Dict[str, Dict[str, List[str]]] = {
    "single_line_comment": {
        "valid": ["##", "## hello", "##x123!?"],
        "invalid": ["#", " #", ""],
    },
    "boolean_literal": {
        "valid": ["true", "false"],
        "invalid": ["True", "FALSE", "truth", "falsey"],
    },
    "identifier": {
        "valid": ["A", "Count", "X1", "Z_9", "A" + ("a" * 30)],
        "invalid": ["count", "2Count", "A" + ("a" * 31), "A-B"],
    },
    "floating_point_literal": {
        "valid": ["3.14", "+2.5", "-0.123456", "1.5e10", "2.0E-3"],
        "invalid": ["3.", ".14", "1.2345678", "1e10", "+.5", "12"],
    },
    "integer_literal": {
        "valid": ["42", "+100", "-567", "0"],
        "invalid": ["", "+", "-", "12.34", "1,000"],
    },
    "punctuator": {
        "valid": ["(", ")", "{", "}", "[", "]", ",", ";", ":"],
        "invalid": ["::", "a", ""],
    },
    "single_char_operator": {
        "valid": ["+", "-", "*", "/", "%", "<", ">", "=", "!"],
        "invalid": ["++", "==", "**", "a", ""],
    },
}


def write_outputs(nfas: Dict[str, NFA], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, nfa in nfas.items():
        dot_path = output_dir / f"{name}.dot"
        table_path = output_dir / f"{name}_table.txt"
        dot_path.write_text(nfa.to_dot(), encoding="utf-8")

        rows = nfa.transition_rows()
        table_lines = [
            f"NFA: {name}",
            f"Start state: {nfa.start_state}",
            f"Accept states: {sorted(nfa.accept_states)}",
            "Transitions:",
        ]
        for src, label, dst in rows:
            table_lines.append(f"  q{src} --{label}--> q{dst}")
        table_path.write_text("\n".join(table_lines) + "\n", encoding="utf-8")


def write_combined_output(
    combined: NFA,
    accept_labels: Dict[int, List[str]],
    output_dir: Path,
) -> None:
    dot_path = output_dir / "combined_nfa.dot"
    table_path = output_dir / "combined_nfa_table.txt"
    dot_path.write_text(combined.to_dot(), encoding="utf-8")

    table_lines = [
        "NFA: combined_nfa",
        f"Start state: {combined.start_state}",
        f"Accept states: {sorted(combined.accept_states)}",
        f"Priority order: {COMBINED_PRIORITY}",
        "Accept-state token labels:",
    ]
    for state in sorted(accept_labels):
        table_lines.append(f"  q{state}: {accept_labels[state]}")

    table_lines.append("Transitions:")
    for src, label, dst in combined.transition_rows():
        table_lines.append(f"  q{src} --{label}--> q{dst}")

    table_path.write_text("\n".join(table_lines) + "\n", encoding="utf-8")


def render_pngs(output_dir: Path) -> None:
    dot_bin = shutil.which("dot")
    if not dot_bin:
        print("Graphviz 'dot' not found. Skipping PNG rendering.")
        return

    for dot_file in sorted(output_dir.glob("*.dot")):
        png_file = dot_file.with_suffix(".png")
        subprocess.run(
            [dot_bin, "-Tpng", str(dot_file), "-o", str(png_file)],
            check=False,
        )
    print(f"Rendered PNG files in: {output_dir}")


def run_tests(nfas: Dict[str, NFA]) -> bool:
    all_ok = True
    print("Running sample acceptance tests:")
    for name, groups in SAMPLE_TESTS.items():
        nfa = nfas[name]
        for token in groups["valid"]:
            ok = nfa.accepts(token)
            print(f"  [{name}] valid   {token!r:<36} -> {ok}")
            if not ok:
                all_ok = False
        for token in groups["invalid"]:
            ok = not nfa.accepts(token)
            print(f"  [{name}] invalid {token!r:<36} -> {ok}")
            if not ok:
                all_ok = False
    print("All per-token tests passed." if all_ok else "Some per-token tests failed.")
    return all_ok


def run_combined_tests(
    combined: NFA,
    accept_labels: Dict[int, List[str]],
) -> bool:
    cases = [
        ("## hello", {"single_line_comment"}),
        ("true", {"boolean_literal"}),
        ("Count_2", {"identifier"}),
        ("-0.125e3", {"floating_point_literal"}),
        ("+99", {"integer_literal"}),
        ("+", {"single_char_operator"}),
        (";", {"punctuator"}),
        ("1.2345678", set()),
        ("count", set()),
    ]
    all_ok = True
    print("Running combined NFA tests:")
    for text, expected in cases:
        got = combined_accept_tokens(combined, accept_labels, text)
        ok = got == expected
        print(f"  [combined] {text!r:<20} -> {sorted(got)} expected {sorted(expected)} : {ok}")
        if not ok:
            all_ok = False
    print("All combined tests passed." if all_ok else "Some combined tests failed.")
    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate NFAs for assignment token types.")
    parser.add_argument(
        "--output-dir",
        default="nfa_output",
        help="Directory where .dot and transition tables are written",
    )
    parser.add_argument(
        "--render-png",
        action="store_true",
        help="Also render .png diagrams using Graphviz dot",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run built-in acceptance tests for each NFA",
    )
    args = parser.parse_args()

    nfas = build_all_nfas()
    combined, accept_labels = build_combined_nfa(nfas, COMBINED_PRIORITY)
    output_dir = Path(args.output_dir)
    write_outputs(nfas, output_dir)
    write_combined_output(combined, accept_labels, output_dir)
    print(f"Wrote NFA files to: {output_dir}")

    if args.render_png:
        render_pngs(output_dir)

    if args.run_tests:
        per_token_ok = run_tests(nfas)
        combined_ok = run_combined_tests(combined, accept_labels)
        if not (per_token_ok and combined_ok):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
