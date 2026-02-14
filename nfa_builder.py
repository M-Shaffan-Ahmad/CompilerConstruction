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
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

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


# Use readable input alphabet for visualization (printable ASCII + common whitespace).
ASCII_ALPHABET: Tuple[str, ...] = tuple(
    [chr(i) for i in range(32, 127)] + ["\t", "\r", "\n"]
)


class DFA:
    def __init__(
        self,
        name: str,
        start_state: int,
        alphabet: Iterable[str],
        transitions: Dict[int, Dict[str, int]],
        accept_states: Set[int],
        accept_labels: Optional[Dict[int, FrozenSet[str]]] = None,
    ) -> None:
        self.name = name
        self.start_state = start_state
        self.alphabet: Tuple[str, ...] = tuple(alphabet)
        self.alphabet_set: Set[str] = set(self.alphabet)
        self.transitions: Dict[int, Dict[str, int]] = defaultdict(dict)
        for src, per_char in transitions.items():
            self.transitions[src].update(per_char)
        self.accept_states: Set[int] = set(accept_states)
        self.accept_labels: Dict[int, FrozenSet[str]] = accept_labels or {}

    def all_states(self) -> List[int]:
        states: Set[int] = {self.start_state}
        states.update(self.accept_states)
        for src, per_char in self.transitions.items():
            states.add(src)
            states.update(per_char.values())
        return sorted(states)

    def accepts(self, text: str) -> bool:
        state = self.start_state
        for ch in text:
            if ch not in self.alphabet_set:
                return False
            state = self.transitions.get(state, {}).get(ch, -1)
            if state == -1:
                return False
        return state in self.accept_states

    def accepted_tokens(self, text: str) -> Set[str]:
        state = self.start_state
        for ch in text:
            if ch not in self.alphabet_set:
                return set()
            state = self.transitions.get(state, {}).get(ch, -1)
            if state == -1:
                return set()
        if state not in self.accept_states:
            return set()
        return set(self.accept_labels.get(state, frozenset()))

    def transition_rows_grouped(self) -> List[Tuple[int, str, int]]:
        rows: List[Tuple[int, str, int]] = []
        trap_states = self.trap_states()
        for src in self.all_states():
            grouped: Dict[int, Set[str]] = defaultdict(set)
            for ch, dst in self.transitions.get(src, {}).items():
                grouped[dst].add(ch)

            # Compact trap-state labels to keep diagrams readable.
            if len(grouped) == 1:
                only_dst = next(iter(grouped))
                only_chars = grouped[only_dst]
                if only_dst in trap_states and only_chars == self.alphabet_set:
                    if src in trap_states and only_dst == src:
                        rows.append((src, "[any]", only_dst))
                    else:
                        rows.append((src, "[other]", only_dst))
                    continue

            if len(grouped) > 1:
                non_trap_chars: Set[str] = set()
                for dst, chars in grouped.items():
                    if dst not in trap_states:
                        non_trap_chars.update(chars)
                for dst in list(grouped.keys()):
                    if dst in trap_states:
                        trap_chars = grouped[dst]
                        complement = self.alphabet_set - non_trap_chars
                        if trap_chars == complement:
                            grouped[dst] = set()

            for dst in sorted(grouped):
                if grouped[dst]:
                    label = _chars_to_label(grouped[dst])
                else:
                    label = "[other]"
                rows.append((src, label, dst))
        return rows

    def to_dot(self, split_traps: bool = False) -> str:
        lines = [
            "digraph DFA {",
            "  rankdir=LR;",
            "  node [shape=circle, width=0.8, height=0.8, fixedsize=true];",
            "  qi [shape=point];",
            f"  qi -> q{self.start_state};",
        ]
        trap_states = self.trap_states() if split_traps else set()
        visible_states = [
            s for s in self.all_states() if s not in trap_states or s == self.start_state
        ]

        for state in visible_states:
            shape = "doublecircle" if state in self.accept_states else "circle"
            label = _escape_dot_label(str(state))
            attrs = [f"shape={shape}", f'label="{label}"']
            if state in self.accept_states and self.accept_labels.get(state):
                token_label = _escape_dot_label(",".join(sorted(self.accept_labels[state])))
                attrs.append(f'xlabel="{token_label}"')
            lines.append(f"  q{state} [{', '.join(attrs)}];")

        if split_traps and trap_states:
            local_traps: Set[Tuple[int, int]] = set()
            for src, label, dst in self.transition_rows_grouped():
                if src in trap_states:
                    continue
                edge_label = _escape_dot_label(label)
                if dst in trap_states:
                    trap_id = f"qt_{src}_{dst}"
                    if (src, dst) not in local_traps:
                        local_traps.add((src, dst))
                        lines.append(f'  {trap_id} [shape=circle, label="T"];')
                        lines.append(f'  {trap_id} -> {trap_id} [label="[any]"];')
                    lines.append(f'  q{src} -> {trap_id} [label="{edge_label}"];')
                else:
                    lines.append(f'  q{src} -> q{dst} [label="{edge_label}"];')
        else:
            for src, label, dst in self.transition_rows_grouped():
                edge_label = _escape_dot_label(label)
                lines.append(f'  q{src} -> q{dst} [label="{edge_label}"];')
        lines.append("}")
        return "\n".join(lines)

    def trap_states(self) -> Set[int]:
        traps: Set[int] = set()
        for s in self.all_states():
            if s in self.accept_states:
                continue
            per_char = self.transitions.get(s, {})
            if not self.alphabet_set.issubset(per_char.keys()):
                continue
            if all(per_char[ch] == s for ch in self.alphabet_set):
                traps.add(s)
        return traps


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


