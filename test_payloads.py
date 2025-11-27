import unittest
from unittest.mock import patch, MagicMock
import json
import os
from main import app, check_filters

class TestGitHubDiscordBridge(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
        # Mock config loading by patching the CONFIG variable in main
        patcher = patch('main.CONFIG', {
            "workflows": [
                {
                    "name": "Test PR",
                    "event": "pull_request",
                    "filters": {"action": "opened", "is_draft": False},
                    "actions": [{"webhook_env": "TEST_WEBHOOK_1", "format": "pr_detailed"}]
                },
                {
                    "name": "Test Issue",
                    "event": "issues",
                    "filters": {"labels_include": ["bug"]},
                    "actions": [{"webhook_env": "TEST_WEBHOOK_2", "format": "issue_priority"}]
                }
            ]
        })
        self.mock_config = patcher.start()
        self.addCleanup(patcher.stop)

    def test_check_filters_pr(self):
        filters = {"action": "opened", "is_draft": False}
        
        # Match
        data = {"action": "opened", "pull_request": {"draft": False}}
        self.assertTrue(check_filters(filters, data, "pull_request"))
        
        # Mismatch action
        data = {"action": "closed", "pull_request": {"draft": False}}
        self.assertFalse(check_filters(filters, data, "pull_request"))
        
        # Mismatch draft
        data = {"action": "opened", "pull_request": {"draft": True}}
        self.assertFalse(check_filters(filters, data, "pull_request"))

    def test_check_filters_issue(self):
        filters = {"labels_include": ["bug", "urgent"]}
        
        # Match one label
        data = {"issue": {"labels": [{"name": "bug"}, {"name": "other"}]}}
        self.assertTrue(check_filters(filters, data, "issues"))
        
        # Match other label
        data = {"issue": {"labels": [{"name": "urgent"}]}}
        self.assertTrue(check_filters(filters, data, "issues"))
        
        # No match
        data = {"issue": {"labels": [{"name": "feature"}]}}
        self.assertFalse(check_filters(filters, data, "issues"))

    @patch('main.requests.post')
    def test_webhook_routing(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Test PR event triggers TEST_WEBHOOK_1
        data = {
            "action": "opened",
            "pull_request": {
                "number": 1,
                "title": "Test PR",
                "html_url": "http://url",
                "body": "body",
                "head": {"ref": "feature"},
                "base": {"ref": "main"},
                "draft": False
            },
            "repository": {"full_name": "test/repo"},
            "sender": {"login": "tester"}
        }
        
        with patch.dict('os.environ', {'TEST_WEBHOOK_1': 'http://webhook1', 'TEST_WEBHOOK_2': 'http://webhook2'}):
            response = self.app.post('/webhook', 
                                     headers={'X-GitHub-Event': 'pull_request'},
                                     data=json.dumps(data),
                                     content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            # Should call webhook 1
            mock_post.assert_called_with('http://webhook1', json=unittest.mock.ANY)

    @patch('main.requests.post')
    def test_webhook_filtering(self, mock_post):
        # Test Issue event without 'bug' label should NOT trigger
        data = {
            "action": "opened",
            "issue": {
                "number": 1,
                "title": "Test Issue",
                "labels": [{"name": "feature"}]
            },
            "repository": {"full_name": "test/repo"},
            "sender": {"login": "tester"}
        }
        
        with patch.dict('os.environ', {'TEST_WEBHOOK_1': 'http://webhook1', 'TEST_WEBHOOK_2': 'http://webhook2'}):
            response = self.app.post('/webhook', 
                                     headers={'X-GitHub-Event': 'issues'},
                                     data=json.dumps(data),
                                     content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            mock_post.assert_not_called()

if __name__ == '__main__':
    unittest.main()
