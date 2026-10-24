"""Hosted startup must not overwrite an existing workspace."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launch import prepare_demo, start_command
from store import Store


class LaunchTests(unittest.TestCase):
    def test_demo_startup_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'demo.db')
            with patch.dict(os.environ, BRANDSHIELD_DB=path, BRANDSHIELD_DEMO_MODE='true'):
                prepare_demo()
                store = Store()
                self.assertIsNotNone(store.authenticate('creator', 'BrandShield!2026'))
                self.assertEqual(len(store.list_reviews('creator')), 2)
                prepare_demo()
                self.assertEqual(len(store.list_reviews('creator')), 2)

    def test_disabled_mode_does_not_create_users(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, BRANDSHIELD_DB=str(Path(directory)/'app.db'), BRANDSHIELD_DEMO_MODE='false'):
                prepare_demo()
                self.assertFalse(Store().has_users())

    def test_demo_does_not_replace_existing_accounts(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, BRANDSHIELD_DB=str(Path(directory)/'app.db'), BRANDSHIELD_DEMO_MODE='true'):
                store = Store()
                store.bootstrap('my-private-admin!')
                prepare_demo()
                self.assertIsNotNone(store.authenticate('admin', 'my-private-admin!'))
                self.assertIsNone(store.authenticate('creator', 'BrandShield!2026'))

    def test_host_command_uses_assigned_port(self):
        with patch.dict(os.environ, PORT='10000'):
            command = start_command()
            self.assertIn('10000', command)
            self.assertIn('0.0.0.0', command)
            self.assertEqual(command[:3], [sys.executable, '-m', 'streamlit'])


if __name__ == '__main__':
    unittest.main()