def _render_char(c: str) -> str:
    if c == "\n":
        return r"\n"
    if c == "\t":
        return r"\t"
    if c == "\r":
        return r"\r"
    if c == " ":
        return "space"
    if c == "\\":
        return r"\\"
    if c == '"':
        return r"\""
    code = ord(c)
    if 32 <= code <= 126:
        return c
    return f"\\x{code:02X}"


def _chars_to_label(chars: Set[str]) -> str:
    if not chars:
        return "[]"
    ords = sorted(ord(c) for c in chars)
    parts: List[str] = []
    i = 0
    while i < len(ords):
        j = i
        while j + 1 < len(ords) and ords[j + 1] == ords[j] + 1:
            j += 1
        run_len = j - i + 1
        if run_len >= 4:
            start = _render_char(chr(ords[i]))
            end = _render_char(chr(ords[j]))
            parts.append(f"{start}-{end}")
        else:
            for idx in range(i, j + 1):
                parts.append(_render_char(chr(ords[idx])))
        i = j + 1
    return "[" + " ".join(parts) + "]"


def nfa_to_dfa(
    nfa: NFA,
    nfa_accept_labels: Optional[Dict[int, List[str]]] = None,
    name: Optional[str] = None,
    alphabet: Iterable[str] = ASCII_ALPHABET,
) -> DFA:
    sigma = tuple(dict.fromkeys(alphabet))
    start_subset = frozenset(nfa.epsilon_closure({nfa.start_state}))
    subset_to_id: Dict[FrozenSet[int], int] = {start_subset: 0}
    queue: deque[FrozenSet[int]] = deque([start_subset])
    transitions: Dict[int, Dict[str, int]] = defaultdict(dict)
    accept_states: Set[int] = set()
    accept_labels: Dict[int, FrozenSet[str]] = {}

    while queue:
        subset = queue.popleft()
        dfa_state = subset_to_id[subset]

        token_labels: Set[str] = set()
        for st in subset:
            if st not in nfa.accept_states:
                continue
            if nfa_accept_labels is None:
                token_labels.add(nfa.name)
            else:
                token_labels.update(nfa_accept_labels.get(st, []))
        if token_labels:
            accept_states.add(dfa_state)
            accept_labels[dfa_state] = frozenset(sorted(token_labels))

        for ch in sigma:
            target = frozenset(nfa.epsilon_closure(nfa.move(subset, ch)))
            if not target:
                continue
            if target not in subset_to_id:
                subset_to_id[target] = len(subset_to_id)
                queue.append(target)
            transitions[dfa_state][ch] = subset_to_id[target]

    dfa_name = name if name else f"{nfa.name}_dfa"
    return DFA(
        name=dfa_name,
        start_state=0,
        alphabet=sigma,
        transitions=dict(transitions),
        accept_states=accept_states,
        accept_labels=accept_labels,
    )


