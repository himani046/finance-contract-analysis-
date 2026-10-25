import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
import demo
import agents

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=server.ROOT/'data',prefix='test-')
        self.old_db=server.DB
        server.DB=Path(self.tmp.name)/'test.db'
        self.s=demo.fixture()
        self.s.update(mode='live',contracts=[demo.contracts()[0]])
        self.config={'model':'gemini-3.8-flash','max_calls':18,'max_tokens':60000,'max_seconds':600}

    def tearDown(self):
        server.DB=self.old_db
        if Path(self.tmp.name).resolve().is_relative_to((server.ROOT/'data').resolve()):
            self.tmp.cleanup()

    def response(self,name,context,model):
        e=demo.evidence('atlas','8.2')
        values={
          'Odin':{'summary':'Plan','workstreams':[{'contract_id':'atlas','task':'Review'},{'contract_id':'portfolio','task':'Cross-contract review'}]},
          'Thor':{'facts':[dict(e,type='obligation',value='Credit claim deadline',confidence=.9)],'ambiguities':[]},
          'Norns':{'obligations':[dict(e,title='Claim window',due_date='',date_basis='Needs event date',status='unresolved')],'uncertainties':['Event date missing']},
          'Loki':{'findings':[{'id':'x','title':'Claim deadline','severity':'medium','likelihood':'Conditional','claim':'A late claim can lose credit eligibility.','attack_path':'Miss deadline','evidence':[e],'assumptions':[]}],'clarifications':[]},
          'Heimdall':{'verifications':[{'finding_id':'finding-1','verdict':'qualified','reason':'Needs event','missing_facts':['Incident date']}],'event_mappings':[]},
          'Tyr':{'rulings':[{'finding_id':'finding-1','verdict':'qualified','rationale':'Needs event','confidence':.9}],'actions':[{'title':'Collect evidence','finding_id':'finding-1','owner':'Operations','due_date':'','draft':'Subject: Evidence request for Atlas credit eligibility\n\nTo: [Operations contact]\n\nPlease review Atlas clause 8.2 and collect the incident evidence needed to assess a potential service credit. Confirm the incident date, outage duration, classification, and any advance maintenance notice before reaching a conclusion. Please attach the incident report, the relevant system logs, and the written receipt acknowledgement if a claim has already been submitted. This request does not establish eligibility, authorize a notice, or confirm that a claim was received on time. Escalate any missing information to the contract owner and preserve the original supporting records for authorized review.\n\n[Authorized signatory]','clause_ids':['atlas-8.2']}],'summary':'Collect evidence'}
        }
        return values[name],100

    def run_once(self,rid='test'):
        self.s['run']={'id':rid,'status':'running','trace':[],'workstreams':{'atlas':'queued','portfolio':'queued'}}
        server.save(self.s)
        server.RUN_LOCK.acquire()
        server.run_agents(rid,self.s,self.config)
        return server.load()

    def test_all_roles_and_shared_state(self):
        with patch.object(agents,'call_agent',side_effect=self.response) as call:
            result=self.run_once()
        self.assertEqual(result['run']['status'],'complete')
        self.assertEqual([c.args[0] for c in call.call_args_list],['Odin','Thor','Norns','Loki','Heimdall','Tyr'])
        self.assertEqual(result['actions'][0]['status'],'needs_approval')
        self.assertEqual(result['run']['tokens'],600)

    def test_repeated_input_reuses_cache(self):
        with patch.object(agents,'call_agent',side_effect=self.response) as call:
            self.run_once('one')
            first=call.call_count
            result=self.run_once('two')
        self.assertEqual(call.call_count,first)
        self.assertEqual(result['run']['calls'],0)

    def test_invalid_evidence_is_excluded(self):
        def invalid(name,context,model):
            output,tokens=self.response(name,context,model)
            if name=='Loki': output['findings'][0]['evidence'][0]['quote']='A fabricated obligation with no source.'
            if name=='Tyr': output['actions']=[];output['rulings']=[]
            return output,tokens
        with patch.object(agents,'call_agent',side_effect=invalid):
            result=self.run_once()
        self.assertEqual(result['live_results']['Loki']['findings'],[])
        self.assertEqual(result['run']['status'],'needs_review')

    def test_service_failure_uses_only_authorized_fallback(self):
        def fallback(name,context,model):
            if model=='gemini-3.8-flash': raise agents.AgentError('Gemini request failed (HTTP 503).')
            return self.response(name,context,model)
        with patch.object(agents,'call_agent',side_effect=fallback) as call:
            result=self.run_once()
        self.assertEqual(result['run']['effective_model'],'gemini-3.6-flash')
        self.assertEqual({c.args[2] for c in call.call_args_list},{'gemini-3.8-flash','gemini-3.6-flash'})
        self.assertTrue(any(t['type']=='Model fallback' for t in result['run']['trace']))

    def test_authentication_failure_is_incomplete(self):
        with patch.object(agents,'call_agent',side_effect=agents.AgentError('Gemini authentication failed. Replace the API key.')):
            result=self.run_once()
        self.assertEqual(result['run']['status'],'incomplete')
        self.assertEqual(result['run']['calls'],1)
        self.assertFalse(server.RUN_LOCK.locked())

    def test_quota_keeps_partial_results_without_switching_models(self):
        def quota(name,context,model):
            if name=='Thor': raise agents.AgentError('Gemini quota or rate limit reached. Wait or check billing and quota.')
            return self.response(name,context,model)
        with patch.object(agents,'call_agent',side_effect=quota) as call:
            result=self.run_once()
        self.assertEqual(result['run']['status'],'incomplete')
        self.assertIn('quota',result['run']['error'])
        self.assertIn('Odin',result['live_results'])
        self.assertEqual({c.args[2] for c in call.call_args_list},{'gemini-3.8-flash'})
        self.assertFalse(server.RUN_LOCK.locked())

    def test_missing_arbitration_cannot_complete(self):
        def missing(name,context,model):
            output,tokens=self.response(name,context,model)
            if name=='Tyr': output['rulings']=[]
            return output,tokens
        with patch.object(agents,'call_agent',side_effect=missing): result=self.run_once()
        self.assertEqual(result['run']['status'],'needs_review')

    def test_low_confidence_triggers_targeted_feedback_and_loki_reassessment(self):
        def feedback(name,context,model):
            output,tokens=self.response(name,context,model)
            if name=='Thor' and 'clarify' not in context:output['facts'][0]['confidence']=0.3
            return output,tokens
        with patch.object(agents,'call_agent',side_effect=feedback) as call:result=self.run_once()
        self.assertEqual(result['run']['status'],'complete')
        self.assertEqual(result['run']['iterations'],1)
        self.assertEqual([c.args[0] for c in call.call_args_list].count('Loki'),2)
        targeted=next(c.args[1] for c in call.call_args_list if c.args[0]=='Thor' and 'clarify' in c.args[1])
        self.assertEqual(targeted['clarify'][0]['clause']['id'],'atlas-8.2')
        self.assertEqual(len(result['live_results']['ClarificationHistory']),1)

    def test_configurable_zero_round_limit_preserves_review_flag(self):
        self.config['max_iterations']=0
        def feedback(name,context,model):
            output,tokens=self.response(name,context,model)
            if name=='Thor':output['facts'][0]['confidence']=0.3
            return output,tokens
        with patch.object(agents,'call_agent',side_effect=feedback) as call:result=self.run_once()
        self.assertEqual(result['run']['status'],'needs_review')
        self.assertEqual([c.args[0] for c in call.call_args_list].count('Thor'),1)
        self.assertTrue(any('threshold' in i for i in result['run']['issues']))

    def test_repeated_clarification_cannot_loop_forever(self):
        self.config['max_iterations']=1
        def feedback(name,context,model):
            output,tokens=self.response(name,context,model)
            if name=='Loki':output['clarifications']=[{'contract_id':'atlas','clause_id':'atlas-8.2','question':'Clarify receipt.'}]
            return output,tokens
        with patch.object(agents,'call_agent',side_effect=feedback) as call:result=self.run_once()
        self.assertEqual(result['run']['status'],'needs_review')
        self.assertEqual(result['run']['iterations'],1)
        self.assertLessEqual(call.call_count,8)

    def test_response_crossing_token_budget_cannot_complete(self):
        self.config['max_tokens']=1000
        def expensive(name,context,model):
            output,_=self.response(name,context,model)
            return output,600
        with patch.object(agents,'call_agent',side_effect=expensive):result=self.run_once()
        self.assertEqual(result['run']['status'],'incomplete')
        self.assertIn('budget',result['run']['error'])

    def test_actions_have_arbitration_confidence(self):
        with patch.object(agents,'call_agent',side_effect=self.response):result=self.run_once()
        self.assertEqual(result['actions'][0]['confidence'],.9)
        self.assertIn('Tyr',result['actions'][0]['confidence_basis'])

    def test_failed_refresh_keeps_prior_analysis_explicitly_stale(self):
        self.s['live_results']={'Tyr':{'summary':'Earlier analysis','rulings':[]},'Odin':{'summary':'Earlier plan'}}
        with patch.object(agents,'call_agent',side_effect=agents.AgentError('Gemini quota or rate limit reached.')):result=self.run_once()
        self.assertTrue(result['results_are_stale'])
        self.assertEqual(result['live_results']['Tyr']['summary'],'Earlier analysis')
        self.assertEqual(result['run']['status'],'incomplete')
        self.assertEqual(result['partial_results'],{})

if __name__=='__main__': unittest.main()
