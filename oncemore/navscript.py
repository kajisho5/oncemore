"""Navigation commands written by hand: a project's scripts.

A script is a few lines of a small language, run where an action would be
(`commands:<id>`: a menu's or a title's button, a menu's time-out, a
title's end), for what a link alone cannot do: count, remember, choose at
random, ask a pass code. It is dvdauthor's command language with two
changes that keep it from breaking the disc's own navigation:

* **variables** are `$name` instead of general registers: oncemore gives
  each variable of the project a register its own navigation leaves free
  (author.script_registers), so a script cannot clobber them; they start
  at 0 when the disc starts and keep their value (0 to 65535) until a
  script changes them;
* **links** are `play <action>;` with any action a button takes
  (`menu:main`, `title:t2`, `chapter:t1:3`, `playlist:p`, `playall`,
  `lastmenu`, `stop`, `audio:2`, `subtitle:off`), compiled as that action
  is where the script runs; raw `jump` and `call` are not taken.

Statements: `$x = <expression>;` (and `+=`, `-=`, `*=`, `/=`, `%=`, `&=`,
`|=`, `^=` with one value), `audio = …;`, `subtitle = …;`, `angle = …;`,
`button = …;` (the player's own registers, as in dvdauthor: audio stream
from 0, subtitle stream from 0 plus 64 when shown, button number * 1024;
set to a number or a `$name`), `if (<condition>) { … } else { … }` and
`play <action>;`. Values are numbers, `$x`, `audio`, `subtitle`, `angle`
and `button`; an expression is values joined by `+ - * / % & | ^`,
worked out from left to right, the first of them may be `random(n)` (1 to
n, as dvdauthor's manual describes it), and `$x` itself may only come
first in its own expression (it is computed in place, one operation a
command). A condition compares two values (`== != < <= > >=`), one of
them a `$name` or a player register; comparisons are joined by `and` or by
`or`. A script ends with a `play` that leaves (not a sound or subtitle
switch) on every path, so the player always knows where to go.

What a player does when a value leaves 0 to 65535 or is divided by 0 is
not in the public descriptions, so the simulator stops there and says so.

`expand` writes a script in dvdauthor's language for vtskit.lang to
compile; `run` plays it in the disc simulator.
"""

import random as _random
import re
from dataclasses import dataclass

LEAVING = ("menu", "title", "chapter", "playlist", "playall", "lastmenu", "stop")
SYSTEM = ("audio", "subtitle", "angle", "button")
ASSIGN = ("=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=")
COMPARE = ("==", "!=", "<=", ">=", "<", ">")
ARITH = ("+", "-", "*", "/", "%", "&", "|", "^")
# what a number set into a player register may be (SetSTN, SetHL_BTNN)
LIMITS = {"audio": (0, 7), "subtitle": (0, 127), "angle": (1, 9), "button": (1024, 36 * 1024)}

_TOKEN = re.compile(r"\s*(?:(\d+)|\$([A-Za-z_]\w*)|"
                    r"((?:menu|title|chapter|playlist|audio|subtitle):[A-Za-z0-9_:-]+)|"
                    r"([A-Za-z_]\w*)|(==|!=|<=|>=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|&&|\|\||[-+*/%&|^<>=(){};]))")


_ID = r"[A-Za-z0-9_-]{1,40}"
# the actions a play takes (as the project schema's for a button's)
_ACTION = re.compile(rf"(menu:{_ID}(:{_ID})?|title:{_ID}|chapter:{_ID}:[1-9][0-9]*|playlist:{_ID}|"
                     r"audio:[1-8]|subtitle:([1-9]|[12][0-9]|3[0-2]|off)|playall|lastmenu|stop)")


class ScriptError(ValueError):
    pass


@dataclass
class Var:
    name: str


@dataclass
class Sys:
    name: str


@dataclass
class Num:
    value: int


@dataclass
class Rand:
    n: int


@dataclass
class Op:
    left: object
    op: str
    right: object


@dataclass
class Cmp:
    left: object
    op: str
    right: object


@dataclass
class Junction:
    kind: str          # "and" / "or"
    parts: list


@dataclass
class Set:
    target: object     # Var or Sys
    op: str
    value: object


@dataclass
class If:
    cond: object
    then: list
    orelse: list


@dataclass
class Play:
    action: str