def minimize_dfa(dfa: DFA, name: Optional[str] = None) -> DFA:
    sigma = dfa.alphabet
    if not sigma:
        raise ValueError("DFA alphabet must not be empty.")

    # Keep only reachable states from the start state.
    reachable: Set[int] = {dfa.start_state}
    queue: deque[int] = deque([dfa.start_state])
    while queue:
        state = queue.popleft()
        for dst in dfa.transitions.get(state, {}).values():
            if dst not in reachable:
                reachable.add(dst)
                queue.append(dst)

    complete_transitions: Dict[int, Dict[str, int]] = {
        s: dict(dfa.transitions.get(s, {})) for s in reachable
    }
    labels: Dict[int, FrozenSet[str]] = {
        s: dfa.accept_labels.get(s, frozenset()) for s in reachable
    }

    need_dead = any(
        ch not in complete_transitions[s] for s in reachable for ch in sigma
    )
    dead_state = None
    if need_dead:
        dead_state = (max(reachable) + 1) if reachable else 0
        complete_transitions[dead_state] = {ch: dead_state for ch in sigma}
        labels[dead_state] = frozenset()
        for s in list(reachable):
            for ch in sigma:
                complete_transitions[s].setdefault(ch, dead_state)
        reachable.add(dead_state)

    # Initial partition by accepting token label-set signature.
    by_label: Dict[FrozenSet[str], Set[int]] = defaultdict(set)
    for s in reachable:
        by_label[labels.get(s, frozenset())].add(s)
    partitions: List[Set[int]] = [block for block in by_label.values() if block]
    worklist: List[Set[int]] = [set(block) for block in partitions]

    while worklist:
        splitter = worklist.pop()
        for ch in sigma:
            predecessors = {
                s for s in reachable if complete_transitions[s].get(ch) in splitter
            }
            if not predecessors:
                continue

            new_partitions: List[Set[int]] = []
            for block in partitions:
                inter = block & predecessors
                diff = block - predecessors
                if inter and diff:
                    new_partitions.extend([inter, diff])
                    if block in worklist:
                        worklist.remove(block)
                        worklist.append(inter)
                        worklist.append(diff)
                    else:
                        worklist.append(inter if len(inter) <= len(diff) else diff)
                else:
                    new_partitions.append(block)
            partitions = new_partitions

    # Map old states to partition IDs.
    part_by_old_state: Dict[int, int] = {}
    ordered_parts = sorted(partitions, key=lambda p: min(p))
    for part_id, block in enumerate(ordered_parts):
        for s in block:
            part_by_old_state[s] = part_id

    # Reorder minimized states to keep start state at 0 and preserve readability.
    start_part = part_by_old_state[dfa.start_state]
    part_graph: Dict[int, Set[int]] = defaultdict(set)
    for part_id, block in enumerate(ordered_parts):
        rep = next(iter(block))
        for ch in sigma:
            dst = complete_transitions[rep][ch]
            part_graph[part_id].add(part_by_old_state[dst])

    ordered_by_reachability: List[int] = []
    seen_parts: Set[int] = {start_part}
    q_parts: deque[int] = deque([start_part])
    while q_parts:
        p = q_parts.popleft()
        ordered_by_reachability.append(p)
        for nxt in sorted(part_graph[p]):
            if nxt not in seen_parts:
                seen_parts.add(nxt)
                q_parts.append(nxt)
    for p in range(len(ordered_parts)):
        if p not in seen_parts:
            ordered_by_reachability.append(p)

    part_to_new_id = {old: new for new, old in enumerate(ordered_by_reachability)}

    new_transitions: Dict[int, Dict[str, int]] = defaultdict(dict)
    new_accept_states: Set[int] = set()
    new_accept_labels: Dict[int, FrozenSet[str]] = {}
    for part_id, block in enumerate(ordered_parts):
        rep = next(iter(block))
        new_src = part_to_new_id[part_id]
        for ch in sigma:
            dst_old = complete_transitions[rep][ch]
            dst_part = part_by_old_state[dst_old]
            new_transitions[new_src][ch] = part_to_new_id[dst_part]

        lbl = labels.get(rep, frozenset())
        if lbl:
            new_accept_states.add(new_src)
            new_accept_labels[new_src] = lbl

    min_name = name if name else f"{dfa.name}_min"
    return DFA(
        name=min_name,
        start_state=part_to_new_id[start_part],
        alphabet=sigma,
        transitions=dict(new_transitions),
        accept_states=new_accept_states,
        accept_labels=new_accept_labels,
    )


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


