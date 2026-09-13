"""Inspect direct Python/pytest commands in a POSIX shell snippet without execution.
Reports process-local evidence; does not infer whole-CI execution or thread safety.
"""
import argparse,ast,json,re,shlex
from pathlib import Path
from gil_evidence import analyze

PYTHON=re.compile(r'(?:.*/)?python(?:\d+(?:\.\d+)*)?t?$')
PYTEST=re.compile(r'(?:.*/)?pytest(?:-\d+(?:\.\d+)*)?$')

def commands(script):
    lexer=shlex.shlex(script,posix=True,punctuation_chars=';&|\n')
    lexer.whitespace=' \t\r';lexer.whitespace_split=True
    # Backslash-newline continuation is a POSIX lexical feature, resolved before tokenization.
    tokens=list(lexer);group=[]
    for t in tokens:
        if t and all(c in ';&|\n' for c in t):
            if group:yield group,t;group=[]
        else:group.append(t)
    if group:yield group,''

def inspect_script(script):
    report={'processes':[],'unknown_commands':[],'notes':[], 'input_executed':False}
    if '$' in script or '`' in script or '<<' in script:
        return {**report,'status':'UNKNOWN','notes':['shell expansion or here-document requires a richer shell model']}
    script=script.replace('\\\n','')
    try:groups=list(commands(script))
    except ValueError as e:return {**report,'status':'UNKNOWN','notes':[str(e)]}
    for tokens,separator in groups:
        original=tokens[:];environment={}
        while tokens and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=',tokens[0]):
            k,v=tokens.pop(0).split('=',1);environment[k]=v
        if not tokens:continue
        executable=tokens.pop(0)
        if not(PYTHON.fullmatch(executable) or PYTEST.fullmatch(executable)):
            report['unknown_commands'].append(original);continue
        p={'process_id':len(report['processes'])+1,'command':original,'environment':environment,'separator':separator,'runtime_gil_state':'NOT_MEASURED','kind':'unknown','checks':[]}
        if separator.strip() not in ('',';','&&'):
            report['notes'].append('conditional/pipeline shell semantics not resolved')
        if PYTEST.fullmatch(executable):p['kind']='test_process'
        else:
            optimized=False;code=None;idx=0
            while idx<len(tokens):
                token=tokens[idx]
                if token in ('-O','-OO'):optimized=True;idx+=1;continue
                if token=='-X' and idx+1<len(tokens):
                    p.setdefault('python_x_options',[]).append(tokens[idx+1]);idx+=2;continue
                if token.startswith('-X') and len(token)>2:
                    p.setdefault('python_x_options',[]).append(token[2:]);idx+=1;continue
                if token in ('-I','-B','-S','-s','-E','-u'):idx+=1;continue
                if token=='-c' and idx+1<len(tokens):code=tokens[idx+1];p['kind']='inline_python';break
                if token=='-m' and idx+1<len(tokens):
                    p['kind']='test_process' if tokens[idx+1]=='pytest' else 'module_process';break
                break
            p['optimized']=optimized
            if code is not None:
                p['source']=code
                try:
                    tree=ast.parse(code);p['gil_query_text_present']='_is_gil_enabled' in code
                    # Only direct, unshadowed top-level pytest.main calls. No claim about imports inside pytest.
                    aliases={}
                    for n in tree.body:
                        if isinstance(n,ast.Import):
                            for a in n.names:
                                aliases.pop(a.asname or a.name.split('.')[0],None)
                                if a.name=='pytest':aliases[a.asname or 'pytest']='pytest'
                        elif isinstance(n,ast.ImportFrom):
                            if any(a.name == '*' for a in n.names):
                                aliases.clear()
                            for a in n.names:aliases.pop(a.asname or a.name,None)
                        else:
                            # Unmodeled compound statements can rebind any imported alias.
                            if not isinstance(n, (ast.Expr, ast.Assert, ast.Pass)):
                                aliases.clear()
                            for node in ast.walk(n):
                                if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                                    aliases.pop(node.id, None)
                        if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call):
                            f=n.value.func
                            if isinstance(f,ast.Attribute) and f.attr=='main' and isinstance(f.value,ast.Name) and aliases.get(f.value.id)=='pytest':
                                p['checks'].append(analyze(code,n.lineno,column=n.col_offset,optimized=optimized))
                                p['kind']='inline_test_process'
                    end=code+'\npass\n'
                    p['end_evidence']=analyze(end,len(end.splitlines()),optimized=optimized)
                except (SyntaxError,ValueError) as e:p['parse_error']=str(e)
        if environment.get('PYTHON_GIL')=='0' or 'gil=0' in p.get('python_x_options',[]):
            p['forced_gil_disabled_requested']=True
            p['force_note']='Configuration request recorded separately from an observed or checked runtime state.'
        report['processes'].append(p)
    earlier=[]
    for p in report['processes']:
        if p['kind']=='test_process':
            p['entry_check']='NOT_ESTABLISHED_FROM_THIS_COMMAND'
            if earlier:
                p['separate_process_checks']=earlier[:]
                p['explanation']='Earlier GIL checks belong to other processes and cannot establish state in this test process. Runner/plugin checks may exist but are not resolved here.'
        if p.get('gil_query_text_present'):earlier.append(p['process_id'])
    report['status']='COMMAND_EVIDENCE_ONLY'
    report['notes'].append('No whole-CI verdict. Interpreter selection, plugin behavior, lazy imports, shell reachability and separate run steps require further context.')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('script',type=Path)
    args=parser.parse_args();print(json.dumps(inspect_script(args.script.read_text()),indent=2))
