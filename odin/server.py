"""Odin local application: persistent SQLite state, bounded agents, and static UI."""
import base64
import hashlib
import io
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT=Path(__file__).resolve().parent
for line in (ROOT/'.env').read_text(encoding='utf-8').splitlines() if (ROOT/'.env').exists() else []:
    if '=' in line and not line.lstrip().startswith('#'):
        k,v=line.split('=',1)
        os.environ.setdefault(k.strip(),v.strip().strip('"'))
import agents
import demo
import intelligence

DEFAULTS={'max_calls':18,'max_tokens':60000,'max_seconds':600,'max_iterations':2,'evidence_threshold':0.8}

def configuration(data=None):
    data=data or {}
    config={'model':str(data.get('model') or os.getenv('GEMINI_MODEL','gemini-3.8-flash'))}
    if not re.fullmatch(r'[a-zA-Z0-9.\-]+',config['model']):raise ValueError('Invalid model name.')
    for field,low,high in [('max_calls',6,30),('max_tokens',1000,200000),('max_seconds',30,1200),('max_iterations',0,5)]:
        config[field]=max(low,min(high,int(data.get(field,DEFAULTS[field]))))
    config['evidence_threshold']=max(0,min(1,float(data.get('evidence_threshold',0.8))))
    return config

DB=ROOT/'data'/'odin.db'
LOCK=threading.RLock()
RUN_LOCK=threading.Lock()
DB.parent.mkdir(exist_ok=True)

@contextmanager
def connection():
    db=sqlite3.connect(DB,timeout=10)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, body TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, body TEXT NOT NULL, tokens INTEGER)')
    db.execute('CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS modes (mode TEXT PRIMARY KEY, body TEXT NOT NULL)')
    try:
        with db:
            yield db
    finally:
        db.close()

def load():
    with LOCK, connection() as db:
        row=db.execute('SELECT body FROM state WHERE id=1').fetchone()
        if row:
            state=json.loads(row[0])
            state.setdefault('clock_origin',min([state['as_of']]+[e['date'] for e in state['events']]))
            return state
        state=demo.fixture()
        db.execute('INSERT INTO state VALUES(1,?)',(json.dumps(state),))
        return state

def save(state):
    with LOCK, connection() as db:
        db.execute('INSERT OR REPLACE INTO state VALUES(1,?)',(json.dumps(state),))

def patch(fn):
    with LOCK:
        state=load()
        fn(state)
        save(state)
        return state

def now():
    return datetime.now(timezone.utc).isoformat()

def add_trace(run_id, agent, phase, text, output=None):
    def update(s):
        if not s.get('run') or s['run']['id']!=run_id:
            return
        s['run']['agent']=agent
        s['run']['trace'].append({'agent':agent,'type':phase,'text':text,'time':now(),'output':output})
    patch(update)

