from pathlib import Path
import subprocess,json,os,sys,datetime
R=Path(__file__).resolve().parent;P=R.parent.parent;W=P.parent.parent;sys.path.insert(0,str(P));from guard_evidence import analyze_guards
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--ft-python',type=Path,required=True);parser.add_argument('--normal-python',type=Path,required=True);args=parser.parse_args();ft=args.ft_python.resolve();normal=args.normal_python.resolve()
d=subprocess.run([str(normal),'-I','-S','-B','-c','import sysconfig,json;print(json.dumps([sysconfig.get_path("include"),sysconfig.get_config_var("EXT_SUFFIX")]))'],capture_output=True,text=True,check=True)
include,suffix=json.loads(d.stdout)
cmd=['/usr/bin/clang','-bundle','-undefined','dynamic_lookup','-I'+include,str(R/'legacy_fixture.c'),'-o',str(R/('legacy_fixture'+suffix))]
subprocess.run(cmd,capture_output=True,text=True,check=True)
root=R/'guard_cases';root.mkdir(exist_ok=True)
helper='''def _is_free_threaded():
    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    return callable(is_gil_enabled) and not is_gil_enabled()
'''
rows=[]
for context,interpreter,module in [('ft_legacy',ft,'legacy_fixture'),('ft_declared',ft,'declared_fixture'),('normal_legacy',normal,'legacy_fixture')]:
 for guard_kind in ['runtime_state','build_capability']:
  condition='not _is_free_threaded()' if guard_kind=='runtime_state' else 'not sysconfig.get_config_var("Py_GIL_DISABLED")'
  source='import sys\nimport sysconfig\nimport pytest\nimport '+module+'\n'+helper+'\n@pytest.mark.skipif('+condition+', reason="Free-threading check")\ndef test_gil_disabled():\n    assert not sys._is_gil_enabled()\n'
  name=context+'_'+guard_kind;file=root/('test_'+name+'.py');file.write_text(source)
  bootstrap='import sys; sys.path[:0]='+repr([str(R/'pytestdeps'),str(R)])+'; import pytest; raise SystemExit(pytest.main('+repr([str(file),'-q','-p','no:cacheprovider','--basetemp',str(root/(name+'_tmp'))])+'))'
  env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
  run=subprocess.run([str(interpreter),'-I','-S','-B','-c',bootstrap],cwd=root,env=env,capture_output=True,text=True,timeout=30)
  expected='failed' if context=='ft_legacy' and guard_kind=='build_capability' else 'skipped' if (context=='normal_legacy' or (context=='ft_legacy' and guard_kind=='runtime_state')) else 'passed'
  ok=('1 '+expected) in run.stdout and run.returncode==(1 if expected=='failed' else 0)
  rows.append({'name':name,'interpreter':str(interpreter),'module':module,'source':source,'expected_pytest_outcome':expected,'matched':ok,'exit':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'static':analyze_guards(source)})
  assert ok,rows[-1]
result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pytest_version':'9.1.1','cases':rows,'summary':{'cases':len(rows),'matched':sum(r['matched'] for r in rows)},'interpretation':'Runtime-state skip can hide the enabled-GIL condition the assertion aims to detect. A build-capability skip preserves regular-CPython skipping while exposing enabled-GIL failure on a free-threaded build. This is a purpose-built pattern reproduction, not execution or a bug report against tokenizers.'}
(P/'results/pytest_guard_matrix.json').write_text(json.dumps(result,indent=2));print(json.dumps(result['summary']))
