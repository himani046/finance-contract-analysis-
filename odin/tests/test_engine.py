import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import demo
import agents
from server import split_clauses

def outage(classification='unplanned',duration=95):
    s=demo.fixture()
    s['events']=[{'id':'test','type':'outage','date':'2026-10-25','classification':classification,'duration_minutes':duration}]
    return s

class ScenarioTests(unittest.TestCase):
    def test_no_event_no_incident_exposure(self):
        sc=demo.scenario(demo.fixture())
        self.assertEqual((sc['gross'],sc['recovery'],sc['net']),(0,0,0))
        self.assertEqual(sc['commitments'],240000)

    def test_qualifying_incident(self):
        sc=demo.scenario(outage())
        self.assertEqual((sc['gross'],sc['recovery'],sc['net']),(100000,30000,70000))
        self.assertEqual(sc['deadline'],'2026-11-01')

    def test_boundary_inclusive_through_deadline_date(self):
        s=outage()
        s['as_of']='2026-11-01'
        self.assertEqual(demo.scenario(s)['recovery'],30000)
        s['as_of']='2026-11-02'
        self.assertEqual(demo.scenario(s)['recovery'],0)

    def test_future_event_does_not_affect_past(self):
        s=outage(); s['as_of']='2026-10-24'
        self.assertEqual(demo.scenario(s)['gross'],0)

    def test_unknown_is_explicitly_conditional(self):
        sc=demo.scenario(outage('unknown'))
        self.assertTrue(sc['conditional'])
        self.assertEqual(sc['findings'][0]['status'],'qualified')

    def test_scheduled_maintenance_excluded(self):
        sc=demo.scenario(outage('scheduled'))
        self.assertEqual(sc['gross'],0)
        self.assertEqual(sc['findings'][0]['status'],'rejected')

    def test_threshold_is_strict(self):
        self.assertEqual(demo.scenario(outage(duration=60))['gross'],0)
        self.assertEqual(demo.scenario(outage(duration=61))['gross'],100000)

    def test_unknown_classification_still_requires_duration_threshold(self):
        sc=demo.scenario(outage(classification='unknown',duration=60))
        self.assertEqual((sc['gross'],sc['recovery'],sc['net']),(0,0,0))
        self.assertFalse(sc['conditional'])
        self.assertEqual(sc['findings'][0]['status'],'rejected')

    def test_approval_does_not_fake_delivery(self):
        s=outage();s['actions']=[dict(demo.claim_action(s['events'][0]),status='approved')];s['as_of']='2026-11-02'
        self.assertEqual(demo.scenario(s)['recovery'],0)

    def test_evidence_validation_rejects_fabrication(self):
        e=demo.evidence('atlas','8.2')
        self.assertTrue(agents.validate_evidence(e,demo.contracts()))
        e['quote']='The vendor pays INR 300,000 in cash.'
        self.assertFalse(agents.validate_evidence(e,demo.contracts()))

    def test_wrong_document_rejected(self):
        e=demo.evidence('atlas','8.2');e['contract_id']='northstar'
        self.assertFalse(agents.validate_evidence(e,demo.contracts()))

    def test_clause_parser_preserves_text_and_page(self):
        pages=['1.1 Agreement begins on 1 January.\n2.1 Payment due in 30 days.','3.1 Termination requires notice.']
        clauses=split_clauses(pages,'x')
        self.assertEqual(len(clauses),3)
        self.assertEqual(clauses[2]['page'],2)
        self.assertIn('Payment due in 30 days.',clauses[1]['text'])

    def test_all_fixture_evidence_resolves(self):
        for f in demo.scenario(outage())['findings']:
            for e in f['evidence']:
                self.assertTrue(agents.validate_evidence(e,demo.contracts()))

if __name__=='__main__': unittest.main()
