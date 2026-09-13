from pathlib import Path
import sys,json,hashlib,subprocess,os,datetime
R=Path(__file__).resolve().parent;P=R.parent.parent;W=P.parent.parent;sys.path.insert(0,str(P));from guard_evidence import analyze_guards
import runpy
frozen_analyzer=P/'validation/frozen/guard_evidence_before_matrix.py'
analyze_guards=runpy.run_path(str(frozen_analyzer))['analyze_guards']
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--ft-python',type=Path,required=True);args=parser.parse_args();ft=args.ft_python.resolve()
root=R/'expanded_guard_cases';root.mkdir(exist_ok=True)
forms=[
 ('direct','sys._is_gil_enabled()',''),
 ('identity_negated','not (sys._is_gil_enabled() is False)',''),
 ('equals_true','sys._is_gil_enabled() == True',''),
 ('getattr_fallback','getattr(sys, "_is_gil_enabled", lambda: True)()',''),
 ('build_not','not sysconfig.get_config_var("Py_GIL_DISABLED")',''),
 ('build_zero','sysconfig.get_config_var("Py_GIL_DISABLED") == 0',''),
 ('never_skip','False',''),
 ('always_skip','True',''),
 ('helper','not is_off()','def is_off():\n    return not sys._is_gil_enabled()\n'),
 ('decorated_helper','is_on()','def identity(f):\n    return f\n@identity\ndef is_on():\n    return sys._is_gil_enabled()\n'),
 ('truthy_and','sys._is_gil_enabled() and sysconfig.get_config_var("Py_GIL_DISABLED")',''),
 ('string_condition',repr('sys._is_gil_enabled()'),'')]
plan=[]
for name,condition,helper in forms:
 for scope in ['function','class','module']:
  prefix='import sys\nimport sysconfig\nimport pytest\nimport {module}\n'+helper+'\n'
  marker='pytest.mark.skipif('+condition+', reason="Fixture state check")'
  body='def test_gil():\n    assert not sys._is_gil_enabled()\n'
  if scope=='function':source=prefix+'@'+marker+'\n'+body
  elif scope=='class':source=prefix+'@'+marker+'\nclass TestGIL:\n    def test_gil(self):\n        assert not sys._is_gil_enabled()\n'
  else:source=prefix+'pytestmark = '+marker+'\n'+body
  plan.append({'id':name+'_'+scope,'form':name,'scope':scope,'source_template':source})
freeze={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'analyzer_sha256':hashlib.sha256(frozen_analyzer.read_bytes()).hexdigest(),'cases':plan,'rule':'Post-freeze expanded fixture validation; no analyzer changes during execution. Not an independently authored or random benchmark. Ground truth: legacy skips and declared passes => state-selective masking. Always-skipped is a distinct outcome, not a selective-mask negative certification.'}
freeze_file=P/'results/expanded_guard_matrix_freeze.json';
if freeze_file.exists():
 prior=json.loads(freeze_file.read_text());assert prior['analyzer_sha256']==freeze['analyzer_sha256'] and prior['cases']==freeze['cases'];freeze=prior
else:freeze_file.write_text(json.dumps(freeze,indent=2))
rows=[]
for spec in plan:
 outcomes={};runs=[]
 for module in ['legacy_fixture','declared_fixture']:
  source=spec['source_template'].replace('{module}',module);file=root/('test_'+spec['id']+'_'+module+'.py');file.write_text(source)
  bootstrap='import sys;sys.path[:0]='+repr([str(R/'pytestdeps'),str(R)])+';import pytest;raise SystemExit(pytest.main('+repr([str(file),'-q','-p','no:cacheprovider'])+'))'
  proc=subprocess.run([str(ft),'-I','-S','-B','-c',bootstrap],cwd=root,env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'),capture_output=True,text=True,timeout=30)
  outcome=next((o for o in ['passed','failed','skipped'] if '1 '+o in proc.stdout),'unresolved')
  outcomes[module]=outcome;runs.append({'module':module,'exit':proc.returncode,'outcome':outcome,'stdout':proc.stdout,'stderr':proc.stderr})
 truth=outcomes=={'legacy_fixture':'skipped','declared_fixture':'passed'}
 static=analyze_guards(spec['source_template'].replace('{module}','legacy_fixture'))
 positive=any(x['status']=='SELF_MASKING_GIL_GUARD_CANDIDATE' for x in static['findings'])
 rows.append({'id':spec['id'],'scope':spec['scope'],'truth_state_selective_mask':truth,'static_candidate':positive,'static':static,'runs':runs,'both_always_skip':all(x=='skipped' for x in outcomes.values())})
 print(spec['id'],truth,positive,flush=True)
assert hashlib.sha256(frozen_analyzer.read_bytes()).hexdigest()==freeze['analyzer_sha256']
summary={'templates':len(rows),'pytest_processes':len(rows)*2,'state_selective_masks':sum(x['truth_state_selective_mask'] for x in rows),'candidates':sum(x['static_candidate'] for x in rows),'correct_candidates':sum(x['truth_state_selective_mask'] and x['static_candidate'] for x in rows),'false_candidates':sum(not x['truth_state_selective_mask'] and x['static_candidate'] for x in rows),'missed_or_unresolved_masks':sum(x['truth_state_selective_mask'] and not x['static_candidate'] for x in rows),'always_skipped_templates':sum(x['both_always_skip'] for x in rows),'unresolved_runtime_cases':sum(y['outcome']=='unresolved' for x in rows for y in x['runs']),'analyzer_unchanged_from_freeze':True}
(P/'results/expanded_guard_matrix.json').write_text(json.dumps({'summary':summary,'rows':rows},indent=2));print(json.dumps(summary,indent=2))
