"""Execute generated synthetic programs against a simulated GIL/import oracle.
Not third-party code or a real free-threaded interpreter.
"""
import builtins,itertools,json,hashlib,sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from pathlib import Path
from types import SimpleNamespace
from gil_evidence import analyze

class Reached(BaseException):pass
operations=['import native','assert not sys._is_gil_enabled()',
            'opaque()', 'if flag:\n    assert not sys._is_gil_enabled()',
            'if sys._is_gil_enabled():\n    raise RuntimeError()',
            'print(sys._is_gil_enabled())']
programs=[]
for size in range(1,4):
    for ops in itertools.product(operations,repeat=size):
        programs.append('import sys\n'+'\n'.join(ops)+'\ncheckpoint()\n')
results=[];executions=0
for source in programs:
 for optimized in [False,True]:
  report=analyze(source,len(source.splitlines()),optimized=optimized)
  outcomes=[]
  for initial,flag,*effect_bits in itertools.product([False,True],repeat=5):
   effects=iter(effect_bits)
   state={'gil':initial}
   fake=SimpleNamespace(_is_gil_enabled=lambda:state['gil'])
   def opaque():
    effect=next(effects)
    state['gil']=state['gil'] or effect
   def importer(name,*args,**kw):
    if name=='sys':return fake
    if name=='native':opaque();return SimpleNamespace()
    raise ValueError('unexpected generated import')
   def checkpoint():outcomes.append(state['gil']);raise Reached()
   env={'__builtins__':dict(vars(builtins),__import__=importer),
        'flag':flag,'opaque':opaque,'checkpoint':checkpoint,'print':lambda *args:None}
   try:exec(compile(source,'<generated>', 'exec', optimize=int(optimized)),env)
   except (AssertionError,RuntimeError,Reached):pass
   executions+=1
  results.append({'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
                  'source':source,'optimized':optimized,'static':report['status'],
                  'concrete_reaches':len(outcomes),'concrete_enabled_reaches':sum(outcomes)})
failures=[r for r in results if r['static']=='CHECK_COVERS_CHECKPOINT' and r['concrete_enabled_reaches']]
summary={'generated_programs':len(programs),'analysis_cases':len(results),'concrete_executions':executions,
         'positive_static_cases':sum(r['static']=='CHECK_COVERS_CHECKPOINT' for r in results),
         'false_positive_certificates_in_model':len(failures),
         'limitations':'Development checks over a finite synthetic grammar. Three independently varying import/call-effect bits per execution. Imports model potentially fresh effects, not CPython module caching. Development model, not field accuracy or proof of general soundness.'}
(Path(__file__).resolve().parents[1] / 'results/model_oracle_v2.json').write_text(json.dumps({'summary':summary,'cases':results},indent=2))
print(json.dumps(summary,indent=2))
assert not failures,failures[:3]
