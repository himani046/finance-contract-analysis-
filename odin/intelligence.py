"""Source-grounded rules, temporal ledger, graph, alerts, and report synthesis.

The rule compiler accepts explicit fixed amounts, calendar deadlines and daily
penalties. Unsupported monetary language remains visible as unquantified coverage.
It never evaluates code supplied by a document or a model.
"""
import calendar
import hashlib
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

UTC = timezone.utc
WORDS = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'seventh':7,'eight':8,'nine':9,'ten':10,'fourteen':14,'thirty':30,'sixty':60}
MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
DATE = r'(\d{1,2})\s+('+'|'.join(MONTHS)+r')\s+(20\d{2})'
MONEY = re.compile(r'\b(INR|USD|EUR|GBP|AUD|CAD)\s*([\d,]+(?:\.\d{1,2})?)\b', re.I)

def number(value):
    return int(value) if value.isdigit() else WORDS.get(value.lower())

def dates(text):
    out=[]
    for m in re.finditer(DATE, text, re.I):
        try: out.append((date(int(m[3]), MONTHS[m[2].lower()], int(m[1])), m.start(), m.end()))
        except ValueError: pass
    for m in re.finditer(r'\b20\d{2}-\d{2}-\d{2}\b',text):
        try: out.append((date.fromisoformat(m[0]),m.start(),m.end()))
        except ValueError: pass
    return sorted(out,key=lambda x:x[1])

def instant(value):
    if not value: return None
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None: raise ValueError('A timestamp must include its UTC offset.')
    return parsed.astimezone(UTC)

def as_of(state):
    return instant(state.get('as_of_time')) or datetime.combine(date.fromisoformat(state['as_of']),time(23,59,59),UTC)

def clause_type(text):
    t=text.lower()
    for kind,words in [('renewal',('renew','non-renew','cancellation')),('penalty',('penalty','per day','per calendar day')),('payment',('payment','invoice','credit','pay ')),('compliance',('personal data','unauthorized','audit')),('termination',('termination','terminate')),('notification',('notify','notification','incident report'))]:
        if any(w in t for w in words): return kind
    return 'obligation'

def source(c,cl):
    return {'contract_id':c['id'],'clause_id':cl['id'],'quote':cl['text'],'clause_number':cl['number'],'page':cl['page']}

def infer_party(contract,company):
    for clause in contract['clauses']:
        text=clause['text']
        match=re.search(r'between\s+(.+?)\s+and\s+(.+?)(?:[,.;]|\s+effective|\s+from|$)',text,re.I)
        if match:
            parties=[p.strip(' "\'') for p in match.groups()]
            others=[p for p in parties if company.lower() not in p.lower()]
            if len(others)==1:return others[0][:100]
    return contract['party']