def run_agents(run_id, snapshot, config):
    config=configuration(config)
    calls=0
    tokens=0
    start=time.monotonic()
    results={}
    issues=[]
    previous=snapshot.get('run') or {}
    effective_model=('gemini-3.6-flash' if config['model']=='gemini-3.8-flash' and previous.get('effective_model')=='gemini-3.6-flash' and previous.get('status')=='incomplete' else config['model'])
    try:
        def invoke(name, context):
            nonlocal calls,tokens,effective_model
            if calls >= config['max_calls'] or tokens >= config['max_tokens'] or time.monotonic()-start>config['max_seconds']:
                raise agents.AgentError('Analysis budget reached. Partial results are retained; analysis is incomplete.')
            serialized=json.dumps({'prompt_version':5 if name=='Tyr' else 4,'name':name,'model':effective_model,'context':context},sort_keys=True)
            key=hashlib.sha256(serialized.encode()).hexdigest()
            with connection() as db:
                cached=db.execute('SELECT body FROM cache WHERE key=?',(key,)).fetchone()
            if cached:
                add_trace(run_id,name,'Cached','Reused identical input with '+effective_model+'.')
                result=json.loads(cached[0])
            else:
                calls+=1
                add_trace(run_id,name,'Running','Reviewing source evidence with '+effective_model+'.')
                patch(lambda s:s['run'].update({'calls':calls,'effective_model':effective_model}))
                try:
                    result,used=agents.call_agent(name,context,effective_model)
                except agents.AgentError as error:
                    if effective_model!='gemini-3.8-flash' or not any(t in str(error) for t in ('HTTP 503','HTTP 500','HTTP 502','HTTP 504','could not be reached','model is unavailable')):
                        raise
                    if calls>=config['max_calls']:
                        raise agents.AgentError('Call budget reached before fallback. Analysis is incomplete.')
                    effective_model='gemini-3.6-flash'
                    add_trace(run_id,name,'Model fallback','Gemini 3.8 could not complete after retry. Continuing with the user-approved Gemini 3.6 Flash.')
                    patch(lambda s:s['run'].update({'effective_model':effective_model}))
                    serialized=json.dumps({'prompt_version':5 if name=='Tyr' else 4,'name':name,'model':effective_model,'context':context},sort_keys=True)
                    key=hashlib.sha256(serialized.encode()).hexdigest()
                    calls+=1
                    result,used=agents.call_agent(name,context,effective_model)
                tokens+=used
                with connection() as db:
                    db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)',(key,json.dumps(result),used))
            patch(lambda s:s['run'].update({'calls':calls,'tokens':tokens,'effective_model':effective_model}))
            if tokens>config['max_tokens'] or time.monotonic()-start>config['max_seconds']:
                raise agents.AgentError('Analysis budget reached after a response. Cached output is retained; analysis is incomplete.')
            return result

        context={'company':snapshot['company'],'contracts':snapshot['contracts'],'events':snapshot['events'],'as_of':snapshot['as_of']}
        results['Odin']=invoke('Odin',{'company':context['company'],'contracts':[{'id':c['id'],'name':c['name']} for c in context['contracts']]})
        planned={w.get('contract_id') for w in results['Odin']['workstreams'] if isinstance(w,dict)}
        expected={c['id'] for c in context['contracts']}|{'portfolio'}
        if not expected.issubset(planned):issues.append('Odin omitted a required workstream; the application retained all contract and portfolio workstreams.')
        patch(lambda s:s['run'].update(plan=results['Odin']))
        add_trace(run_id,'Odin','Plan',results['Odin']['summary'],results['Odin'])
        facts=[]
        for contract in context['contracts']:
            result=invoke('Thor',{'contract':contract})
            if contract['party']=='Pending extraction':contract['party']=intelligence.infer_party(contract,context['company'])
            accepted=[]
            for fact in result['facts']:
                if isinstance(fact,dict) and fact.get('contract_id')==contract['id'] and agents.validate_evidence(fact,context['contracts']):
                    fact['confidence']=max(0,min(1,float(fact.get('confidence',0))))
                    accepted.append(fact)
                else:
                    issues.append('Thor returned a fact without valid source evidence; it was excluded.')
            facts+=accepted
            if not accepted:
                issues.append(contract['name']+': no source-validated facts were extracted; coverage needs review.')
            required_types={'party','duration','renewal','payment','obligation','penalty','compliance','termination'}
            present={f.get('type') for f in accepted}
            missing=sorted(required_types-present)
            ambiguities=result['ambiguities']+[f'{field}: not explicitly established by extraction; no value inferred.' for field in missing]
            results.setdefault('Thor',[]).append({'contract_id':contract['id'],'facts':accepted,'ambiguities':ambiguities,'coverage':{'present':sorted(present),'missing':missing}})
            add_trace(run_id,'Thor','Evidence',f'{contract["name"]}: {len(accepted)} source-validated facts.',results['Thor'][-1])
            patch(lambda s,cid=contract['id']:s['run']['workstreams'].update({cid:'extracted'}))
        results['Norns']=invoke('Norns',dict(context,facts=facts))
        valid_obligations=[]
        for obligation in results['Norns']['obligations']:
            if not isinstance(obligation,dict) or not agents.validate_evidence(obligation,context['contracts']):
                issues.append('A temporal obligation lacked valid evidence and was excluded.')
                continue
            if obligation.get('due_date'):
                try:
                    date.fromisoformat(obligation['due_date'])
                except ValueError:
                    obligation['due_date']=''
                    issues.append('An invalid obligation date was withheld.')
            valid_obligations.append(obligation)
        results['Norns']['obligations']=valid_obligations
        add_trace(run_id,'Norns','Timeline',f'{len(valid_obligations)} cited obligations; dates remain subject to source interpretation.',results['Norns'])
        results['Loki']=invoke('Loki',dict(context,facts=facts))
        seen=set();rounds=0
        low_confidence=[{'contract_id':f['contract_id'],'clause_id':f['clause_id'],'question':'Recheck source interpretation: extraction confidence is below the configured evidence threshold.'} for f in facts if f['confidence']<config['evidence_threshold']]
        requests=results['Loki']['clarifications']+low_confidence
        while requests and rounds<config['max_iterations']:
            targets=[]
            for req in requests:
                if not isinstance(req,dict): continue
                target_key=(req.get('contract_id'),req.get('clause_id'))
                if target_key in seen:continue
                if len(targets)>=2:break
                for c in context['contracts']:
                    if c['id']==req.get('contract_id'):
                        targets += [{'contract_id':c['id'],'clause':cl,'question':req.get('question')} for cl in c['clauses'] if cl['id']==req.get('clause_id')]
                if targets:seen.add(target_key)
            if targets:
                rounds+=1
                patch(lambda s:s['run'].update(iterations=rounds))
                add_trace(run_id,'Loki','Clarification',f'Targeted re-extraction round {rounds} of {config["max_iterations"]}.',targets)
                result=invoke('Thor',{'clarify':targets})
                target_ids={(t['contract_id'],t['clause']['id']) for t in targets}
                extra=[f for f in result['facts'] if isinstance(f,dict) and (f.get('contract_id'),f.get('clause_id')) in target_ids and agents.validate_evidence(f,context['contracts'])]
                for f in extra:f['confidence']=max(0,min(1,float(f.get('confidence',0))))
                if len(extra)!=len(result['facts']):issues.append('A clarification fact lacked valid evidence and was excluded.')
                replacements={f['clause_id'] for f in extra}
                facts=[f for f in facts if f['clause_id'] not in replacements]+extra
                for extracted in results['Thor']:
                    extracted['facts']=[f for f in facts if f['contract_id']==extracted['contract_id']]
                results.setdefault('ClarificationHistory',[]).append({'round':rounds,'targets':targets,'facts':extra,'ambiguities':result['ambiguities']})
                results['Clarification']={'facts':extra,'ambiguities':result['ambiguities']}
                add_trace(run_id,'Thor','Clarification',f'Returned {len(extra)} validated facts for the requested clauses.',results['Clarification'])
                results['Loki']=invoke('Loki',dict(context,facts=facts,clarification=results['Clarification'],round=rounds))
                requests=results['Loki']['clarifications']+[{'contract_id':f['contract_id'],'clause_id':f['clause_id'],'question':'Recheck remaining low-confidence source interpretation.'} for f in facts if f['confidence']<config['evidence_threshold'] and (f['contract_id'],f['clause_id']) not in seen]
            else:
                issues.append('Clarification requests could not be resolved with new source clauses.');break
        if requests and rounds>=config['max_iterations']:issues.append('Clarification iteration limit reached; unresolved questions require review.')
        if any(f['confidence']<config['evidence_threshold'] for f in facts):issues.append('Some extractions remain below the configured evidence threshold.')
        findings=[]
        for i,f in enumerate(results['Loki']['findings']):
            if isinstance(f,dict) and f.get('evidence') and all(isinstance(e,dict) and agents.validate_evidence(e,context['contracts']) for e in f['evidence']):
                f['id']='finding-'+str(i+1)
                f['severity']=f.get('severity') if f.get('severity') in ('high','medium','low') else 'medium'
                findings.append(f)
            else:
                issues.append('An unsupported Loki finding was excluded.')
        results['Loki']['findings']=findings
        add_trace(run_id,'Loki','Challenge',f'{len(findings)} findings passed exact-source validation.',results['Loki'])
        results['Heimdall']=invoke('Heimdall',dict(context,facts=facts,findings=findings))
        results['Heimdall']['verifications']=[v for v in results['Heimdall']['verifications'] if isinstance(v,dict) and v.get('finding_id') in {f['id'] for f in findings} and v.get('verdict') in ('supported','qualified','rejected')]
        valid_clauses={cl['id'] for c in context['contracts'] for cl in c['clauses']}
        event_ids={e['id'] for e in context['events']}
        mappings=results['Heimdall'].get('event_mappings',[])
        results['Heimdall']['event_mappings']=[m for m in mappings if isinstance(m,dict) and m.get('event_id') in event_ids and m.get('clause_ids') and all(cid in valid_clauses for cid in m['clause_ids'])]
        if len(mappings)!=len(results['Heimdall']['event_mappings']):issues.append('An event mapping with invalid references was excluded.')
        add_trace(run_id,'Heimdall','Verification',f'{len(results["Heimdall"]["verifications"])} claims reviewed against clauses and events.',results['Heimdall'])
        results['Tyr']=invoke('Tyr',dict(context,findings=findings,verification=results['Heimdall'],clarification=results.get('Clarification',{})))
        ids={f['id'] for f in findings}
        results['Tyr']['rulings']=[r for r in results['Tyr']['rulings'] if isinstance(r,dict) and r.get('finding_id') in ids and r.get('verdict') in ('supported','qualified','rejected','unresolved')]
        verified_ids={v['finding_id'] for v in results['Heimdall']['verifications']}
        ruled_ids={r['finding_id'] for r in results['Tyr']['rulings']}
        for f in findings:
            if f['id'] not in verified_ids or f['id'] not in ruled_ids:
                issues.append('Finding '+f['id']+' lacks a complete review and arbitration.')
        clause_ids={cl['id'] for c in context['contracts'] for cl in c['clauses']}
        actions=[]
        for a in results['Tyr']['actions']:
            if not isinstance(a,dict) or a.get('finding_id') not in ids or not a.get('clause_ids') or not all(c in clause_ids for c in a['clause_ids']):
                issues.append('An action lacked valid references and was excluded.')
                continue
            if a.get('due_date'):
                try: date.fromisoformat(a['due_date'])
                except ValueError: a['due_date']=''
            ruling=next((r for r in results['Tyr']['rulings'] if r['finding_id']==a['finding_id']),{})
            a.update(id=uuid.uuid4().hex[:12],status='needs_approval',confidence=max(0,min(1,float(ruling.get('confidence',0)))),confidence_basis='Associated Tyr arbitration; uncalibrated model assessment')
            if a['confidence']<config['evidence_threshold']:issues.append('An action has low arbitration confidence and needs human review.')
            if len(a.get('draft','').split())<80 or 'subject:' not in a.get('draft','').lower():issues.append('A drafted action needs editing before sending; it is retained for human review.')
            actions.append(a)
        add_trace(run_id,'Tyr','Ruling',results['Tyr']['summary'],results['Tyr'])
        actions.sort(key=lambda a:a.get('due_date') or '9999')
        def finish(s):
            s['live_results']=results
            s.update(results_are_stale=False,analysis_as_of=snapshot['as_of'],analysis_run_id=run_id,partial_results=None)
            for c in s['contracts']:
                updated=next((x for x in context['contracts'] if x['id']==c['id']),None)
                if updated:c['party']=updated['party']
            s['actions']=actions
            s['run'].update(status='needs_review' if issues else 'complete',issues=issues,finished=now(),calls=calls,tokens=tokens)
            s['run']['workstreams']={k:('needs_review' if issues else 'complete') for k in s['run']['workstreams']}
        patch(finish)
    except Exception as e:
        message=str(e) if isinstance(e,agents.AgentError) else 'Agent output could not be validated. Partial results are retained; retry the analysis.'
        def fail(s):
            s['partial_results']=results
            if (s.get('live_results') or {}).get('Tyr'):
                s['results_are_stale']=True
            else:s['live_results']=results
            s['run'].update(status='incomplete',error=message,issues=issues,finished=now(),calls=calls,tokens=tokens)
        patch(fail)
        if 'quota' in message.lower() or 'billing' in message.lower():
            patch(lambda s:s.setdefault('monitor',{}).update(pending=False,blocked_until=time.time()+900,last_error=message))
        add_trace(run_id,'Odin','Incomplete',message)
    finally:
        current=load()
        with connection() as db:
            db.execute('INSERT OR REPLACE INTO history VALUES(?,?)',(run_id,json.dumps({'run':current.get('run'),'results':results})))
        RUN_LOCK.release()

