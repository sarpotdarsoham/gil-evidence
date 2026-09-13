"""Conservative GIL-check evidence analysis; never executes the input program."""
from __future__ import annotations
import argparse
import ast
from dataclasses import dataclass, replace, asdict
import json
from pathlib import Path

@dataclass(frozen=True)
class State:
    aliases: tuple[tuple[str, str], ...] = ()
    checked_at: int | None = None
    invalidated_at: int | None = None
    trace: tuple[str, ...] = ()

class Analyzer:
    def __init__(self, optimized=False, max_paths=256):
        self.optimized = optimized
        self.max_paths = max_paths
        self.arrivals = []
        self.unsupported = []
        self.checkpoint = None

    def invalidate(self, s, n, why):
        aliases = dict(s.aliases)
        for node in ast.walk(n):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                aliases.pop(node.id, None)
        return replace(s, aliases=tuple(sorted(aliases.items())), checked_at=None, invalidated_at=n.lineno,
                       trace=s.trace + (f'line {n.lineno}: {why}',))

    def query(self, n, s):
        if not isinstance(n, ast.Call) or n.args or n.keywords:
            return False
        aliases = dict(s.aliases)
        f = n.func
        return ((isinstance(f, ast.Attribute) and f.attr == '_is_gil_enabled'
                 and isinstance(f.value, ast.Name) and aliases.get(f.value.id) == 'sys')
                or (isinstance(f, ast.Name) and aliases.get(f.id) == 'query'))

    def polarity(self, n, s):
        """True means expression true implies GIL enabled; False means disabled."""
        if self.query(n, s):
            return True
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            p = self.polarity(n.operand, s)
            return None if p is None else not p
        if isinstance(n, ast.Compare) and len(n.ops) == 1 and self.query(n.left, s):
            c = n.comparators[0]
            if isinstance(c, ast.Constant) and type(c.value) is bool:
                if isinstance(n.ops[0], (ast.Is, ast.Eq)):
                    return c.value
                if isinstance(n.ops[0], (ast.IsNot, ast.NotEq)):
                    return not c.value
        return None

    def branch(self, expr, s, truth):
        p = self.polarity(expr, s)
        if p is not None:
            disabled = truth != p
            return replace(s, checked_at=expr.lineno if disabled else None,
                           trace=s.trace + (f'line {expr.lineno}: GIL query branch {truth}',))
        if isinstance(expr, ast.Constant):
            return s if bool(expr.value) == truth else None
        # Evaluating arbitrary expressions/boolean conversions can execute user code.
        return self.invalidate(s, expr, f'opaque condition, branch {truth}')

    def block(self, body, states):
        for n in body:
            if not states:
                break
            if len(states) > self.max_paths:
                self.unsupported.append({'line':n.lineno, 'reason':'path budget exceeded'})
                return []
            if (n.lineno, n.col_offset) == self.checkpoint:
                self.arrivals.extend(states)
                return []
            next_states = []
            for s in states:
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    s = self.invalidate(s, n, 'import may change GIL state')
                    aliases = dict(s.aliases)
                    if isinstance(n, ast.Import):
                        for a in n.names:
                            name = a.asname or a.name.split('.')[0]
                            aliases.pop(name, None)
                            if a.name == 'sys': aliases[name] = 'sys'
                    else:
                        if any(a.name == '*' for a in n.names):
                            self.unsupported.append({'line':n.lineno,'reason':'star import'})
                        for a in n.names:
                            name = a.asname or a.name
                            aliases.pop(name, None)
                            if n.module == 'sys' and n.level == 0 and a.name == '_is_gil_enabled':
                                aliases[name] = 'query'
                    next_states.append(replace(s, aliases=tuple(sorted(aliases.items()))))
                elif isinstance(n, ast.Assert):
                    if self.optimized:
                        next_states.append(replace(s, trace=s.trace+(f'line {n.lineno}: assert removed under optimization',)))
                    else:
                        q = self.branch(n.test, s, True)
                        if q is not None: next_states.append(q)
                elif isinstance(n, ast.If):
                    for truth, body in [(True,n.body),(False,n.orelse)]:
                        q = self.branch(n.test, s, truth)
                        if q is not None: next_states.extend(self.block(body,[q]))
                elif isinstance(n, (ast.Raise, ast.Return)):
                    # Without supported exception handlers, neither reaches later code in this scope.
                    continue
                elif isinstance(n, ast.Pass):
                    next_states.append(s)
                elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
                    next_states.append(s)
                elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
                    aliases = dict(self.invalidate(s, n, 'binding update').aliases)
                    targets = n.targets if isinstance(n,(ast.Assign,ast.Delete)) else [n.target]
                    for t in targets:
                        for x in ast.walk(t):
                            if isinstance(x, ast.Name): aliases.pop(x.id, None)
                    # Assignment can invoke descriptors/finalizers; retain no evidence across it.
                    next_states.append(replace(self.invalidate(s,n,'assignment/deletion may execute code'),aliases=tuple(sorted(aliases.items()))))
                elif isinstance(n, ast.Expr):
                    next_states.append(self.invalidate(s,n,'opaque expression/call may import or change state'))
                else:
                    self.unsupported.append({'line':n.lineno,'reason':f'unsupported control construct: {type(n).__name__}'})
            states = next_states
        return states

    def analyze(self, source, checkpoint, function=None, column=None):
        tree = ast.parse(source)
        body = tree.body
        if function:
            matches=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==function]
            if len(matches)!=1: raise ValueError('function must name exactly one top-level function')
            body=matches[0].body
        # Checkpoints must start a statement in this scope, not in a nested function/class.
        def candidates(nodes):
            for n in nodes:
                yield (n.lineno, n.col_offset)
                if isinstance(n,ast.If):
                    yield from candidates(n.body); yield from candidates(n.orelse)
        points = [point for point in candidates(body) if point[0] == checkpoint and (column is None or point[1] == column)]
        if len(points) != 1:
            raise ValueError('checkpoint must identify exactly one statement; use --column for same-line statements')
        self.checkpoint = points[0]
        self.block(body,[State()])
        if self.unsupported: status='UNKNOWN'
        elif not self.arrivals: status='UNREACHABLE_IN_MODEL'
        elif all(s.checked_at is not None for s in self.arrivals): status='CHECK_COVERS_CHECKPOINT'
        else: status='CHECK_NOT_ESTABLISHED'
        return {'status':status,'checkpoint_line':checkpoint,'checkpoint_column':self.checkpoint[1],'function':function,
                'optimized':self.optimized,'paths':len(self.arrivals),
                'witness_paths':[asdict(s) for s in self.arrivals],
                'unsupported':self.unsupported,
                'meaning':'Evidence immediately before the selected statement, not inside the called test or proof of thread safety.',
                'assumptions':['standard unmodified sys._is_gil_enabled API and import semantics',
                               'no external concurrent changes, tracing hooks or monkeypatching',
                               'normal continuation only; no proof that the checkpoint actually runs',
                               'function analysis starts without global aliases; import sys inside the selected function'],
                'input_executed':False}

def analyze(source, checkpoint, *, optimized=False, function=None, column=None):
    return Analyzer(optimized).analyze(source,checkpoint,function,column)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--line',type=int,required=True,help='statement line immediately before which evidence is checked')
    p.add_argument('--column',type=int,help='zero-based AST byte column for same-line statements')
    p.add_argument('--function',help='analyze one top-level function body in isolation')
    p.add_argument('--optimized',action='store_true',help='model Python -O/-OO removing asserts')
    a=p.parse_args()
    try: result=analyze(a.source.read_text(),a.line,optimized=a.optimized,function=a.function,column=a.column)
    except (ValueError,SyntaxError) as e: result={'status':'UNKNOWN','error':str(e),'input_executed':False}
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='CHECK_COVERS_CHECKPOINT' else 2
if __name__=='__main__': raise SystemExit(main())
