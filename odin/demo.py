"""Synthetic fixture and deterministic scenario engine. Never represented as live AI."""
from datetime import date, timedelta

START = '2026-10-25'

def contract(cid, title, party, category, clauses):
    return {'id':cid,'name':title,'party':party,'category':category,'synthetic':True,'version':1,
            'clauses':[{'id':f'{cid}-{n}','number':n,'page':1,'text':text} for n,text in clauses],
            'status':'ready'}

def contracts():
    return [
      contract('atlas','Atlas Cloud Services','Atlas Cloud','Infrastructure',[
        ('1.1','This agreement is between Meridian Labs and Atlas Cloud, effective 1 January 2026 through 31 December 2026.'),
        ('4.2','A qualifying incident is an unplanned production outage lasting more than 60 consecutive minutes. Scheduled maintenance announced at least 48 hours in advance is excluded.'),
        ('8.2','For each qualifying incident, Meridian Labs is eligible for an INR 30,000 service credit. A written claim with an incident report must be received by 23:59 UTC on the seventh calendar day after the incident date. An approved timely claim preserves credit eligibility after this deadline.'),
        ('8.3','Service credits are the sole monetary remedy and are capped at INR 30,000 per incident. Credits are applied to future invoices, not paid in cash.'),
        ('11.1','The agreement renews on 1 January 2027 for twelve months unless written non-renewal notice is received no later than 1 December 2026.')]),
      contract('northstar','Northstar Enterprise SLA','Northstar Retail','Customer',[
        ('1.1','Meridian Labs provides a production analytics service to Northstar Retail from 1 January 2026 through 31 December 2026.'),
        ('3.1','The production analytics service depends on the Atlas Cloud production infrastructure.'),
        ('6.1','An unplanned production outage lasting more than 60 consecutive minutes requires Meridian Labs to issue an INR 100,000 service credit to Northstar Retail within 30 calendar days of the incident date. Scheduled maintenance announced at least 48 hours in advance is excluded. The credit is capped at INR 100,000 per incident.'),
        ('6.2','An incident notification must be provided to the customer within 24 hours of detection.'),
        ('9.1','Customer service credits are independent of any recovery Meridian Labs may obtain from its infrastructure providers.')]),
      contract('beacon','Beacon Incident Support','Beacon Operations','Operations',[
        ('1.1','Beacon Operations provides incident support to Meridian Labs for the production service hosted on Atlas Cloud.'),
        ('4.1','Beacon must deliver an incident report identifying start time, end time and maintenance classification within 48 hours of an incident.'),
        ('4.2','A planned maintenance exclusion requires written evidence that the maintenance was announced at least 48 hours before the interruption.'),
        ('7.1','Failure to supply the report does not automatically establish whether the outage qualifies under any third-party agreement.')]),
      contract('prism','Prism Analytics License','Prism Software','Software',[
        ('1.1','Meridian Labs licenses Prism Analytics for INR 240,000 per annual term, from 1 December 2025 to 30 November 2026.'),
        ('5.1','This license renews automatically on 1 December 2026 for another annual term at INR 240,000 unless written cancellation is received by 1 November 2026 at 23:59 UTC.'),
        ('5.2','Cancellation prevents future renewal only; it does not refund fees paid for the current term.')]),
      contract('aegis','Aegis Data Processing','Aegis Data','Compliance',[
        ('2.1','Aegis processes personal data for Meridian Labs during the term of the services agreement.'),
        ('7.1','Aegis must notify Meridian Labs within 24 hours after confirming unauthorized access to personal data. A service outage alone does not establish unauthorized access.'),
        ('8.1','Aegis must maintain an audit trail of incident notifications. No monetary remedy is specified in this schedule.')])
    ]

def evidence(cid, num):
    c = next(c for c in contracts() if c['id']==cid)
    cl = next(x for x in c['clauses'] if x['number']==num)
    return {'contract_id':cid,'clause_id':cl['id'],'quote':cl['text']}

def fixture():
    return {'company':'Meridian Labs','mode':'demo','as_of':START,'contracts':contracts(),'events':[],
      'actions':[{'id':'renewal','title':'Review Prism renewal','owner':'Finance','due_date':'2026-11-01','status':'needs_approval','clause_ids':['prism-5.1'],'draft':'Subject: Non-renewal notice — Prism Analytics\n\nFor authorized review only.\n\nPursuant to Clause 5.1 of the Prism Analytics License, Meridian Labs gives notice that it does not intend to renew the term beginning 1 December 2026. Please acknowledge receipt before 1 November 2026 at 23:59 UTC.\n\n[Authorized signatory]'}],
      'run':None,'live_results':None}

