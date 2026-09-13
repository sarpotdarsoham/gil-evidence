"""Find pytest skip conditions that mask an explicit disabled-GIL assertion.
Evaluates a small AST subset under concrete interpreter-state assumptions;
never executes input code. Unsupported expressions stay unknown.
"""
import ast,argparse,json
from pathlib import Path

UNKNOWN=object()
def token(name):return ('symbol',name)

class Evaluator:
 def __init__(self,tree,gil_enabled,ft_build):
  self.gil_enabled=gil_enabled;self.ft_build=ft_build;self.env={};self.functions={}
  for n in tree.body:
   if isinstance(n,ast.Import):
    for a in n.names:self.env[a.asname or a.name.split('.')[0]]=token(a.name)
   elif isinstance(n,ast.ImportFrom):
    for a in n.names:
     if a.name=='*':self.env.clear()
     else:self.env[a.asname or a.name]=token((n.module or '')+'.'+a.name) if n.level==0 else UNKNOWN
   elif isinstance(n,ast.FunctionDef):
    self.functions[n.name]=n;self.env[n.name]=token('helper:'+n.name)
   elif isinstance(n,ast.Assign):
    for t in n.targets:
     if isinstance(t,ast.Name):self.env[t.id]=self.expr(n.value,self.env,0)
  # Repeated bindings are not assumed to have the same value at decorator evaluation.
  counts={}
  for n in tree.body:
   names=[]
   if isinstance(n,(ast.Import,ast.ImportFrom)):
    names=[a.asname or a.name.split('.')[0] for a in n.names]
   elif isinstance(n,(ast.FunctionDef,ast.ClassDef)):names=[n.name]
   elif isinstance(n,(ast.Assign,ast.AnnAssign,ast.AugAssign,ast.Delete)):
    names=[x.id for x in ast.walk(n) if isinstance(x,ast.Name) and isinstance(x.ctx,(ast.Store,ast.Del))]
   for name in names:counts[name]=counts.get(name,0)+1
  for name,count in counts.items():
   if count>1:self.env[name]=UNKNOWN
  # Only standard module bindings and simple values are modeled.
 def expr(self,n,env,depth=0):
  if depth>8:return UNKNOWN
  if isinstance(n,ast.Constant):return n.value
  if isinstance(n,ast.Name):return env.get(n.id,UNKNOWN)
  if isinstance(n,ast.Attribute):
   base=self.expr(n.value,env,depth)
   if isinstance(base,tuple) and base[:1]==('symbol',):return token(base[1]+'.'+n.attr)
   return UNKNOWN
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.Not):
   v=self.expr(n.operand,env,depth);return UNKNOWN if v is UNKNOWN else not bool(v)
  if isinstance(n,ast.BoolOp):
   saw_unknown=False;last=None
   for x in n.values:
    v=self.expr(x,env,depth)
    if v is UNKNOWN:saw_unknown=True;continue
    if isinstance(n.op,ast.And) and not bool(v):return False
    if isinstance(n.op,ast.Or) and bool(v):return True
    last=v
   return UNKNOWN if saw_unknown else last
  if isinstance(n,ast.Compare) and len(n.ops)==1:
   a=self.expr(n.left,env,depth);b=self.expr(n.comparators[0],env,depth)
   if a is UNKNOWN or b is UNKNOWN:return UNKNOWN
   if isinstance(n.ops[0],ast.Is):return a is b
   if isinstance(n.ops[0],ast.IsNot):return a is not b
   if isinstance(n.ops[0],ast.Eq):return a==b
   if isinstance(n.ops[0],ast.NotEq):return a!=b
  if isinstance(n,ast.Call) and not n.keywords:
   f=self.expr(n.func,env,depth);args=[self.expr(x,env,depth) for x in n.args]
   if f==token('sys._is_gil_enabled') and not args:return self.gil_enabled
   if f==token('sysconfig.get_config_var') and args==['Py_GIL_DISABLED']:return int(self.ft_build)
   if isinstance(n.func,ast.Name) and n.func.id=='getattr' and 'getattr' not in env and len(args) in (2,3):
    if args[0]==token('sys') and args[1]=='_is_gil_enabled':return token('sys._is_gil_enabled')
   if isinstance(n.func,ast.Name) and n.func.id=='callable' and 'callable' not in env and len(args)==1:
    return True if args[0]==token('sys._is_gil_enabled') else UNKNOWN
   if isinstance(n.func,ast.Name) and not args and n.func.id in self.functions and f==token('helper:'+n.func.id):
    fn=self.functions[n.func.id]
    if fn.decorator_list:return UNKNOWN
    if fn.args.args or fn.args.posonlyargs or fn.args.kwonlyargs or fn.args.vararg or fn.args.kwarg:return UNKNOWN
    local=dict(env)
    for statement in fn.body:
     if isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Constant):continue
     if isinstance(statement,ast.Assign) and all(isinstance(t,ast.Name) for t in statement.targets):
      value=self.expr(statement.value,local,depth+1)
      for t in statement.targets:local[t.id]=value
     elif isinstance(statement,ast.Return):return self.expr(statement.value,local,depth+1)
     else:return UNKNOWN
  return UNKNOWN