def compile_rules(state):
    rules=[];unsupported=[]
    for c in state['contracts']:
        all_text=' '.join(cl['text'] for cl in c['clauses'])
        thresholds={int(m[1]) for m in re.finditer(r'more than\s+(\d+)\s+(?:consecutive\s+)?minutes',all_text,re.I)}
        threshold=next(iter(thresholds)) if len(thresholds)==1 else None
        for cl in c['clauses']:
            text=cl['text'];lower=text.lower();amounts=list(MONEY.finditer(text));ds=dates(text)
            base={**source(c,cl),'confidence':1.0,'origin':'explicit_source_rule','type':clause_type(text),'evidence':[source(c,cl)]}
            recognized=False
            if amounts and state['company'].lower() not in all_text.lower() and not re.search(r'\b(?:the company|company must|company shall)\b',all_text,re.I):
                unsupported.append(dict(base,reason='The company context is not established as a party/obligor in these clauses. No amount is attributed to it.'))
                continue
            distinct={(m[1].upper(),m[2].replace(',','')) for m in amounts}
            complex_formula=bool(re.search(r'%|percent|whichever|greater of|lower of|up to|subject to negotiation|multiplied|tiered|\bplus\b|\bminus\b',lower)) or len({m[1].upper() for m in amounts})>1 or (len(distinct)>1 and 'cap' not in lower)
            if (amounts or re.search(r'\b(?:INR|USD|EUR|GBP|AUD|CAD)\s*\d|[₹$€£]\s*\d',text,re.I)) and complex_formula:
                unsupported.append(dict(base,reason='A variable, percentage, tier, or negotiated condition prevents a safe fixed-amount calculation. It is excluded from totals.'))
                continue
            if amounts and ('service credit' in lower) and ('qualifying incident' in lower or 'outage' in lower) and not ('sole monetary remedy' in lower):
                recovery=bool(re.search(r'eligible for|entitled to|may claim',lower))
                direction='recovery' if recovery else 'liability' if re.search(r'requires .*? to issue|shall (?:issue|pay)|must (?:issue|pay)',lower) else None
                if direction and threshold is not None:
                    match=re.search(r'(?:on the\s+|within\s+)(\w+)\s+calendar day(?:s)?\s+(?:after|of)',lower)
                    claim_days=number(match[1]) if match else None
                    currency=amounts[0][1].upper();amount=Decimal(amounts[0][2].replace(',',''))
                    for related in c['clauses']:
                        cap=re.search(r'(?:capped at|cap of)\s+(INR|USD|EUR|GBP|AUD|CAD)\s*([\d,]+(?:\.\d{1,2})?)\s+per incident',related['text'],re.I)
                        if cap and cap[1].upper()==currency:amount=min(amount,Decimal(cap[2].replace(',','')))
                        if related['id']!=cl['id'] and (cap or re.search(r'more than\s+\d+\s+(?:consecutive\s+)?minutes',related['text'],re.I)):base['evidence'].append(source(c,related))
                    rules.append(dict(base,id='credit:'+cl['id'],kind='incident_credit',direction=direction,currency=currency,amount=float(amount),threshold_minutes=threshold,deadline_days=claim_days,requires_claim=recovery and 'claim' in lower,requires_report='incident report' in lower,requires_notice='48 hours' in all_text.lower(),non_cash='credit' in lower))
                    recognized=True
            if amounts and re.search(r'renews? automatically|automatically renews?',lower) and len(ds)>=2:
                renewal=ds[0][0];deadline=ds[-1][0]
                rules.append(dict(base,id='renewal:'+cl['id'],kind='renewal',direction='commitment',currency=amounts[0][1].upper(),amount=float(Decimal(amounts[0][2].replace(',',''))),renewal_date=renewal.isoformat(),deadline=deadline.isoformat()))
                recognized=True
            if amounts and ds and re.search(r'(?:per|each) (?:calendar )?day',lower) and re.search(r'late|overdue|delay',lower):
                due=ds[0][0].isoformat() if ds else None
                rules.append(dict(base,id='penalty:'+cl['id'],kind='daily_penalty',direction='liability',currency=amounts[0][1].upper(),amount=float(Decimal(amounts[0][2].replace(',',''))),due_date=due,cap=float(Decimal(amounts[1][2].replace(',',''))) if len(amounts)>1 and 'cap' in lower else None))
                recognized=True
            elif amounts and ds and re.search(r'(?:shall|must) pay|payment (?:of .*? )?(?:is )?due|invoice .*?due',lower) and not recognized:
                rules.append(dict(base,id='payment:'+cl['id'],kind='fixed_payment',direction='liability',currency=amounts[0][1].upper(),amount=float(Decimal(amounts[0][2].replace(',',''))),due_date=ds[-1][0].isoformat()))
                recognized=True
            # Clauses repeating a cap or current-term fee are not additional exposure.
            duplicate_context=bool(re.search(r'sole monetary remedy|capped at|current term|per annual term',lower))
            if (amounts or re.search(r'\b(?:INR|USD|EUR|GBP|AUD|CAD)\s*\d|[₹$€£]\s*\d',text,re.I)) and not recognized and not duplicate_context:
                unsupported.append(dict(base,reason='The amount is explicit, but its trigger or formula is not supported by the deterministic compiler. It is excluded from totals.'))
    return rules,unsupported

def matching_event(event,contract_id,clause_id):
    return event.get('contract_id')==contract_id and event.get('clause_id')==clause_id

def completed(events,rule,purpose,deadline=None,event_id=None):
    for event in events:
        if event.get('type')!=purpose or not matching_event(event,rule['contract_id'],rule['clause_id']): continue
        if event.get('status')!='received': continue
        if event_id and event.get('related_event_id')!=event_id:continue
        received=instant(event.get('timestamp')) or datetime.combine(date.fromisoformat(event['date']),time(23,59),UTC)
        if not deadline or received<=deadline: return event
    return None

