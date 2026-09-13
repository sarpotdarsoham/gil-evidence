from pathlib import Path
import sys,json,hashlib
P=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(P));from guard_evidence import analyze_guards
f=json.loads((P/'results/expanded_guard_matrix_freeze.json').read_text());original=json.loads((P/'results/expanded_guard_matrix.json').read_text());specs={x['id']:x for x in f['cases']};rows=[]
for old in original['rows']:
 source=specs[old['id']]['source_template'].replace('{module}','legacy_fixture');out=analyze_guards(source)
 positive=any(r['status']=='SELF_MASKING_GIL_GUARD_CANDIDATE' for r in out['findings'])
 rows.append({'id':old['id'],'truth_state_selective_mask':old['truth_state_selective_mask'],'static_candidate':positive,'static':out,'earlier_candidate':old['static_candidate']})
summary={'templates':len(rows),'state_selective_masks':sum(x['truth_state_selective_mask'] for x in rows),'correct_candidates':sum(x['truth_state_selective_mask'] and x['static_candidate'] for x in rows),'false_candidates':sum(not x['truth_state_selective_mask'] and x['static_candidate'] for x in rows),'missed_or_unresolved_masks':sum(x['truth_state_selective_mask'] and not x['static_candidate'] for x in rows),'evaluation_status':'Adaptive regression on the already examined expanded matrix, NOT untouched validation','analyzer_sha256':hashlib.sha256((P/'guard_evidence.py').read_bytes()).hexdigest()}
(P/'results/refined_guard_matrix.json').write_text(json.dumps({'summary':summary,'rows':rows},indent=2));print(json.dumps(summary,indent=2))
