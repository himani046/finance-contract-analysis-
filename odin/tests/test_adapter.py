import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import agents


class AdapterTests(unittest.TestCase):
    def test_missing_key_never_sends_request(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}), patch.object(agents.urllib.request, 'urlopen') as request:
            with self.assertRaisesRegex(agents.AgentError, 'key is missing'):
                agents.check_connection()
        request.assert_not_called()

    def test_quota_error_retries_are_bounded_and_clear(self):
        error = urllib.error.HTTPError('https://example.invalid', 429, 'quota', {}, None)
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'unit-test-key'}), patch.object(agents.urllib.request, 'urlopen', side_effect=error) as request, patch.object(agents.time, 'sleep'):
            with self.assertRaisesRegex(agents.AgentError, 'quota or rate limit reached'):
                agents.request_json('/models')
        self.assertEqual(request.call_count, 3)

    def test_authentication_error_is_not_retried(self):
        error = urllib.error.HTTPError('https://example.invalid', 401, 'unauthorized', {}, None)
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'unit-test-key'}), patch.object(agents.urllib.request, 'urlopen', side_effect=error) as request:
            with self.assertRaisesRegex(agents.AgentError, 'authentication failed'):
                agents.request_json('/models')
        self.assertEqual(request.call_count, 1)

    def test_billing_error_is_clear_and_not_retried(self):
        error=urllib.error.HTTPError('https://example.invalid',402,'payment required',{},None)
        with patch.dict(os.environ,{'GEMINI_API_KEY':'unit-test-key'}),patch.object(agents.urllib.request,'urlopen',side_effect=error) as request:
            with self.assertRaisesRegex(agents.AgentError,'billing or credits'):
                agents.request_json('/models')
        self.assertEqual(request.call_count,1)

    def test_key_is_a_header_and_never_in_prompt_or_url(self):
        response = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'thought': True, 'text': 'private reasoning'}, {'text': json.dumps({'summary': 'Plan', 'workstreams': []})}]}}], 'usageMetadata': {'totalTokenCount': 21}}
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'unit-test-key'}), patch.object(agents.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as request:
            result, tokens = agents.call_agent('Odin', {'company': 'Synthetic test'}, 'gemini-3.6-flash')
        sent = request.call_args.args[0]
        self.assertEqual(sent.get_header('X-goog-api-key'), 'unit-test-key')
        self.assertNotIn('unit-test-key', sent.full_url)
        self.assertNotIn('unit-test-key', sent.data.decode())
        self.assertEqual(result['summary'], 'Plan')
        self.assertEqual(tokens, 21)

    def test_truncated_generation_is_never_accepted(self):
        response = {'candidates': [{'finishReason': 'MAX_TOKENS', 'content': {'parts': [{'text': '{}'}]}}]}
        with patch.object(agents, 'request_json', return_value=response):
            with self.assertRaisesRegex(agents.AgentError, 'incomplete response'):
                agents.call_agent('Odin', {}, 'gemini-3.6-flash')

    def test_generations_are_paced_without_delaying_cache_logic(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':'unit-test-key','GEMINI_MIN_INTERVAL_SECONDS':'15'}), patch.object(agents,'_LAST_GENERATION',100), patch.object(agents.time,'monotonic',return_value=105), patch.object(agents.time,'sleep') as sleep, patch.object(agents.urllib.request,'urlopen',return_value=io.BytesIO(b'{}')):
            agents.request_json('/models/example:generateContent',{})
        sleep.assert_called_once_with(10)


if __name__ == '__main__':
    unittest.main()
