from pathlib import Path
import subprocess,sys,json,hashlib,datetime
R=Path(__file__).resolve().parent;P=R.parent.parent;W=P.parent.parent
sys.path.insert(0,str(P));from gil_evidence import analyze
# Own purpose-built fixtures only. No historical target package or experiment is executed.
def run(cmd):
 d=subprocess.run(cmd,cwd=R,capture_output=True,text=True,timeout=30)
 return {'command':cmd,'exit':d.returncode,'stdout':d.stdout,'stderr':d.stderr}
def config(p):
 d=run([str(p),'-I','-B','-S','-c','import sys,sysconfig,json;print(json.dumps({"version":sys.version,"gil":sys._is_gil_enabled(),"include":sysconfig.get_path("include"),"suffix":sysconfig.get_config_var("EXT_SUFFIX")}))']);assert d['exit']==0;return json.loads(d['stdout'])
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--ft-python',type=Path,required=True);parser.add_argument('--normal-python',type=Path,required=True);args=parser.parse_args();ft=args.ft_python.resolve();normal=args.normal_python.resolve()
cfg=config(ft);build=[]
for name in ['legacy_fixture','declared_fixture']:
 cmd=['/usr/bin/clang','-bundle','-undefined','dynamic_lookup','-I'+cfg['include'],str(R/(name+'.c')),'-o',str(R/(name+cfg['suffix']))]
 d=run(cmd);build.append(d);assert d['exit']==0,d
cases=[
 ('early_check','import sys\nassert not sys._is_gil_enabled()\nimport legacy_fixture\n',[],True,0),
 ('late_check','import sys\nimport legacy_fixture\nassert not sys._is_gil_enabled()\n',[],None,1),
 ('late_check_optimized','import sys\nimport legacy_fixture\nassert not sys._is_gil_enabled()\n',['-O'],True,0),
 ('declared_late_check','import sys\nimport declared_fixture\nassert not sys._is_gil_enabled()\n',[],False,0),
 ('explicit_guard','import sys\nimport legacy_fixture\nif sys._is_gil_enabled():\n    raise RuntimeError("GIL enabled")\n',['-O'],None,1),
 ('forced_disabled','import sys\nimport legacy_fixture\nassert not sys._is_gil_enabled()\n',['-X','gil=0'],False,0),
 ('logging_only','import sys\nimport legacy_fixture\nprint("LOG", sys._is_gil_enabled())\n',[],True,0),
 ('opaque_import','import sys\nassert not sys._is_gil_enabled()\n__import__("legacy_fixture")\n',[],True,0),
]
results=[]
for name,body,flags,expected_gil,expected_exit in cases:
 source=body+'print("CHECKPOINT", sys._is_gil_enabled())\n'
 (R/(name+'.py')).write_text(source)
 prefix='import sys; sys.path.insert(0, '+repr(str(R))+')\n'
 d=run([str(ft),'-I','-B','-S',*flags,'-c',prefix+source])
 lines=[l for l in d['stdout'].splitlines() if l.startswith('CHECKPOINT ')]
 observed=(lines[-1]=='CHECKPOINT True') if lines else None
 static=analyze(source,len(source.splitlines()),optimized='-O' in flags)
 ok=d['exit']==expected_exit and observed==expected_gil
 results.append({'name':name,'expected_gil_at_checkpoint':expected_gil,'observed_gil_at_checkpoint':observed,'expected_exit':expected_exit,'matched_expectation':ok,'static':static,**d})
 assert ok,results[-1]
 assert not(static['status']=='CHECK_COVERS_CHECKPOINT' and observed is True)
# A successful check in one process is not transferable to a later process.
a=run([str(ft),'-I','-B','-S','-c','import sys; assert not sys._is_gil_enabled(); print("CHECK_PROCESS", sys._is_gil_enabled())'])
b=run([str(ft),'-I','-B','-S','-c','import sys; sys.path.insert(0, '+repr(str(R))+'); import legacy_fixture; print("TEST_PROCESS", sys._is_gil_enabled())'])
assert a['exit']==b['exit']==0 and 'False' in a['stdout'] and 'True' in b['stdout']
normal_check=run([str(normal),'-I','-B','-S','-c','import sys; print("GIL", sys._is_gil_enabled()); assert not sys._is_gil_enabled()'])
assert normal_check['exit']==1 and 'GIL True' in normal_check['stdout']
out={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':'macOS arm64','ft_config':cfg,'normal_config':config(normal),'builds':build,'cases':results,'separate_processes':[a,b],'normal_interpreter_negative_control':normal_check,'summary':{'runtime_cases':len(results),'matched':sum(r['matched_expectation'] for r in results),'static_positive_enabled_counterexamples':sum(r['static']['status']=='CHECK_COVERS_CHECKPOINT' and r['observed_gil_at_checkpoint'] is True for r in results)},'limitations':'Purpose-built stateless fixtures on one OS/architecture and Python release. Tests documented interpreter behavior, not new CPython or third-party defects. Positive static coverage is conditional on reaching the checkpoint.'}
(P/'results/runtime_validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out['summary'],indent=2))