def evaluate(state,at=None,compiled=None,include_obligations=True):
    now=at or as_of(state);rules,unsupported=compiled or compile_rules(state)
    events=[e for e in state['events'] if (instant(e.get('timestamp')) or datetime.combine(date.fromisoformat(e['date']),time.min,UTC))<=now]
    entries=[];obligations=[]
    def obligation(rule,title,due,event=None,status=None,reason='Explicit source rule'):
        if not include_obligations:return
        obligations.append({**{k:rule[k] for k in ('contract_id','clause_id','quote','confidence','type')},'id':rule['id']+(':'+event['id'] if event else ''),'title':title,'date':due.date().isoformat() if due else None,'due_date':due.date().isoformat() if due else '', 'due_at':due.isoformat() if due else None,'date_basis':reason,'status':status or ('overdue' if due and due<now else 'due_today' if due and due.date()==now.date() else 'upcoming' if due else 'unresolved'),'days':(due.date()-now.date()).days if due else None,'event_id':event['id'] if event else None})
    def entry(rule,amount,status,event=None,detail=''):
        entries.append({**rule,'amount':amount,'status':status,'event_id':event['id'] if event else None,'detail':detail})
    for rule in rules:
        if rule['kind']=='incident_credit':
            for event in events:
                if event['type']!='outage': continue
                if event.get('contract_id') and event['contract_id']!=rule['contract_id']:
                    # A supplied dependency list explicitly expands an event to other contracts.
                    if rule['contract_id'] not in event.get('affected_contract_ids',[]): continue
                duration=event.get('duration_minutes',0)
                if rule['threshold_minutes'] is None:
                    entry(rule,0,'unquantified',event,'The qualifying duration is not explicit.');continue
                if duration<=rule['threshold_minutes']: continue
                classification=event.get('classification','unknown')
                excluded=classification=='scheduled' and event.get('advance_notice_hours',0)>=48
                if excluded: continue
                conditional=classification!='unplanned'
                due=datetime.combine(date.fromisoformat(event['date'])+timedelta(days=rule['deadline_days']),time(23,59,59),UTC) if rule['deadline_days'] is not None else None
                received=completed(events,rule,'notice',due,event['id']) if rule['requires_claim'] else None
                eligible_claim=bool(received and (not rule['requires_report'] or received.get('evidence_verified')))
                expired=rule['requires_claim'] and due and now>due and not eligible_claim
                paid=completed(events,rule,'payment',event_id=event['id']) if rule['direction']=='liability' else None
                value=0 if expired or paid else rule['amount']
                status='fulfilled' if paid else 'expired' if expired else 'conditional' if conditional or rule['requires_claim'] and not eligible_claim else 'supported'
                entry(rule,value,status,event,'Invoice credit; conditional on qualification and timely documented receipt.' if rule['direction']=='recovery' else 'Fixed event-triggered customer credit; not necessarily a cash payment.')
                obligation(rule,'Submit credit claim' if rule['direction']=='recovery' else 'Issue customer credit',due,event,'fulfilled' if eligible_claim or paid else 'expired' if expired else None)
        elif rule['kind']=='renewal':
            deadline=datetime.combine(date.fromisoformat(rule['deadline']),time(23,59,59),UTC)
            notice=completed(events,rule,'notice',deadline)
            entry(rule,0 if notice else rule['amount'],'avoided' if notice else 'locked' if now>deadline else 'avoidable',detail='Annual renewal commitment, separate from incident exposure.')
            obligation(rule,'Non-renewal notice deadline',deadline,status='fulfilled' if notice else None)
        elif rule['kind'] in ('fixed_payment','daily_penalty'):
            due=datetime.combine(date.fromisoformat(rule['due_date']),time(23,59,59),UTC) if rule.get('due_date') else None
            paid=completed(events,rule,'payment')
            if rule['kind']=='daily_penalty':
                end=instant(paid.get('timestamp')) if paid and paid.get('timestamp') else datetime.combine(date.fromisoformat(paid['date']),time(23,59,59),UTC) if paid else now
                days=max(0,(end.date()-due.date()).days) if due else 0
                value=float(Decimal(str(rule['amount']))*days)
                if rule.get('cap') is not None:value=min(value,rule['cap'])
            else:value=rule['amount'] if due and due<=now and not paid else 0
            entry(rule,0 if paid else value,'unquantified' if not due else 'fulfilled' if paid else 'supported',detail=('Settled historical amount '+str(value)+'. ' if paid else '')+('Accrued daily penalty.' if rule['kind']=='daily_penalty' else 'Due fixed payment.'))
            obligation(rule,'Late-payment penalty starts' if rule['kind']=='daily_penalty' else 'Contract payment due',due,status='fulfilled' if paid else None)
    # Explicit non-monetary calendar deadlines and hour-level event obligations.
    rule_clauses={r['clause_id'] for r in rules}
    for c in state['contracts'] if include_obligations else []:
        for cl in c['clauses']:
            t=cl['text'];lower=t.lower();base={**source(c,cl),'id':'time:'+cl['id'],'type':clause_type(t),'confidence':1.0}
            ds=dates(t)
            if cl['id'] not in rule_clauses and ds and re.search(r'no later than|received by|due on|deadline|unless .*? by',lower):
                due=datetime.combine(ds[-1][0],time(23,59,59),UTC)
                obligation(base,'Contract notice deadline',due,status='fulfilled' if completed(events,base,'notice',due) else None)
            hours=re.search(r'within\s+(\d+)\s+hours',lower)
            if not hours or not any(w in lower for w in ('incident','detection','confirming','unauthorized')):continue
            for event in events:
                if 'unauthorized' in lower and not event.get('unauthorized_access_confirmed'):continue
                if event['type'] not in ('outage','incident'):continue
                if event.get('contract_id') and c['id']!=event['contract_id'] and c['id'] not in event.get('affected_contract_ids',[]):continue
                anchor=instant(event.get('confirmed_at') if 'confirming' in lower else event.get('detected_at') if 'detection' in lower else event.get('timestamp'))
                due=anchor+timedelta(hours=int(hours[1])) if anchor else None
                fulfilled=completed(events,base,'notice')
                obligation(base,'Incident report required' if 'report' in lower else 'Incident notification required',due,event,'fulfilled' if fulfilled else None,reason=f"{hours[1]} hours from recorded event anchor" if anchor else 'Event timestamp/detection/confirmation time is missing; exact deadline unresolved.')
    # Preserve cited agent interpretations, keeping compiled arithmetic authoritative.
    for o in (state.get('live_results') or {}).get('Norns',{}).get('obligations',[]) if include_obligations else []:
        if not any(c['id']==o.get('contract_id') and any(cl['id']==o.get('clause_id') and o.get('quote','') in cl['text'] for cl in c['clauses']) for c in state['contracts']):continue
        if any(x['clause_id']==o['clause_id'] for x in obligations):continue
        due=datetime.combine(date.fromisoformat(o['due_date']),time(23,59,59),UTC) if o.get('due_date') else None
        base=dict(o,id='interpreted:'+o['clause_id'],type=clause_type(o.get('title','')),confidence=None)
        obligation(base,o['title'],due,reason='Agent interpretation: '+o.get('date_basis',''))
    totals=defaultdict(lambda:{'gross':0,'recovery':0,'net':0,'commitments':0,'conditional':False})
    for e in entries:
        total=totals[e['currency']]
        total['commitments' if e['direction']=='commitment' else 'recovery' if e['direction']=='recovery' else 'gross']+=e['amount']
        total['conditional'] |= e['status']=='conditional'
    for total in totals.values():
        for field in ('gross','recovery','commitments'):total[field]=round(total[field],2)
        total['net']=round(total['gross']-total['recovery'],2)
    return {'as_of':now.isoformat(),'rules':rules,'unsupported':unsupported,'entries':entries,'currencies':dict(totals),'obligations':sorted(obligations,key=lambda o:o['due_at'] or '9999'),'coverage':{'compiled':len(rules),'unquantified':len(unsupported)},'basis':'Source-compiled fixed amounts and calendar/hour rules. Separate currencies; conditional recoveries and renewal commitments are identified.'}

