import base64
import json
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
import time
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
import demo

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(dir=server.ROOT/'data',prefix='test-api-')
        cls.old_db=server.DB
        server.DB=Path(cls.tmp.name)/'test.db'
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.base='http://127.0.0.1:'+str(cls.http.server_address[1])
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join()
        server.DB=cls.old_db
        if Path(cls.tmp.name).resolve().is_relative_to((server.ROOT/'data').resolve()):cls.tmp.cleanup()

    def setUp(self):
        server.save(demo.fixture())
        with server.connection() as db:db.execute('DELETE FROM modes')

    def request(self,path,data=None,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try:
            with urllib.request.urlopen(req) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:return e.code,json.load(e)

    def test_state_does_not_expose_key(self):
        status,body=self.request('/api/state')
        self.assertEqual(status,200)
        self.assertNotIn('GEMINI_API_KEY',json.dumps(body))
        self.assertIn('key_configured',body['config'])

    def test_secret_and_source_paths_not_served(self):
        for path in ('/.env','/server.py','/data/odin.db'):
            self.assertEqual(self.request(path)[0],404)

    def test_duplicate_event_id_is_idempotent(self):
        event={'id':'same','type':'outage','date':'2026-10-25','classification':'unplanned','duration_minutes':95}
        self.request('/api/event',event)
        status,body=self.request('/api/event',event)
        self.assertEqual(status,200)
        self.assertEqual(len(body['events']),1)
        self.assertEqual(len(body['actions']),2)

    def test_modes_preserve_separate_inputs(self):
        self.request('/api/mode',{'mode':'live'})
        self.request('/api/company',{'name':'My live company'})
        _,demo_state=self.request('/api/mode',{'mode':'demo'})
        self.assertEqual(demo_state['company'],'Meridian Labs')
        _,live_state=self.request('/api/mode',{'mode':'live'})
        self.assertEqual(live_state['company'],'My live company')

    def test_upload_and_duplicate_content(self):
        self.request('/api/mode',{'mode':'live'})
        data={'name':'test.txt','content':base64.b64encode(b'1.1 The agreement begins on 1 January 2026.\n2.1 Payment is due within thirty days.').decode()}
        self.request('/api/upload',data)
        _,body=self.request('/api/upload',data)
        self.assertEqual(len(body['contracts']),6)
        self.assertEqual(len(body['contracts'][-1]['clauses']),2)

    def test_invalid_pdf_does_not_mutate_portfolio(self):
        self.request('/api/mode',{'mode':'live'})
        status,_=self.request('/api/upload',{'name':'broken.pdf','content':base64.b64encode(b'not a PDF').decode()})
        self.assertGreaterEqual(status,400)
        self.assertEqual(len(server.load()['contracts']),5)

    def test_readable_pdf_preserves_source_text_and_page(self):
        self.request('/api/mode',{'mode':'live'})
        stream=b'BT /F1 12 Tf 50 750 Td (1.1 Payment is due within thirty calendar days.) Tj 0 -20 Td (2.1 Termination requires written notice.) Tj ET'
        objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
        raw=b'%PDF-1.4\n';offsets=[0]
        for i,obj in enumerate(objects,1):
            offsets.append(len(raw));raw+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
        xref=len(raw)
        raw+=b'xref\n0 6\n0000000000 65535 f \n'+b''.join(f'{offset:010} 00000 n \n'.encode() for offset in offsets[1:])+b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF\n'
        status,body=self.request('/api/upload',{'name':'readable.pdf','content':base64.b64encode(raw).decode()})
        self.assertEqual(status,200)
        clauses=body['contracts'][-1]['clauses']
        self.assertEqual(len(clauses),2)
        self.assertEqual(clauses[0]['page'],1)
        self.assertIn('Payment is due within thirty calendar days.',clauses[0]['text'])

    def test_foreign_origin_cannot_mutate_state(self):
        status,_=self.request('/api/reset',{},origin='https://untrusted.example')
        self.assertEqual(status,403)

    def test_feedback_settings_are_persistent(self):
        status,body=self.request('/api/settings',{'max_iterations':3,'evidence_threshold':.95,'max_seconds':120})
        self.assertEqual(status,200)
        self.assertEqual(body['settings']['max_iterations'],3)
        self.assertEqual(server.load()['settings']['evidence_threshold'],.95)

    def test_event_stream_queues_automatic_reassessment(self):
        self.request('/api/mode',{'mode':'live'})
        self.request('/api/monitor',{'enabled':True})
        status,body=self.request('/api/event',{'id':'stream','date':'2026-10-25','timestamp':'2026-10-25T10:00:00Z'})
        self.assertEqual(status,200)
        self.assertTrue(body['monitor']['pending'])
        server.patch(lambda s:s['monitor'].update(queued_at=time.time()-3))
        with patch.object(server,'start_analysis',return_value='mock-run') as start:
            server.monitor_tick()
        start.assert_called_once_with(source='event_monitor')

    def test_quota_backoff_prevents_automatic_request_storm(self):
        self.request('/api/mode',{'mode':'live'})
        server.patch(lambda s:s.update(monitor={'enabled':True,'pending':True,'queued_at':0,'blocked_until':time.time()+900}))
        with patch.object(server,'start_analysis') as start:server.monitor_tick()
        start.assert_not_called()

    def test_bad_receipt_reference_cannot_mutate_state(self):
        status,_=self.request('/api/event',{'type':'notice','contract_id':'atlas','clause_id':'northstar-6.1'})
        self.assertEqual(status,400)
        self.assertEqual(server.load()['events'],[])

    def test_hour_clock_and_generalized_origin(self):
        status,body=self.request('/api/clock',{'date':'2027-04-01','timestamp':'2027-04-01T09:30:00Z'})
        self.assertEqual(status,200)
        self.assertEqual(body['as_of_time'],'2027-04-01T09:30:00+00:00')
        self.assertEqual(body['clock_origin'],'2027-04-01')

    def test_complete_contract_report_endpoint(self):
        with urllib.request.urlopen(self.base+'/api/report?contract_id=atlas') as response:report=response.read().decode()
        for heading in ('Key terms and confidence','Recommended actions','References','Financial exposure'):
            self.assertIn(heading,report)

if __name__=='__main__':unittest.main()
