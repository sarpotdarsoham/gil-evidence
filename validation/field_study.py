from pathlib import Path
import concurrent.futures,datetime,hashlib,io,json,sys,tarfile,urllib.request,ast
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));from guard_evidence import analyze_guards
def get(url,cap=60*1024*1024):
 req=urllib.request.Request(url,headers={'User-Agent':'gil-evidence-research','Accept':'application/vnd.github+json'})
 with urllib.request.urlopen(req,timeout=60) as r:
  data=r.read(cap+1)
 if len(data)>cap:raise ValueError('download size bound exceeded')
 return data
def query(n):
 return isinstance(n,ast.Call) and not n.args and not n.keywords and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='sys' and n.func.attr=='_is_gil_enabled'
def direct(tree):
 hits=[]
 def visit(body,inherited=False):
  for n in body:
   if not isinstance(n,(ast.ClassDef,ast.FunctionDef)):continue
   guard=inherited or any(isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and d.func.attr=='skipif' and len(d.args)==1 and query(d.args[0]) for d in n.decorator_list)
   if isinstance(n,ast.ClassDef):visit(n.body,guard)
   elif n.name.startswith('test') and guard and any(isinstance(a,ast.Assert) and isinstance(a.test,ast.UnaryOp) and isinstance(a.test.op,ast.Not) and query(a.test.operand) for a in n.body):hits.append(n.lineno)
 visit(tree.body);return hits
def capture(repo):
 r={'repository':repo,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[],'excluded':[]}
 folder=WORK/repo.replace('/','__');folder.mkdir(exist_ok=True)
 try:
  pin=revisions[repo];sha=pin['commit'];r.update(commit=sha)
  url=pin['archive_url'];r['archive_url']=url
  cached=folder/'source.tar.gz'
  data=cached.read_bytes() if cached.exists() else get(url)
  assert hashlib.sha256(data).hexdigest()==pin['archive_sha256'], 'archive checksum mismatch'
  r['archive_sha256']=pin['archive_sha256']
  if not cached.exists():cached.write_bytes(data)
  with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
   for m in archive:
    path='/'.join(m.name.split('/')[1:]);pp=Path(path)
    if not m.isfile() or pp.suffix!='.py' or not(any('test' in x.lower() for x in pp.parts) or pp.name=='conftest.py'):continue
    if m.size>1024*1024:r['excluded'].append({'path':path,'reason':'over 1MB'});continue
    raw=archive.extractfile(m).read()
    try:source=raw.decode('utf-8')
    except UnicodeDecodeError:r['excluded'].append({'path':path,'reason':'not UTF-8'});continue
    row={'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'query_text':'_is_gil_enabled' in source,'cooccurrence':all(t in source for t in ['_is_gil_enabled','skipif','assert']),'direct_ast':False,'findings':[]}
    try:
     tree=ast.parse(source);row['direct_ast']=bool(direct(tree))
     if 'skipif' in source:row['findings']=[x for x in analyze_guards(source)['findings'] if x['status']=='SELF_MASKING_GIL_GUARD_CANDIDATE']
    except Exception as e:row['error']=type(e).__name__+': '+str(e)
    if row['cooccurrence'] or row['findings']:
     dst=folder/'selected'/path
     # Archive content is data; never extract arbitrary paths or execute it.
     assert '..' not in pp.parts and not pp.is_absolute()
     dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
    r['files'].append(row)
  r['status']='completed'
 except Exception as e:r['status']='unavailable';r['error']=type(e).__name__+': '+str(e)
 r['summary']={k:sum(bool(x.get(k)) for x in r['files']) for k in ['query_text','cooccurrence','direct_ast','findings','error']};r['summary']['eligible_files']=len(r['files'])
 (OUT/(repo.replace('/','__')+'.json')).write_text(json.dumps(r,indent=2)+'\n')
 print(repo,r['status'],r['summary'],flush=True)
 return r
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description='Reproduce the fixed field01 source-only study; never execute target code.')
 parser.add_argument('--cache',type=Path,required=True)
 parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args();WORK=args.cache.resolve();OUT=args.output.resolve();OUT.mkdir(parents=True,exist_ok=True)
 if any(OUT.glob('*__*.json')):raise SystemExit('Choose a fresh output directory to preserve earlier results')
 plan_file=ROOT/'evidence/field01/plan.json'
 plan=json.loads(plan_file.read_text())
 revisions=json.loads((ROOT/'evidence/field01/revisions.json').read_text())
 assert hashlib.sha256((ROOT/'guard_evidence.py').read_bytes()).hexdigest()==plan['analysis_sha256']
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(capture,plan['repositories']))
 totals={k:sum(r['summary'][k] for r in results) for k in results[0]['summary']}
 (OUT/'summary.json').write_text(json.dumps({'plan_sha256':hashlib.sha256(plan_file.read_bytes()).hexdigest(),'analyzer_sha256':plan['analysis_sha256'],'capture_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'repositories_completed':sum(r['status']=='completed' for r in results),'totals':totals},indent=2)+'\n')
 print(totals)