def findings(state):
    if state['mode']=='demo':
        import demo
        return demo.scenario(state)['findings']
    results=state.get('live_results') or {}
    rulings={r['finding_id']:r for r in results.get('Tyr',{}).get('rulings',[])}
    clauses={cl['id']:cl['text'] for c in state['contracts'] for cl in c['clauses']}
    return [dict(f,status=rulings.get(f['id'],{}).get('verdict','unresolved'),confidence=rulings.get(f['id'],{}).get('confidence')) for f in results.get('Loki',{}).get('findings',[]) if all(e.get('quote','') and e.get('quote','') in clauses.get(e.get('clause_id'),'') for e in f.get('evidence',[]))]

def graph(state,fs):
    nodes=[{'id':'company','type':'company','label':state['company']}];edges=[];known=set();parties={c['party']:c['id'] for c in state['contracts'] if c['party']!='Pending extraction'}
    for c in state['contracts']:
        nodes.append({'id':c['id'],'type':'contract','label':c['name'],'contract_id':c['id']})
        pid='party:'+hashlib.sha256(c['party'].encode()).hexdigest()[:10]
        if pid not in known:nodes.append({'id':pid,'type':'party','label':c['party'],'contract_id':c['id']});known.add(pid)
        edges.extend([{'source':'company','target':c['id'],'type':'owns'},{'source':pid,'target':c['id'],'type':'party'}])
        for cl in c['clauses']:
            nodes.append({'id':cl['id'],'type':'clause','label':cl['number']+' · '+clause_type(cl['text']),'contract_id':c['id'],'quote':cl['text']})
            edges.append({'source':c['id'],'target':cl['id'],'type':'contains'})
            for party,cid in parties.items():
                if cid!=c['id'] and party.lower() in cl['text'].lower():
                    dependency=bool(re.search(r'depends on|hosted on|support .*? for|infrastructure',cl['text'],re.I))
                    edges.append({'source':cl['id'],'target':cid,'type':'dependency' if dependency else 'reference','evidence':[source(c,cl)]})
    for f in fs:
        ids=list(dict.fromkeys(e['clause_id'] for e in f.get('evidence',[])))
        for target in ids[1:]:edges.append({'source':ids[0],'target':target,'type':'conflict' if f.get('status')!='rejected' else 'rejected_challenge','finding_id':f['id'],'label':f['title'],'severity':f.get('severity'),'status':f.get('status')})
    return {'nodes':nodes,'edges':edges}