def _tokens(text):
    out, pos = [], 0
    text = re.sub(r"#[^\n]*", "", text).strip()          # (comments: # to the end of the line)
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ScriptError(f"cannot read {text[pos:pos + 20].strip()!r}")
        pos = m.end()
        num, var, action, word, sym = m.groups()
        if num is not None:
            out.append(("num", int(num)))
        elif var is not None:
            out.append(("var", var))
        elif action is not None:
            out.append(("action", action))
        elif word is not None:
            out.append(("word", word))
        else:
            out.append(("sym", sym))
    return out


class _Parser:
    def __init__(self, text):
        self.t = _tokens(text)
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self, kind=None, value=None):
        k, v = self.peek()
        if k is None:
            raise ScriptError("the script ends early" + (f" (expected {value!r})" if value else ""))
        if (kind and k != kind) or (value is not None and v != value):
            raise ScriptError(f"expected {value or kind!r}, found {v!r}")
        self.i += 1
        return k, v

    def program(self):
        out = []
        while self.peek()[0] is not None:
            out.append(self.statement())
        return out

    def block(self):
        if self.peek() == ("sym", "{"):
            self.take("sym", "{")
            out = []
            while self.peek() != ("sym", "}"):
                if self.peek()[0] is None:
                    raise ScriptError("the script ends early (expected '}')")
                out.append(self.statement())
            self.take("sym", "}")
            return out
        return [self.statement()]

    def statement(self):
        k, v = self.take()
        if (k, v) == ("word", "if"):
            self.take("sym", "(")
            cond = self.condition()
            self.take("sym", ")")
            then = self.block()
            orelse = []
            if self.peek() == ("word", "else"):
                self.take()
                orelse = self.block()
            return If(cond, then, orelse)
        if (k, v) == ("word", "play"):
            k2, action = self.take()
            if k2 == "word" and action in ("playall", "lastmenu", "stop"):
                pass
            elif k2 != "action" or not _ACTION.fullmatch(action):
                raise ScriptError(f"play takes an action (menu:<id>, title:<id>, …), not {action!r}")
            self.take("sym", ";")
            return Play(action)
        if k == "var" or (k == "word" and v in SYSTEM):
            target = Var(v) if k == "var" else Sys(v)
            _, op = self.take("sym")
            if op not in ASSIGN:
                raise ScriptError(f"{op!r} is not an assignment (=, +=, -=, *=, /=, %=, &=, |=, ^=)")
            if isinstance(target, Sys):
                if op != "=":
                    raise ScriptError(f"{v} takes = only")
                value = self.value()
                if not isinstance(value, (Num, Var)):
                    raise ScriptError(f"{v} is set to a number or a $name")
                low, high = LIMITS[v]
                if isinstance(value, Num) and not (low <= value.value <= high and
                                                   (v != "button" or value.value % 1024 == 0)):
                    raise ScriptError(f"{v} = {value.value}: " + (
                        "a button number * 1024 (1024 to 36864)" if v == "button" else f"{low} to {high}"))
            elif op == "=":
                value = self.expression()
                for node in _chain(value)[1:]:
                    if node == target:
                        raise ScriptError(f"${v} may only come first in its own expression "
                                          f"(${v} = ${v} + …)")
            else:
                value = self.value()
                _no_zero(op[0], value)
            self.take("sym", ";")
            return Set(target, op, value)
        if k == "word" and (v in ("jump", "call") or re.fullmatch(r"[gs]\d+", v)):
            raise ScriptError(f"{v!r}: use play <action> for links and $names for values "
                              "(the disc's own registers are oncemore's)")
        raise ScriptError(f"cannot read the statement starting {v!r}")

    def condition(self):
        parts = [self.conjunction()]
        while self.peek() in (("word", "or"), ("sym", "||")):
            self.take()
            parts.append(self.conjunction())
        if len(parts) == 1:
            return parts[0]
        if any(isinstance(p, Junction) for p in parts):
            raise ScriptError("a condition joins comparisons with and, or with or, not both "
                              "(use an if inside an if)")
        return Junction("or", parts)

    def conjunction(self):
        parts = [self.comparison()]
        while self.peek() in (("word", "and"), ("sym", "&&")):
            self.take()
            parts.append(self.comparison())
        if len(parts) == 1:
            return parts[0]
        if any(isinstance(p, Junction) for p in parts):
            raise ScriptError("a condition joins comparisons with and, or with or, not both "
                              "(use an if inside an if)")
        return Junction("and", parts)

    def comparison(self):
        if self.peek() == ("sym", "("):
            self.take()
            c = self.condition()
            self.take("sym", ")")
            return c
        left = self.value()
        _, op = self.take("sym")
        if op not in COMPARE:
            raise ScriptError(f"{op!r} is not a comparison (==, !=, <, <=, >, >=)")
        right = self.value()
        if isinstance(left, Num) and isinstance(right, Num):
            raise ScriptError(f"{left.value} {op} {right.value} compares two numbers: one side "
                              "is a $name or a player register")
        return Cmp(left, op, right)

    def expression(self):
        left = self.term()
        while self.peek()[0] == "sym" and self.peek()[1] in ARITH:
            _, op = self.take()
            right = self.value()
            _no_zero(op, right)
            left = Op(left, op, right)
        return left

    def value(self):
        """A number, a $name or a player register (not random)."""
        node = self.term()
        if isinstance(node, Rand):
            raise ScriptError("random(n) is the first value of an assignment ($x = random(n) …)")
        return node

    def term(self):
        k, v = self.take()
        if k == "num":
            if not 0 <= v <= 65535:
                raise ScriptError(f"{v} is not 0 to 65535")
            return Num(v)
        if k == "var":
            return Var(v)
        if k == "word" and v in SYSTEM:
            return Sys(v)
        if (k, v) == ("word", "random"):
            self.take("sym", "(")
            _, n = self.take("num")
            self.take("sym", ")")
            if not 1 <= n <= 65535:
                raise ScriptError("random(n) takes n from 1 to 65535")
            return Rand(n)
        raise ScriptError(f"{v!r} is not a value ($name, a number, random(n), audio, subtitle, "
                          "angle or button)")


