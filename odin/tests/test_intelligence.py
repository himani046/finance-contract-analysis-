import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import demo
import intelligence as intel


class IntelligenceTests(unittest.TestCase):
    def state(self):
        s=demo.fixture();s['mode']='live'
        s['events']=[{'id':'outage','type':'outage','date':'2026-10-25','timestamp':'2026-10-25T12:00:00Z','detected_at':'2026-10-25T12:05:00Z','classification':'unplanned','duration_minutes':95}]
        return s

    def receipt(self,clause='atlas-8.2',day='2026-11-01',**extra):
        return dict({'id':'receipt','type':'notice','date':day,'contract_id':clause.split('-')[0],'clause_id':clause,'status':'received','related_event_id':'outage','evidence_verified':True},**extra)

    def test_live_sample_amounts_come_from_source_rules(self):
        result=intel.evaluate(self.state())
        self.assertEqual((result['currencies']['INR']['gross'],result['currencies']['INR']['recovery'],result['currencies']['INR']['net']),(100000,30000,70000))
        self.assertEqual(result['currencies']['INR']['commitments'],240000)
        self.assertTrue(all(r['quote'] for r in result['rules']))

    def test_claim_expires_without_receipt(self):
        s=self.state();s['as_of']='2026-11-02'
        self.assertEqual(intel.evaluate(s)['currencies']['INR']['recovery'],0)

    def test_timely_verified_receipt_preserves_credit_after_deadline(self):
        s=self.state();s['as_of']='2026-11-02';s['events'].append(self.receipt())
        self.assertEqual(intel.evaluate(s)['currencies']['INR']['recovery'],30000)

    def test_late_receipt_does_not_resurrect_credit(self):
        s=self.state();s['as_of']='2026-11-03';s['events'].append(self.receipt(day='2026-11-02'))
        self.assertEqual(intel.evaluate(s)['currencies']['INR']['recovery'],0)

    def test_wrong_incident_or_unverified_report_does_not_preserve_credit(self):
        for extra in ({'related_event_id':'other'},{'evidence_verified':False},{'clause_id':'atlas-11.1'}):
            s=self.state();s['as_of']='2026-11-02';s['events'].append(self.receipt(**extra))
            self.assertEqual(intel.evaluate(s)['currencies']['INR']['recovery'],0)

    def test_unknown_classification_cannot_bypass_duration(self):
        s=self.state();s['events'][0].update(classification='unknown',duration_minutes=60)
        self.assertEqual(intel.evaluate(s)['currencies']['INR']['gross'],0)

    def test_maintenance_requires_verified_advance_notice(self):
        s=self.state();s['events'][0].update(classification='scheduled',advance_notice_hours=48)
        self.assertEqual(intel.evaluate(s)['currencies']['INR']['gross'],0)
        s['events'][0]['advance_notice_hours']=0
        self.assertTrue(intel.evaluate(s)['currencies']['INR']['conditional'])

    def test_hour_deadline_uses_detection_anchor(self):
        result=intel.evaluate(self.state())
        notice=next(o for o in result['obligations'] if o['clause_id']=='northstar-6.2')
        self.assertEqual(notice['due_at'],'2026-10-26T12:05:00+00:00')

    def test_missing_hour_anchor_stays_unresolved(self):
        s=self.state();s['events'][0].pop('detected_at')
        notice=next(o for o in intel.evaluate(s)['obligations'] if o['clause_id']=='northstar-6.2')
        self.assertIsNone(notice['due_at'])
        self.assertEqual(notice['status'],'unresolved')

    def test_outage_alone_does_not_trigger_data_breach_notice(self):
        self.assertFalse(any(o['clause_id']=='aegis-7.1' for o in intel.evaluate(self.state())['obligations']))

    def test_confirmed_access_uses_confirmation_time(self):
        s=self.state();s['events'][0].update(unauthorized_access_confirmed=True,confirmed_at='2026-10-25T15:00:00Z')
        notice=next(o for o in intel.evaluate(s)['obligations'] if o['clause_id']=='aegis-7.1')
        self.assertEqual(notice['due_at'],'2026-10-26T15:00:00+00:00')

    def test_received_nonrenewal_avoids_future_commitment(self):
        s=self.state();s['as_of']='2026-11-02';s['events'].append(self.receipt('prism-5.1'))
        self.assertEqual(intel.evaluate(s)['currencies']['INR']['commitments'],0)

    def test_generic_payment_and_capped_penalty_in_other_currency(self):
        s=self.state();s['contracts']=[demo.contract('custom','Other agreement','Other','Services',[('1.1','The company must pay USD 500 on 1 October 2026.'),('2.1','Late payment incurs a penalty of USD 25 per calendar day after 1 October 2026, capped at USD 100.')])]
        self.assertEqual(intel.evaluate(s)['currencies']['USD']['gross'],600)
        s['events'].append({'id':'paid','type':'payment','date':'2026-10-25','contract_id':'custom','clause_id':'custom-1.1','status':'received'})
        self.assertEqual(intel.evaluate(s)['currencies']['USD']['gross'],100)

    def test_multiple_currencies_are_never_added(self):
        s=self.state();s['contracts'].append(demo.contract('usd','Dollar','Dollar','Services',[('1.1','The company must pay USD 500 on 1 October 2026.')]))
        totals=intel.evaluate(s)['currencies']
        self.assertEqual(totals['USD']['gross'],500)
        self.assertEqual(totals['INR']['gross'],100000)

    def test_unsupported_formula_not_silently_zero(self):
        s=self.state();s['contracts']=[demo.contract('x','x','x','x',[('1.1','Damages are EUR 200 plus 5 percent of future revenue, subject to negotiation.')])]
        result=intel.evaluate(s)
        self.assertEqual(len(result['unsupported']),1)
        self.assertEqual(result['currencies'],{})

    def test_fixed_payment_with_variable_component_is_not_truncated(self):
        s=self.state();s['contracts']=[demo.contract('x','x','x','x',[('1.1','The company must pay USD 200 plus 5 percent of revenue on 1 October 2026.')])]
        result=intel.evaluate(s)
        self.assertEqual(result['currencies'],{})
        self.assertEqual(len(result['unsupported']),1)

    def test_cross_clause_cap_is_applied_and_cited(self):
        s=self.state();s['contracts'][0]['clauses'][3]['text']='Service credits are capped at INR 10,000 per incident.'
        result=intel.evaluate(s);rule=next(r for r in result['rules'] if r['id']=='credit:atlas-8.2')
        self.assertEqual(result['currencies']['INR']['recovery'],10000)
        self.assertTrue({'atlas-8.2','atlas-4.2','atlas-8.3'}.issubset({e['clause_id'] for e in rule['evidence']}))

    def test_conflicting_duration_definitions_do_not_compile(self):
        s=self.state();s['contracts'][0]['clauses'].append({'id':'atlas-conflict','number':'4.3','page':1,'text':'A qualifying outage lasts more than 30 consecutive minutes.'})
        result=intel.evaluate(s)
        self.assertFalse(any(r['id']=='credit:atlas-8.2' for r in result['rules']))
        self.assertTrue(any(u['clause_id']=='atlas-8.2' for u in result['unsupported']))

    def test_reported_notice_does_not_equal_received_notice(self):
        s=self.state();s['as_of']='2026-11-02';s['events'].append(self.receipt(status='reported'))
        self.assertEqual(intel.evaluate(s)['currencies']['INR']['recovery'],0)

    def test_other_company_liability_is_not_assigned_to_context(self):
        s=self.state();s['company']='Unrelated Limited'
        result=intel.evaluate(s)
        self.assertEqual(result['currencies'],{})
        self.assertTrue(any('company context' in u['reason'] for u in result['unsupported']))

    def test_compound_currency_payment_is_not_silently_truncated(self):
        s=self.state();s['contracts']=[demo.contract('x','x','x','x',[('1.1','The company must pay USD 500 and EUR 200 on 1 October 2026.')])]
        result=intel.evaluate(s)
        self.assertEqual(result['currencies'],{})
        self.assertEqual(len(result['unsupported']),1)

    def test_graph_contains_parties_clauses_dependencies_and_conflicts(self):
        s=self.state();s['mode']='demo';result=intel.build(s);g=result['graph'];ids={n['id'] for n in g['nodes']}
        self.assertTrue({'company','party','contract','clause'}.issubset({n['type'] for n in g['nodes']}))
        self.assertTrue({'contains','dependency','conflict'}.issubset({e['type'] for e in g['edges']}))
        self.assertTrue(all(e['source'] in ids and e['target'] in ids for e in g['edges']))

    def test_projection_has_deadline_jump_and_61_positions(self):
        result=intel.build(self.state())
        self.assertEqual(len(result['projection']),61)
        self.assertEqual(result['projection'][7]['currencies']['INR']['net'],70000)
        self.assertEqual(result['projection'][8]['currencies']['INR']['net'],100000)
        self.assertEqual(result['projection'][0]['worst_case']['INR']['net'],100000)
        self.assertEqual(result['projection'][0]['worst_case']['INR']['recovery'],0)

    def test_fulfilled_deadline_is_removed_from_alerts(self):
        s=self.state();s['events'].append(self.receipt('prism-5.1',day='2026-10-25'))
        self.assertFalse(any(a.get('clause_id')=='prism-5.1' for a in intel.build(s)['alerts']))

    def test_heatmap_keeps_contract_type_month_and_sources(self):
        cells=intel.build(self.state())['heatmap']
        self.assertTrue(any(c['contract_id']=='prism' and c['type']=='renewal' and c['month']=='2026-11' and 'prism-5.1' in c['clause_ids'] for c in cells))

    def test_reports_are_independent_and_complete(self):
        s=self.state();report=intel.contract_report(s,'atlas')
        for title in ('Key terms and confidence','Obligations and timeline','Risks, challenges','Financial exposure','Recommended actions','References'):
            self.assertIn(title,report)
        self.assertIn('atlas-8.2',report)
        self.assertNotIn('## Contract report: Prism',report)
        company=intel.company_report(s)
        self.assertIn('Worst-case / no-action horizon',company)
        self.assertIn('Cross-contract challenges',company)

if __name__=='__main__':unittest.main()