def analyze_guards(source):
 tree=ast.parse(source)
 enabled=Evaluator(tree,True,True);disabled=Evaluator(tree,False,True)
 rows=[]
 def skip_conditions(decorators):
  for d in decorators:
   if isinstance(d,ast.Call) and enabled.expr(d.func,enabled.env)==token('pytest.mark.skipif'):
    if len(d.args)==1:yield d.args[0]
 def visit(body,inherited):
  for n in body:
   if isinstance(n,ast.ClassDef):visit(n.body,inherited+list(skip_conditions(n.decorator_list)))
   elif isinstance(n,ast.FunctionDef) and n.name.startswith('test'):
    conditions=inherited+list(skip_conditions(n.decorator_list));assertions=[]
    local_on=dict(enabled.env);local_off=dict(disabled.env)
    # Local stores shadow globals throughout a function, including before assignment.
    for node in ast.walk(n):
     if isinstance(node,ast.Name) and isinstance(node.ctx,(ast.Store,ast.Del)):
      local_on[node.id]=UNKNOWN;local_off[node.id]=UNKNOWN
    for node in ast.walk(n):
     if isinstance(node,(ast.Import,ast.ImportFrom)):
      for alias in node.names:
       name=alias.asname or alias.name.split('.')[0];local_on[name]=UNKNOWN;local_off[name]=UNKNOWN
    for arg in n.args.posonlyargs+n.args.args+n.args.kwonlyargs:
     local_on[arg.arg]=UNKNOWN;local_off[arg.arg]=UNKNOWN
    # Only assertions directly in the test body are recognized; their truth condition is model-evaluated.
    for a in n.body:
     if isinstance(a,ast.Assert):
      x=enabled.expr(a.test,local_on);y=disabled.expr(a.test,local_off)
      if x is False and y is True:assertions.append(a.lineno)
    for condition in conditions:
     x=enabled.expr(condition,enabled.env);y=disabled.expr(condition,disabled.env)
     rows.append({'test':n.name,'test_line':n.lineno,'skip_line':condition.lineno,'skip_expression':ast.unparse(condition),'disabled_gil_assertion_lines':assertions,'skip_if_ft_build_gil_enabled':None if x is UNKNOWN else bool(x),'skip_if_ft_build_gil_disabled':None if y is UNKNOWN else bool(y),'status':'SELF_MASKING_GIL_GUARD_CANDIDATE' if x is True and y is False and assertions else 'NOT_ESTABLISHED','scope':'Under standard CPython 3.13+ API, standard pytest skipif, unchanged import/helper bindings. Test execution and other skip conditions are not established.'})
 visit(tree.body,[])
 return {'findings':rows,'input_executed':False,'warning':'Candidates, not whole-suite defect findings. Unsupported evaluation yields null, not false.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);a=p.parse_args()
 print(json.dumps(analyze_guards(a.source.read_text()),indent=2))