def _chain(node):
    """An expression's values, left to right."""
    if isinstance(node, Op):
        return _chain(node.left) + [node.right]
    return [node]


def _ops(node):
    if isinstance(node, Op):
        return _ops(node.left) + [node.op]
    return []


def _no_zero(op, value):
    if op in "/%" and value == Num(0):
        raise ScriptError(f"{op} 0: a player's result is not described")


def parse(text):
    """The statements of a script; ScriptError says what is wrong."""
    stmts = _Parser(text).program()
    if not stmts:
        raise ScriptError("the script is empty")
    _no_dead_code(stmts)
    if not _leaves(stmts):
        raise ScriptError("the script must end with play <action> that leaves (a menu, title, "
                          "chapter, playlist, playall, lastmenu or stop) on every path")
    return stmts


def _no_dead_code(stmts):
    for k, s in enumerate(stmts):
        if isinstance(s, If):
            _no_dead_code(s.then)
            _no_dead_code(s.orelse)
        if k + 1 < len(stmts) and _leaves(stmts[:k + 1]):
            raise ScriptError(f"nothing after play {_last_play(stmts[:k + 1])} runs: "
                              "the player has left")


def _last_play(stmts):
    last = stmts[-1]
    return last.action if isinstance(last, Play) else _last_play(last.then)


def _leaves(stmts):
    last = stmts[-1] if stmts else None
    if isinstance(last, Play):
        return kind_of(last.action) in LEAVING
    if isinstance(last, If):
        return _leaves(last.then) and bool(last.orelse) and _leaves(last.orelse)
    return False


def kind_of(action):
    return action.split(":", 1)[0]


def _walk(stmts):
    for s in stmts:
        yield s
        if isinstance(s, If):
            yield from _walk(s.then)
            yield from _walk(s.orelse)


def _values(node):
    if isinstance(node, (Op, Cmp)):
        yield from _values(node.left)
        yield from _values(node.right)
    elif isinstance(node, Junction):
        for p in node.parts:
            yield from _values(p)
    else:
        yield node


def variables(stmts):
    """The script's variables, in the order they first appear."""
    out = []
    for s in _walk(stmts):
        nodes = []
        if isinstance(s, Set):
            nodes = [s.target, *_values(s.value)]
        elif isinstance(s, If):
            nodes = list(_values(s.cond))
        for n in nodes:
            if isinstance(n, Var) and n.name not in out:
                out.append(n.name)
    return out


def plays(stmts):
    """The script's play statements, in order."""
    return [s for s in _walk(stmts) if isinstance(s, Play)]