def write_dfa_outputs(dfas: Dict[str, DFA], output_dir: Path, suffix: str) -> None:
    for name, dfa in dfas.items():
        dot_path = output_dir / f"{name}_{suffix}.dot"
        table_path = output_dir / f"{name}_{suffix}_table.txt"
        split_traps = suffix == "min_dfa"
        dot_path.write_text(dfa.to_dot(split_traps=split_traps), encoding="utf-8")

        table_lines = [
            f"DFA: {name}_{suffix}",
            f"Start state: {dfa.start_state}",
            f"Accept states: {sorted(dfa.accept_states)}",
            f"State count: {len(dfa.all_states())}",
            "Accept-state token labels:",
        ]
        for state in sorted(dfa.accept_states):
            labels = sorted(dfa.accept_labels.get(state, frozenset()))
            if labels:
                table_lines.append(f"  q{state}: {labels}")

        table_lines.append("Transitions:")
        for src, label, dst in dfa.transition_rows_grouped():
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


def run_dfa_tests(
    nfas: Dict[str, NFA],
    dfas: Dict[str, DFA],
    min_dfas: Dict[str, DFA],
) -> bool:
    all_ok = True
    print("Running DFA consistency tests (NFA vs DFA vs minimized DFA):")
    for name, groups in SAMPLE_TESTS.items():
        nfa = nfas[name]
        dfa = dfas[name]
        min_dfa = min_dfas[name]
        for token in groups["valid"] + groups["invalid"]:
            expected = nfa.accepts(token)
            ok_dfa = dfa.accepts(token) == expected
            ok_min = min_dfa.accepts(token) == expected
            ok = ok_dfa and ok_min
            print(
                f"  [{name}] {token!r:<36} -> DFA:{ok_dfa} MinDFA:{ok_min}"
            )
            if not ok:
                all_ok = False
    print("All DFA consistency tests passed." if all_ok else "Some DFA consistency tests failed.")
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


def run_combined_dfa_tests(
    combined: NFA,
    accept_labels: Dict[int, List[str]],
    combined_dfa: DFA,
    combined_min_dfa: DFA,
) -> bool:
    cases = [
        "## hello",
        "true",
        "Count_2",
        "-0.125e3",
        "+99",
        "+",
        ";",
        "1.2345678",
        "count",
    ]
    all_ok = True
    print("Running combined DFA consistency tests:")
    for text in cases:
        expected = combined_accept_tokens(combined, accept_labels, text)
        got_dfa = combined_dfa.accepted_tokens(text)
        got_min = combined_min_dfa.accepted_tokens(text)
        ok_dfa = got_dfa == expected
        ok_min = got_min == expected
        print(
            f"  [combined] {text!r:<20} -> DFA:{sorted(got_dfa)} MinDFA:{sorted(got_min)}"
        )
        if not (ok_dfa and ok_min):
            all_ok = False
    print("All combined DFA tests passed." if all_ok else "Some combined DFA tests failed.")
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
    dfas = {name: nfa_to_dfa(nfa, name=f"{name}_dfa") for name, nfa in nfas.items()}
    min_dfas = {
        name: minimize_dfa(dfa, name=f"{name}_min_dfa")
        for name, dfa in dfas.items()
    }
    combined_dfa = nfa_to_dfa(
        combined,
        nfa_accept_labels=accept_labels,
        name="combined_dfa",
    )
    combined_min_dfa = minimize_dfa(combined_dfa, name="combined_min_dfa")
    output_dir = Path(args.output_dir)
    write_outputs(nfas, output_dir)
    write_combined_output(combined, accept_labels, output_dir)
    write_dfa_outputs(dfas, output_dir, "dfa")
    write_dfa_outputs(min_dfas, output_dir, "min_dfa")
    write_dfa_outputs({"combined": combined_dfa}, output_dir, "dfa")
    write_dfa_outputs({"combined": combined_min_dfa}, output_dir, "min_dfa")
    print(f"Wrote NFA/DFA files to: {output_dir}")

    if args.render_png:
        render_pngs(output_dir)

    if args.run_tests:
        per_token_ok = run_tests(nfas)
        combined_ok = run_combined_tests(combined, accept_labels)
        dfa_ok = run_dfa_tests(nfas, dfas, min_dfas)
        combined_dfa_ok = run_combined_dfa_tests(
            combined,
            accept_labels,
            combined_dfa,
            combined_min_dfa,
        )
        if not (per_token_ok and combined_ok and dfa_ok and combined_dfa_ok):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