def split_clauses(pages,cid):
    clauses=[]
    for page_no,text in enumerate(pages,1):
        chunks=re.split(r'(?m)(?=^\s*\d+(?:\.\d+)+[\s.:])',text)
        for chunk in chunks:
            chunk=chunk.strip()
            if not chunk: continue
            match=re.match(r'^(\d+(?:\.\d+)+)',chunk)
            num=match.group(1) if match else f'p{page_no}-{len(clauses)+1}'
            # Bound oversized unstructured blocks without losing original exact text.
            for offset in range(0,len(chunk),5000):
                clauses.append({'id':f'{cid}-{len(clauses)+1}','number':num,'page':page_no,'text':chunk[offset:offset+5000]})
    return clauses

def state_view():
    s=load()
    s['config']={'key_configured':bool(os.getenv('GEMINI_API_KEY')),'model':os.getenv('GEMINI_MODEL','gemini-3.8-flash'),'fallback_model':'gemini-3.6-flash'}
    s['scenario']=demo.scenario(s) if s['mode']=='demo' else None
    s['settings']=configuration(s.get('settings'))
    s.setdefault('monitor',{'enabled':False,'pending':False})
    s['insights']=intelligence.build(s)
    rulings={r['finding_id']:r for r in (s.get('live_results') or {}).get('Tyr',{}).get('rulings',[])}
    for a in s['actions']:
        a.setdefault('confidence',rulings.get(a.get('finding_id'),{}).get('confidence',1 if s['mode']=='demo' else None))
    return s