def build(state):
    compiled=compile_rules(state);financial=evaluate(state,compiled=compiled);fs=findings(state);now=as_of(state);alerts=[]
    for o in financial['obligations']:
        if o['status'] in ('fulfilled','expired') or o['days'] is None or o['days']>30:continue
        alerts.append({'id':'deadline:'+o['id'],'title':o['title'],'severity':'high' if o['days']<=1 else 'medium' if o['days']<=7 else 'low','reason':o['status']+' · '+(o['due_at'] or 'Unresolved'),'clause_id':o['clause_id'],'contract_id':o['contract_id'],'due_at':o['due_at'],'kind':'deadline'})
    for f in fs:
        if f.get('status')=='rejected':continue
        alerts.append({'id':'finding:'+f['id'],'title':f['title'],'severity':f.get('severity','medium'),'reason':f.get('claim',''),'finding_id':f['id'],'kind':'finding'})
    alerts.sort(key=lambda a:({'high':0,'medium':1,'low':2}.get(a['severity'],3),a.get('due_at') or '9999'))
    projection=[]
    for offset in range(61):
        t=now+timedelta(days=offset)
        # No new future notices/payments are assumed; recorded evidence remains honored.
        future=dict(state,events=[e for e in state['events'] if (instant(e.get('timestamp')) or datetime.combine(date.fromisoformat(e['date']),time.min,UTC))<=now])
        projected=evaluate(future,t,compiled=compiled,include_obligations=False)
        contracts={};worst_case={cur:dict(total,recovery=0,net=total['gross']) for cur,total in projected['currencies'].items()}
        for entry in projected['entries']:
            total=contracts.setdefault(entry['contract_id'],{}).setdefault(entry['currency'],{'gross':0,'recovery':0,'commitments':0,'net':0,'secured_recovery':0,'worst_case_net':0})
            total['commitments' if entry['direction']=='commitment' else 'recovery' if entry['direction']=='recovery' else 'gross']+=entry['amount']
            if entry['direction']=='recovery' and entry['status']=='supported':
                worst_case[entry['currency']]['recovery']+=entry['amount'];total['secured_recovery']+=entry['amount']
        for totals in contracts.values():
            for total in totals.values():
                total['net']=round(total['gross']-total['recovery'],2);total['worst_case_net']=round(total['gross']-total['secured_recovery'],2)
        for total in worst_case.values():total['net']=round(total['gross']-total['recovery'],2)
        projection.append({'date':t.date().isoformat(),'currencies':projected['currencies'],'contracts':contracts,'worst_case':worst_case})
    cells={}
    for o in financial['obligations']:
        if not o['date'] or o['status']=='fulfilled':continue
        key=(o['contract_id'],o['type'],o['date'][:7]);cell=cells.setdefault(key,{'contract_id':key[0],'type':key[1],'month':key[2],'count':0,'weight':0,'clause_ids':[]})
        cell['count']+=1;cell['weight']+=3 if o['days']<=1 else 2 if o['days']<=7 else 1;cell['clause_ids'].append(o['clause_id'])
    return {'financial':financial,'projection':projection,'graph':graph(state,fs),'alerts':alerts,'heatmap':list(cells.values()),'findings':fs,'events':state['events'],'as_of':now.isoformat()}

