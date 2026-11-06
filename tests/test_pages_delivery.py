"""Exercise real Pages retry decisions without a network or credentials."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    'publisher', Path(__file__).resolve().parents[1]/'scripts/v2/publish.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PagesDeliveryTests(unittest.TestCase):
    def test_already_served_does_not_request_a_build(self):
        request = Mock()
        result = publisher.deliver_source_pages(lambda: {'status':'verified'}, request)
        self.assertEqual(result, {'status':'verified', 'pages_attempts':[]})
        request.assert_not_called()

    def test_transient_timeout_retries_same_release(self):
        mismatch = ValueError('Pages does not serve this release: data/release.json')
        verify = Mock(side_effect=[mismatch, mismatch])
        request = Mock(side_effect=[{'status':'already_building'}, {'status':'requested'}])
        wait = Mock(side_effect=[mismatch, {'status':'verified','release_id':'exact'}])
        result = publisher.deliver_source_pages(verify, request, wait)
        self.assertEqual(result['release_id'], 'exact')
        self.assertEqual([row['verified'] for row in result['pages_attempts']], [False,True])
        self.assertEqual(request.call_count,2)
        self.assertEqual([c.args for c in wait.call_args_list],[(verify,),(verify,)])

    def test_changed_local_bytes_never_request_a_build(self):
        request = Mock()
        with self.assertRaisesRegex(ValueError,'local files changed'):
            publisher.deliver_source_pages(
                Mock(side_effect=ValueError('Rebuild the receipt; local files changed')), request)
        request.assert_not_called()

    @patch.dict('os.environ', {'ORACLE_PAGES_BUILD_TOKEN':'fixture'})
    def test_exact_active_deployment_is_not_duplicated(self):
        response = io.BytesIO(json.dumps({'commit':'same','status':'building'}).encode())
        opener = Mock(return_value=response)
        self.assertEqual(publisher.request_public_pages_build(opener,commit='same'),
                         {'status':'already_building'})
        self.assertEqual(opener.call_count,1)
        self.assertEqual(opener.call_args.args[0].get_method(),'GET')