def invalidate(s):
    if s.get('run'):
        s['run']['status']='stale'
        s['run']['error']='Inputs changed. Run analysis to refresh the findings.'

def queue_monitor(s):
    monitor=s.setdefault('monitor',{'enabled':False})
    if s['mode']=='live' and monitor.get('enabled',False):monitor.update(pending=True,queued_at=time.time())

def start_analysis(data=None,source='manual'):
    with LOCK:
        s=load()
        if s['mode']!='live':raise ValueError('Switch to Live analysis to run Gemini agents.')
        if not s['contracts']:raise ValueError('Add at least one contract.')
        if not os.getenv('GEMINI_API_KEY'):raise ValueError('Configure GEMINI_API_KEY in .env first.')
        config=configuration(data or s.get('settings'))
        if not RUN_LOCK.acquire(blocking=False):raise ValueError('Analysis already running.')
        run_id=uuid.uuid4().hex
        run={'id':run_id,'status':'running','agent':'Odin','trace':[],'started':now(),'calls':0,'tokens':0,'config':config,'source':source,'iterations':0,'workstreams':{**{c['id']:'queued' for c in s['contracts']},'portfolio':'queued'}}
        patch(lambda st:(st.update(run=run),st.setdefault('monitor',{}).update(pending=False)))
        threading.Thread(target=run_agents,args=(run_id,s,config),daemon=True).start()
        return run_id