def contract_report(state,cid,insights=None):
    c=next(c for c in state['contracts'] if c['id']==cid);insights=insights or build(state)
    extraction=next((t for t in (state.get('live_results') or {}).get('Thor',[]) if t['contract_id']==cid),{})
    lines=[f'# Contract report: {c["name"]}','',f'Company: {state["company"]}',f'Counterparty: {c["party"]}',f'As of: {insights["as_of"]}',f'Analysis status: {(state.get("run") or {}).get("status","demo" if state["mode"]=="demo" else "not_started")}','Confidence values are uncalibrated model assessments; explicit source-rule arithmetic is separately identified.','','## Key terms and confidence']
    if state.get('results_are_stale'):lines.insert(7,'Retained prior model analysis is stale. Current source-rule dates and amounts are recalculated independently.')
    for f in extraction.get('facts',[]):lines += [f'- {f.get("type")}: {f.get("value")} | confidence {f.get("confidence")} [{f["clause_id"]}]',f'  Source: {f["quote"]}']
    if not extraction:lines+=['No live extraction available. Source clauses and deterministic rules follow.']
    lines+=['','## Ambiguities and missing information']+['- '+x for x in extraction.get('ambiguities',[])]
    lines+=['','## Obligations and timeline']
    for o in insights['financial']['obligations']:
        if o['contract_id']==cid:lines+=[f'- {o["due_at"] or "Unresolved"}: {o["title"]} | {o["status"]} [{o["clause_id"]}] | {o["date_basis"]}']
    lines+=['','## Recorded payments, notices, and events']
    for e in state['events']:
        if not e.get('contract_id') or e.get('contract_id')==cid:lines+=[f'- {e.get("timestamp",e["date"])}: {e.get("title",e["type"])} | {e.get("status","reported")} | {e.get("clause_id","Portfolio event")} | {e.get("description","")}']
    lines+=['','## Risks, challenges, verification, and rulings']
    for f in insights['findings']:
        if any(e['contract_id']==cid for e in f.get('evidence',[])):
            verification=next((v for v in (state.get('live_results') or {}).get('Heimdall',{}).get('verifications',[]) if v['finding_id']==f['id']),{})
            ruling=next((v for v in (state.get('live_results') or {}).get('Tyr',{}).get('rulings',[]) if v['finding_id']==f['id']),{})
            lines += [f'### {f["title"]}',f'Severity: {f.get("severity")} | Likelihood: {f.get("likelihood","Scenario-defined")} | Ruling: {f.get("status")} | Confidence: {ruling.get("confidence","Unconfirmed")}',f['claim'],'Attack path: '+f.get('attack_path','See the cited scenario conditions.'),'Verification: '+verification.get('reason','Synthetic scenario or not yet verified.'),'Rationale: '+ruling.get('rationale','See finding status.')]
            lines += [f'- [{e["clause_id"]}] {e["quote"]}' for e in f['evidence']]
    lines+=['','## Financial exposure and no-action projection']
    for e in insights['financial']['entries']:
        if e['contract_id']==cid:lines += [f'- {e["currency"]} {e["amount"]:,.2f} | {e["direction"]} | {e["status"]} [{e["clause_id"]}] — {e["detail"]}']
    for offset in (0,7,30,60):
        point=insights['projection'][offset]
        lines += [f'- {point["date"]}: opportunity-adjusted '+(str(point['contracts'].get(cid)) if point['contracts'].get(cid) else 'No compiled monetary exposure.')]
    lines += [f'- Unquantified [{u["clause_id"]}]: {u["reason"]}' for u in insights['financial']['unsupported'] if u['contract_id']==cid]
    lines+=['','## Recommended actions and approval']
    for a in sorted(state['actions'],key=lambda a:a.get('due_date') or '9999'):
        if any(cl['id'] in a.get('clause_ids',[]) for cl in c['clauses']):
            ruling=next((r for r in (state.get('live_results') or {}).get('Tyr',{}).get('rulings',[]) if r['finding_id']==a.get('finding_id')),{} )
            lines += [f'### {a["title"]}',f'Owner: {a["owner"]} | Due: {a.get("due_date") or "Unresolved"} | {a["status"]} | Confidence: {a.get("confidence",ruling.get("confidence","Unconfirmed"))}',a['draft'],'References: '+', '.join(a['clause_ids'])]
    lines+=['','## References — original clause text']+[f'- [{cl["id"]}] Clause {cl["number"]}, page {cl["page"]}: {cl["text"]}' for cl in c['clauses']]
    return '\n'.join(lines)