def scenario(state):
    today = date.fromisoformat(state['as_of'])
    events = [e for e in state['events'] if e.get('type')=='outage' and e.get('date','9999') <= state['as_of']]
    event = events[-1] if events else None
    incident = date.fromisoformat(event['date']) if event else today
    deadline = incident + timedelta(days=7)
    confirmed = bool(event and event.get('classification')=='unplanned' and event.get('duration_minutes',0)>60)
    unknown = bool(event and event.get('classification')=='unknown' and event.get('duration_minutes',0)>60)
    gross = 100000 if confirmed or unknown else 0
    recovery = 30000 if (confirmed or unknown) and today <= deadline else 0
    findings = [{'id':'renewal','title':'An annual renewal is approaching','severity':'medium','status':'supported','claim':'Prism renews for INR 240,000 on 1 December unless cancellation is received by 1 November. This is a future commitment, separate from incident exposure.','contract_ids':['prism'],'evidence':[evidence('prism','5.1')],'amount':240000,'type':'commitment'}]
    if today > date(2026,11,1):
        findings[0].update(title='The Prism cancellation window has closed',severity='high',claim='With no cancellation recorded by 1 November, the modeled INR 240,000 renewal commitment remains. This is separate from incident exposure; review any available negotiated options.')
    if event:
        status = 'supported' if confirmed else ('qualified' if unknown else 'rejected')
        findings.insert(0,{'id':'outage','title':'One outage. Two financial consequences.','severity':'high' if confirmed else 'medium','status':status,'claim':('The qualifying outage triggers a customer credit and a separate, conditional vendor recovery.' if confirmed else 'Outage classification must be verified before a customer credit or vendor recovery can be established.' if unknown else 'The event does not meet the modeled qualifying outage conditions.'),'contract_ids':['atlas','northstar','beacon'],'evidence':[evidence('northstar','6.1'),evidence('atlas','8.2'),evidence('beacon','4.2')],'amount':gross,'type':'incident'})
        if today > deadline and (confirmed or unknown):
            findings[0].update(title='The vendor claim window has closed',claim=f'The claim deadline was {deadline.isoformat()}. No submitted claim is recorded, so modeled vendor recovery is now zero. Customer credit exposure '+('remains conditional on qualification.' if unknown else 'remains INR 100,000.'))
    obligations = [{'id':'renewal','title':'Prism cancellation window','date':'2026-11-01','contract_id':'prism','clause_id':'prism-5.1','kind':'renewal'}, {'id':'atlas-renewal','title':'Atlas non-renewal notice','date':'2026-12-01','contract_id':'atlas','clause_id':'atlas-11.1','kind':'renewal'}]
    if event:
        obligations += [{'id':'claim','title':'Submit Atlas credit claim','date':deadline.isoformat(),'contract_id':'atlas','clause_id':'atlas-8.2','kind':'claim'}, {'id':'report','title':'Beacon incident evidence due','date':(incident+timedelta(days=2)).isoformat(),'contract_id':'beacon','clause_id':'beacon-4.1','kind':'evidence'}, {'id':'customer','title':'Customer credit due if eligible','date':(incident+timedelta(days=30)).isoformat(),'contract_id':'northstar','clause_id':'northstar-6.1','kind':'payment'}]
    for o in obligations:
        o['days']=(date.fromisoformat(o['date'])-today).days
        o['status']='overdue' if o['days']<0 else 'due_today' if o['days']==0 else 'upcoming'
    debate = [
      {'agent':'Odin','type':'Plan','text':'Five contract workstreams and one cross-contract review. Synthetic fixture; no Gemini calls are made in this mode.'},
      {'agent':'Thor','type':'Evidence','text':'Indexed 20 source clauses with exact quotes and clause identifiers.'},
      {'agent':'Norns','type':'Timeline','text':'Prism cancellation closes on 1 November. The simulation recalculates deadlines with deterministic calendar arithmetic.'}]
    if event:
        debate += [
          {'agent':'Loki','type':'Challenge','text':'A production outage could trigger INR 100,000 of customer credits while supplier recovery is capped at INR 30,000. Inspect both agreements.'},
          {'agent':'Heimdall','type':'Verification','text':('The event confirms an unplanned outage longer than 60 minutes. Both trigger definitions are met; vendor recovery still requires a timely valid claim.' if confirmed else 'The maintenance exclusion matters. The event does not establish an eligible unplanned outage.' )},
          {'agent':'Thor','type':'Clarification','text':'Beacon Clause 4.2 requires evidence of 48-hour advance notice to establish the maintenance exclusion.'},
          {'agent':'Tyr','type':'Ruling','text':('Support customer credit exposure. Keep vendor recovery conditional; draft a claim for approval and obtain the incident report.' if confirmed else 'Qualify the financial scenario. Obtain maintenance classification and the incident report before treating either amount as established.' if unknown else 'Reject automatic credit liability for this event under the modeled conditions. Preserve the source evidence.')}]
    return {'gross':gross,'recovery':recovery,'net':gross-recovery,'conditional':unknown,'event':event,'deadline':deadline.isoformat() if event else None,'days_left':(deadline-today).days if event else None,'findings':findings,'obligations':sorted(obligations,key=lambda o:o['date']),'debate':debate,'commitments':240000,'currency':'INR','formula':'Customer credit − eligible vendor credit. Vendor credit is conditional and non-cash. Renewal commitments are excluded.'}

def claim_action(event):
    deadline=(date.fromisoformat(event['date'])+timedelta(days=7)).isoformat()
    return {'id':'claim-'+event['id'],'title':'Prepare Atlas credit claim','owner':'Operations','due_date':deadline,'status':'needs_approval','clause_ids':['atlas-8.2','atlas-4.2'],'draft':f'Subject: Service credit claim — incident on {event["date"]}\n\nFor authorized review. Eligibility and attachments must be verified before sending.\n\nUnder Clause 8.2 of the Atlas Cloud Services agreement, Meridian Labs requests review of a service credit for the production incident dated {event["date"]}. Clause 4.2 defines a qualifying incident.\n\nReported duration: {event.get("duration_minutes",0)} minutes. Classification: {event.get("classification","unknown")}.\n\nThe contractual credit is INR 30,000 if eligibility is confirmed. Please acknowledge receipt by {deadline} at 23:59 UTC.\n\nRequired attachment: verified incident report.\n[Authorized signatory]'}