def actions(stmts):
    """The actions the script plays, in order."""
    return [s.action for s in plays(stmts)]


# -- dvdauthor's language ------------------------------------------------------

def _expr(node, regs):
    if isinstance(node, Num):
        return str(node.value)
    if isinstance(node, Var):
        return regs[node.name]
    if isinstance(node, Sys):
        return node.name
    if isinstance(node, Rand):
        return f"random({node.n})"
    if isinstance(node, Op):
        return f"{_expr(node.left, regs)} {node.op} {_expr(node.right, regs)}"
    if isinstance(node, Cmp):
        return f"{_expr(node.left, regs)} {node.op} {_expr(node.right, regs)}"
    if isinstance(node, Junction):
        sep = " and " if node.kind == "and" else " or "
        return sep.join(f"({_expr(p, regs)})" for p in node.parts)
    raise ScriptError(f"cannot write {node!r}")


def expand(stmts, regs, play):
    """The script in dvdauthor's language, one operation a statement as
    vtskit.lang compiles it: `regs` {variable: "gN"}, `play(action)` the
    command text of an action where the script runs."""
    out = []
    for s in stmts:
        if isinstance(s, Set) and isinstance(s.target, Var) and s.op == "=":
            reg = regs[s.target.name]
            first, *rest = _chain(s.value)
            if first != s.target:
                out.append(f"{reg} = {_expr(first, regs)};")
            out += [f"{reg} {op}= {_expr(v, regs)};" for op, v in zip(_ops(s.value), rest)]
        elif isinstance(s, Set):
            target = regs[s.target.name] if isinstance(s.target, Var) else s.target.name
            out.append(f"{target} {s.op} {_expr(s.value, regs)};")
        elif isinstance(s, Play):
            out.append(play(s.action))
        elif isinstance(s, If):
            text = f"if ({_expr(s.cond, regs)}) {{ {expand(s.then, regs, play)} }}"
            if s.orelse:
                text += f" else {{ {expand(s.orelse, regs, play)} }}"
            out.append(text)
    return " ".join(out)


# -- the simulator ----------------------------------------------------------------

def _value(node, env):
    if isinstance(node, Num):
        return node.value
    if isinstance(node, Var):
        return env["vars"].get(node.name, 0)
    if isinstance(node, Sys):
        return env["get"](node.name)
    if isinstance(node, Rand):
        return env.get("rng", _random).randint(1, node.n)
    raise ScriptError(f"cannot work out {node!r}")


def _apply(a, op, b):
    """a op b as a set command does it; what a player does outside 0 to
    65535 or with a division by 0 is not described, so it stops here."""
    if op in "/%" and b == 0:
        raise ScriptError(f"{a} {op} 0: a player's result is not described")
    r = {"+": a + b, "-": a - b, "*": a * b, "/": a // (b or 1), "%": a % (b or 1),
         "&": a & b, "|": a | b, "^": a ^ b}[op]
    if not 0 <= r <= 65535:
        raise ScriptError(f"{a} {op} {b} = {r}: outside 0 to 65535, a player's result is "
                          "not described")
    return r


def _true(cond, env):
    if isinstance(cond, Junction):
        parts = (_true(p, env) for p in cond.parts)
        return all(parts) if cond.kind == "and" else any(parts)
    a, b = _value(cond.left, env), _value(cond.right, env)
    return {"==": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[cond.op]


def run(stmts, env):
    """Play a script in the simulator: `env` {"vars": {name: value}, "get":
    a player register's value, "set": set one, "play": run an action,
    optionally "rng": a random.Random}. Returns True once an action that
    leaves has been played."""
    for s in stmts:
        if isinstance(s, Set) and isinstance(s.target, Sys):
            env["set"](s.target.name, _value(s.value, env))
        elif isinstance(s, Set):
            name = s.target.name
            if s.op == "=":
                first, *rest = _chain(s.value)
                v = _value(first, env)
                for op, node in zip(_ops(s.value), rest):
                    v = _apply(v, op, _value(node, env))
            else:
                v = _apply(env["vars"].get(name, 0), s.op[0], _value(s.value, env))
            env["vars"][name] = v
        elif isinstance(s, Play):
            env["play"](s.action)
            if kind_of(s.action) in LEAVING:
                return True
        elif isinstance(s, If):
            if run(s.then if _true(s.cond, env) else s.orelse, env):
                return True
    return False