def monitor_tick():
    s=load();m=s.get('monitor',{})
    if s['mode']=='live' and m.get('enabled',False) and m.get('pending') and time.time()-m.get('queued_at',0)>=2 and time.time()>=m.get('blocked_until',0) and not RUN_LOCK.locked():
        try:start_analysis(source='event_monitor')
        except ValueError as error:patch(lambda st:st.setdefault('monitor',{}).update(pending=False,last_error=str(error)))

def monitor_loop():
    while True:
        try:monitor_tick()
        except Exception:pass
        time.sleep(2)

def report(s):
    return intelligence.company_report(s)


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,data,status=200,ctype='application/json'):
        body=(json.dumps(data,ensure_ascii=False) if ctype=='application/json' else data).encode() if not isinstance(data,bytes) else data
        self.send_response(status)
        self.send_header('Content-Type',ctype+'; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/state': return self.reply(state_view())
        if path=='/api/report':
            state=load();cid=parse_qs(urlparse(self.path).query).get('contract_id',[None])[0]
            if cid and cid not in {c['id'] for c in state['contracts']}:return self.reply({'error':'Unknown contract.'},404)
            return self.reply(intelligence.contract_report(state,cid) if cid else intelligence.company_report(state),ctype='text/markdown')
        if path=='/api/events':return self.reply({'events':load()['events']})
        if path=='/api/history':
            rid=parse_qs(urlparse(self.path).query).get('id',[None])[0]
            with connection() as db:
                if rid:
                    row=db.execute('SELECT body FROM history WHERE id=?',(rid,)).fetchone()
                    return self.reply(json.loads(row[0])) if row else self.reply({'error':'Unknown run.'},404)
                rows=db.execute('SELECT id,body FROM history ORDER BY rowid DESC LIMIT 12').fetchall()
            return self.reply({'runs':[{'id':rid,'status':json.loads(body)['run'].get('status'),'started':json.loads(body)['run'].get('started'),'model':json.loads(body)['run'].get('effective_model')} for rid,body in rows]})
        if path=='/api/health': return self.reply({'ok':True})
        assets={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css','/editorial.css':'editorial.css','/workspace.js':'workspace.js','/workspace.css':'workspace.css'}
        if path not in assets: return self.reply({'error':'Not found'},404)
        target=ROOT/'static'/assets[path]
        ctype={'.html':'text/html','.js':'application/javascript','.css':'text/css'}[target.suffix]
        self.reply(target.read_bytes(),ctype=ctype)
    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if origin and urlparse(origin).netloc != self.headers.get('Host'):
                return self.reply({'error':'Cross-origin requests are not permitted.'},403)
            length=int(self.headers.get('Content-Length','0'))
            if length>12_000_000: return self.reply({'error':'Upload limit is 8 MB.'},413)
            data=json.loads(self.rfile.read(length) or b'{}')
            path=urlparse(self.path).path
            if path=='/api/connection':
                return self.reply(agents.check_connection())
            if RUN_LOCK.locked() and path not in ('/api/connection',):
                return self.reply({'error':'An analysis is running. Wait for completion before changing inputs.'},409)
            if path=='/api/settings':
                config=configuration(data)
                patch(lambda s:s.update(settings=config))
                return self.reply(state_view())
            if path=='/api/monitor':
                if not isinstance(data.get('enabled'),bool):raise ValueError('enabled must be true or false.')
                patch(lambda s:s.setdefault('monitor',{}).update(enabled=data['enabled'],pending=False))
                return self.reply(state_view())
            if path=='/api/reset':
                save(demo.fixture())
                return self.reply(state_view())
            if path=='/api/mode':
                mode=data.get('mode')
                if mode not in ('demo','live'): raise ValueError('Unknown mode.')
                with LOCK:
                    current=load()
                    if current['mode'] != mode:
                        with connection() as db:
                            db.execute('INSERT OR REPLACE INTO modes VALUES(?,?)',(current['mode'],json.dumps(current)))
                            old=db.execute('SELECT body FROM modes WHERE mode=?',(mode,)).fetchone()
                        if old:
                            next_state=json.loads(old[0])
                        elif mode=='demo':
                            next_state=demo.fixture()
                        else:
                            next_state=dict(current,mode='live',run=None,live_results=None,actions=[])
                        save(next_state)
                return self.reply(state_view())
            if path=='/api/clock':
                value=date.fromisoformat(data['date']).isoformat()
                clock=intelligence.instant(data.get('timestamp'))
                if clock and clock.date().isoformat()!=value:raise ValueError('Clock date and UTC timestamp must agree.')
                def move_clock(s):
                    origin=s.get('clock_origin',s['as_of'])
                    if not 0<=(date.fromisoformat(value)-date.fromisoformat(origin)).days<=60:origin=value
                    s.update(as_of=value,as_of_time=clock.isoformat() if clock else None,clock_origin=origin)
                    invalidate(s);queue_monitor(s)
                patch(move_clock)
                return self.reply(state_view())
            if path=='/api/company':
                name=str(data.get('name','')).strip()[:100]
                if not name: raise ValueError('Company name is required.')
                patch(lambda s:(s.update(company=name),invalidate(s),queue_monitor(s)))
                return self.reply(state_view())
            if path=='/api/event':
                kind=data.get('type','outage')
                if kind not in ('outage','payment','notice','incident'): raise ValueError('Unsupported event type.')
                event={'id':str(data.get('id') or uuid.uuid4().hex[:12])[:100],'type':kind,'date':date.fromisoformat(data.get('date',load()['as_of'])).isoformat(),'title':str(data.get('title') or 'Production outage')[:150],'classification':data.get('classification','unknown'),'duration_minutes':int(data.get('duration_minutes',95)),'description':str(data.get('description',''))[:2000]}
                state=load();valid_contracts={c['id'] for c in state['contracts']};valid_clauses={cl['id']:c['id'] for c in state['contracts'] for cl in c['clauses']}
                for field in ('timestamp','detected_at','confirmed_at'):
                    if data.get(field):event[field]=intelligence.instant(data[field]).isoformat()
                if event.get('timestamp') and event['timestamp'][:10]!=event['date']:raise ValueError('Event date and UTC timestamp must agree.')
                for field in ('contract_id','clause_id'):
                    if data.get(field):event[field]=str(data[field])
                if event.get('contract_id') and event['contract_id'] not in valid_contracts:raise ValueError('Unknown affected contract.')
                if event.get('clause_id') and valid_clauses.get(event['clause_id'])!=event.get('contract_id'):raise ValueError('The clause must belong to the selected affected contract.')
                event['affected_contract_ids']=list(dict.fromkeys(data.get('affected_contract_ids',[])))
                if any(cid not in valid_contracts for cid in event['affected_contract_ids']):raise ValueError('Unknown linked contract.')
                event['status']=data.get('status','reported')
                if event['status'] not in ('reported','received'):raise ValueError('Event status must be reported or received.')
                event['evidence_verified']=data.get('evidence_verified') is True
                if data.get('related_event_id'):
                    if data['related_event_id'] not in {e['id'] for e in state['events']}:raise ValueError('Unknown related incident event.')
                    event['related_event_id']=data['related_event_id']
                event['unauthorized_access_confirmed']=data.get('unauthorized_access_confirmed') is True
                event['advance_notice_hours']=max(0,min(100000,float(data.get('advance_notice_hours',0))))
                if event['classification'] not in ('unplanned','scheduled','unknown') or not 0<=event['duration_minutes']<=100000: raise ValueError('Invalid outage classification or duration.')
                def event_update(s):
                    if any(e['id']==event['id'] for e in s['events']): return
                    if s['mode']=='demo' and kind=='outage' and any(e['type']=='outage' for e in s['events']): raise ValueError('The synthetic demo models one outage. Reset demo to try a different incident; live mode accepts multiple events.')
                    s['events'].append(event)
                    if s['mode']=='demo' and kind=='outage': s['actions'].insert(0,demo.claim_action(event))
                    invalidate(s)
                    queue_monitor(s)
                patch(event_update)
                return self.reply(state_view())
            if path=='/api/upload':
                if load()['mode']=='demo': raise ValueError('Switch to Live analysis before adding contracts.')
                name=Path(str(data.get('name','Contract.txt'))).name[:150]
                raw=base64.b64decode(data['content'],validate=True)
                if len(raw)>8_000_000: raise ValueError('Maximum file size is 8 MB.')
                if name.lower().endswith('.pdf'):
                    from pypdf import PdfReader
                    reader=PdfReader(io.BytesIO(raw))
                    if len(reader.pages)>60: raise ValueError('Maximum 60 pages per contract for this prototype.')
                    pages=[p.extract_text() or '' for p in reader.pages]
                elif name.lower().endswith(('.txt','.md')): pages=[raw.decode('utf-8-sig')]
                else: raise ValueError('Use a PDF, TXT or Markdown file.')
                if sum(len(p.strip()) for p in pages)<40: raise ValueError('No readable contract text found. Scanned PDFs need OCR; paste or upload a text version.')
                if sum(len(p) for p in pages)>100000: raise ValueError('Contract text exceeds the prototype limit of 100,000 characters.')
                digest=hashlib.sha256(raw).hexdigest()
                cid=digest[:12]
                def upload(s):
                    if any(c['id']==cid for c in s['contracts']): return
                    if len(s['contracts'])>=12: raise ValueError('This prototype supports up to 12 contracts per portfolio.')
                    s['contracts'].append({'id':cid,'name':name.rsplit('.',1)[0],'party':'Pending extraction','category':'Uploaded','synthetic':False,'version':digest,'clauses':split_clauses(pages,cid),'status':'ready'})
                    invalidate(s)
                    queue_monitor(s)
                patch(upload)
                return self.reply(state_view())
            if path=='/api/remove-contract':
                if load()['mode']=='demo': raise ValueError('Sample contracts are fixed in demo mode.')
                patch(lambda s:(s.update(contracts=[c for c in s['contracts'] if c['id']!=data['id']]),invalidate(s),queue_monitor(s)))
                return self.reply(state_view())
            if path=='/api/action':
                status=data.get('status')
                if status not in ('approved','needs_approval'): raise ValueError('Invalid action status.')
                def approve(s):
                    for a in s['actions']:
                        if a['id']==data['id']:
                            a['status']=status
                            a['reviewed_at']=now()
                patch(approve)
                return self.reply(state_view())
            if path=='/api/analyze':
                run_id=start_analysis(data or None)
                return self.reply({'ok':True,'run_id':run_id})
            return self.reply({'error':'Not found'},404)
        except agents.AgentError as e:
            self.reply({'error':str(e)},400)
        except (ValueError,KeyError,TypeError) as e:
            self.reply({'error':str(e) if isinstance(e,ValueError) else 'Invalid request fields.'},400)
        except Exception:
            self.reply({'error':'The request could not be processed. Check the file format and try again.'},500)

if __name__=='__main__':
    state=load()
    if state.get('run',{}) and state['run']['status']=='running':
        state['run'].update(status='incomplete',error='Application restarted during analysis. Retry to reuse cached completed calls.')
        save(state)
    port=int(os.getenv('ODIN_PORT','8765'))
    print(f'Odin is ready at http://127.0.0.1:{port}',flush=True)
    threading.Thread(target=monitor_loop,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