def company_report(state):
    insights=build(state)
    lines=['# Odin — Company risk report','',f'Company: {state["company"]}',f'As of: {insights["as_of"]}',f'Mode: {state["mode"]}',f'Agent status: {(state.get("run") or {}).get("status","not_started")}','','## Total financial exposure by currency',insights['financial']['basis']]
    if state.get('results_are_stale'):lines.insert(6,'Retained prior model analysis is stale. Current source-rule dates and amounts are recalculated independently.')
    if (state.get('run') or {}).get('error'):lines.insert(6,'Latest run error: '+state['run']['error'])
    for cur,t in insights['financial']['currencies'].items():lines += [f'- {cur}: gross {t["gross"]:,.2f}; conditional recovery {t["recovery"]:,.2f}; net {t["net"]:,.2f}; renewal commitments (separate) {t["commitments"]:,.2f}. Conditional inputs: {t["conditional"]}.']
    lines+=['Unquantified monetary clauses: '+str(len(insights['financial']['unsupported'])),'','## Worst-case / no-action horizon','Assumes no additional notices or payments; honors already recorded receipt evidence. Conditional upper-bound exposure is not a prediction.']
    lines += [f'- {insights["projection"][i]["date"]}: '+str(insights['projection'][i]['worst_case']) for i in (0,7,30,60)]
    lines+=['','## Prioritized alerts and actions']+[f'- {a["severity"].upper()}: {a["title"]} — {a["reason"]}' for a in insights['alerts']]
    lines+=['','## Prioritized action list']
    for action in sorted(state['actions'],key=lambda a:a.get('due_date') or '9999'):
        ruling=next((r for r in (state.get('live_results') or {}).get('Tyr',{}).get('rulings',[]) if r['finding_id']==action.get('finding_id')),{} )
        lines+=[f'- {action["title"]} | Owner: {action["owner"]} | Due: {action.get("due_date") or "Unconfirmed"} | {action["status"]} | Confidence: {action.get("confidence",ruling.get("confidence","Unconfirmed"))} | '+', '.join(action['clause_ids'])]
    lines+=['','## Cross-contract challenges']
    for f in insights['findings']:
        if len({e['contract_id'] for e in f.get('evidence',[])})>1:lines+=[f'- {f["title"]}: {f["claim"]} | {f.get("status")} | '+', '.join(e['clause_id'] for e in f['evidence'])]
    lines+=['','## Review issues']+['- '+x for x in (state.get('run') or {}).get('issues',[])]
    lines += ['- Unquantified '+u['clause_id']+': '+u['reason'] for u in insights['financial']['unsupported']]
    for c in state['contracts']:lines+=['',contract_report(state,c['id'],insights)]
    return '\n'.join(lines)
