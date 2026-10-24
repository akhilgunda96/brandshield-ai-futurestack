"""SQLite repository; role and state checks live here, not just in the UI."""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from brands import SECOND_PROFILE
from engine import DEFAULT_PROFILE, analyse, validate_profile

ROLES = ('creator', 'reviewer', 'manager', 'admin')


class Store:
    def __init__(self, path=None):
        self.path = str(
            path or os.environ.get('BRANDSHIELD_DB', 'data/brandshield.sqlite3')
        )
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as connection:
            connection.executescript('''
            CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, salt TEXT NOT NULL, hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS profiles(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, body TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, title TEXT NOT NULL, creator TEXT NOT NULL, profile_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'Draft', version INTEGER NOT NULL DEFAULT 1, updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY, review_id INTEGER NOT NULL, version INTEGER NOT NULL, content TEXT NOT NULL, profile TEXT NOT NULL, findings TEXT NOT NULL, actor TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(review_id,version));
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, review_id INTEGER NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, note TEXT NOT NULL, version INTEGER NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            ''')
            if not connection.execute('SELECT 1 FROM profiles').fetchone():
                connection.execute(
                    'INSERT INTO profiles(name,body) VALUES(?,?)',
                    (DEFAULT_PROFILE['name'], json.dumps(DEFAULT_PROFILE)),
                )
            # One-time, non-destructive addition for new and existing installations.
            connection.execute(
                'CREATE TABLE IF NOT EXISTS migrations(key TEXT PRIMARY KEY)'
            )
            if not connection.execute(
                "SELECT 1 FROM migrations WHERE key='novawear-demo-v1'"
            ).fetchone():
                validate_profile(SECOND_PROFILE)
                connection.execute(
                    'INSERT OR IGNORE INTO profiles(name,body) VALUES(?,?)',
                    (SECOND_PROFILE['name'], json.dumps(SECOND_PROFILE)),
                )
                connection.execute(
                    "INSERT INTO migrations(key) VALUES('novawear-demo-v1')"
                )

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('BEGIN IMMEDIATE')
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def digest(password, salt):
        return hashlib.pbkdf2_hmac(
            'sha256', password.encode(), bytes.fromhex(salt), 260000
        ).hex()

    def bootstrap(self, password):
        if len(password) < 12:
            raise ValueError('Use at least 12 characters.')
        with self.db() as connection:
            if connection.execute('SELECT 1 FROM users').fetchone():
                raise ValueError('Setup is already complete.')
            self._user(connection, 'admin', 'Administrator', 'admin', password)

    def _user(self, connection, username, name, role, password):
        if (
            role not in ROLES
            or len(password) < 12
            or not username.strip()
            or not name.strip()
        ):
            raise ValueError(
                'Supply a username, display name, valid role and password of at least 12 characters.'
            )
        salt = secrets.token_hex(16)
        connection.execute(
            'INSERT INTO users VALUES(?,?,?,?,?)',
            (username.strip(), name.strip(), role, salt, self.digest(password, salt)),
        )

    def add_user(self, actor, username, name, role, password):
        with self.db() as connection:
            self._actor(connection, actor, ('admin',))
            self._user(connection, username, name, role, password)

    def has_users(self):
        with self.db() as connection:
            return bool(connection.execute('SELECT 1 FROM users').fetchone())

    def authenticate(self, username, password):
        with self.db() as connection:
            row = connection.execute(
                'SELECT * FROM users WHERE username=?', (username,)
            ).fetchone()
            if row and hmac.compare_digest(
                self.digest(password, row['salt']), row['hash']
            ):
                return dict(
                    username=row['username'], name=row['name'], role=row['role']
                )
        return None

    def _actor(self, connection, actor, roles=ROLES):
        row = connection.execute(
            'SELECT username,role FROM users WHERE username=?', (actor,)
        ).fetchone()
        if not row or row['role'] not in roles:
            raise PermissionError('You do not have permission for this action.')
        return row

    def profiles(self):
        with self.db() as connection:
            return [
                dict(profile_row)
                for profile_row in connection.execute(
                    'SELECT * FROM profiles ORDER BY name'
                )
            ]

    def save_profile(self, actor, body, pid=None):
        validate_profile(body)
        with self.db() as connection:
            self._actor(connection, actor, ('manager', 'admin'))
            if pid:
                if not connection.execute(
                    'SELECT 1 FROM profiles WHERE id=?', (pid,)
                ).fetchone():
                    raise ValueError('Profile not found.')
                connection.execute(
                    'UPDATE profiles SET name=?,body=?,version=version+1 WHERE id=?',
                    (body['name'], json.dumps(body), pid),
                )
            else:
                connection.execute(
                    'INSERT INTO profiles(name,body) VALUES(?,?)',
                    (body['name'], json.dumps(body)),
                )

    def _event(self, connection, rid, actor, action, note, version):
        connection.execute(
            'INSERT INTO events(review_id,actor,action,note,version) VALUES(?,?,?,?,?)',
            (rid, actor, action, note, version),
        )

    def create(self, actor, title, text, pid):
        if not title.strip() or len(title) > 180:
            raise ValueError('Use a title of 1–180 characters.')
        with self.db() as connection:
            self._actor(connection, actor, ('creator', 'admin'))
            profile_row = connection.execute(
                'SELECT body FROM profiles WHERE id=?', (pid,)
            ).fetchone()
            if not profile_row:
                raise ValueError('Profile not found.')
            profile = json.loads(profile_row['body'])
            findings = analyse(text, profile)
            rid = connection.execute(
                'INSERT INTO reviews(title,creator,profile_id) VALUES(?,?,?)',
                (title.strip(), actor, pid),
            ).lastrowid
            connection.execute(
                'INSERT INTO revisions(review_id,version,content,profile,findings,actor) VALUES(?,1,?,?,?,?)',
                (rid, text, profile_row['body'], json.dumps(findings), actor),
            )
            self._event(connection, rid, actor, 'Created', 'Initial analysis', 1)
            return rid

    def _review(self, connection, actor, rid):
        user = self._actor(connection, actor)
        review = connection.execute(
            'SELECT * FROM reviews WHERE id=?', (rid,)
        ).fetchone()
        if not review:
            raise ValueError('Review not found.')
        if user['role'] == 'creator' and review['creator'] != actor:
            raise PermissionError('Creators can access only their own reviews.')
        return review

    def list_reviews(self, actor):
        with self.db() as connection:
            user = self._actor(connection, actor)
            query = 'SELECT * FROM reviews'
            parameters = ()

            if user['role'] == 'creator':
                query += ' WHERE creator = ?'
                parameters = (actor,)

            query += ' ORDER BY updated DESC, id DESC'
            rows = connection.execute(query, parameters)
            return [dict(row) for row in rows]

    def detail(self, actor, rid):
        with self.db() as connection:
            review = dict(self._review(connection, actor, rid))
            review['revisions'] = [
                dict(row)
                for row in connection.execute(
                    'SELECT * FROM revisions WHERE review_id=? ORDER BY version DESC',
                    (rid,),
                )
            ]
            for revision in review['revisions']:
                revision['profile'] = json.loads(revision['profile'])
                revision['findings'] = json.loads(revision['findings'])
            review['events'] = [
                dict(row)
                for row in connection.execute(
                    'SELECT * FROM events WHERE review_id=? ORDER BY id DESC', (rid,)
                )
            ]
            return review

    def revise(self, actor, rid, text, expected):
        with self.db() as connection:
            review = self._review(connection, actor, rid)
            if review['creator'] != actor or review['status'] not in (
                'Draft',
                'Changes requested',
            ):
                raise PermissionError('Only the creator may revise an editable review.')
            if review['version'] != expected:
                raise ValueError('A newer revision exists. Reload this review.')
            prior = connection.execute(
                'SELECT profile FROM revisions WHERE review_id=? AND version=?',
                (rid, expected),
            ).fetchone()
            findings = analyse(text, json.loads(prior['profile']))
            version = expected + 1
            connection.execute(
                'INSERT INTO revisions(review_id,version,content,profile,findings,actor) VALUES(?,?,?,?,?,?)',
                (rid, version, text, prior['profile'], json.dumps(findings), actor),
            )
            connection.execute(
                "UPDATE reviews SET version=?,status='Draft',updated=CURRENT_TIMESTAMP WHERE id=?",
                (version, rid),
            )
            self._event(
                connection,
                rid,
                actor,
                'Revised',
                'Content saved and checked again against the original profile snapshot.',
                version,
            )

    def finding_decision(self, actor, rid, fid, decision, note, expected):
        if decision not in ('Dismissed', 'Open'):
            raise ValueError('Invalid finding decision.')
        if decision == 'Dismissed' and not note.strip():
            raise ValueError('A reason is required to dismiss a finding.')
        with self.db() as connection:
            review = self._review(connection, actor, rid)
            if actor != review['creator'] or review['status'] not in (
                'Draft',
                'Changes requested',
            ):
                raise PermissionError(
                    'Only the creator may change findings on an editable review.'
                )
            if expected != review['version']:
                raise ValueError('A newer revision exists. Reload.')
            row = connection.execute(
                'SELECT id,findings FROM revisions WHERE review_id=? AND version=?',
                (rid, expected),
            ).fetchone()
            findings = json.loads(row['findings'])
            finding = next(
                (finding for finding in findings if finding['id'] == fid), None
            )
            if not finding:
                raise ValueError('Finding not found.')
            finding['status'] = decision
            connection.execute(
                'UPDATE revisions SET findings=? WHERE id=?',
                (json.dumps(findings), row['id']),
            )
            self._event(
                connection,
                rid,
                actor,
                decision,
                finding["affected"] + ': ' + note,
                expected,
            )

    def transition(self, actor, rid, action, note, expected):
        with self.db() as connection:
            review = self._review(connection, actor, rid)
            user = self._actor(connection, actor)
            if expected != review['version']:
                raise ValueError('A newer revision exists. Reload.')
            if action == 'Submit':
                if review['creator'] != actor or review['status'] not in (
                    'Draft',
                    'Changes requested',
                ):
                    raise PermissionError(
                        'Only an editable review can be submitted by its creator.'
                    )
                status = 'Pending review'
            elif action in ('Approve', 'Request changes'):
                if (
                    user['role'] not in ('reviewer', 'manager', 'admin')
                    or actor == review['creator']
                    or review['status'] != 'Pending review'
                ):
                    raise PermissionError(
                        'A separate authorised reviewer must decide a pending review.'
                    )
                if not note.strip():
                    raise ValueError('Record a decision explanation.')
                status = 'Approved' if action == 'Approve' else 'Changes requested'
            else:
                raise ValueError('Invalid action.')
            connection.execute(
                'UPDATE reviews SET status=?,updated=CURRENT_TIMESTAMP WHERE id=?',
                (status, rid),
            )
            self._event(connection, rid, actor, action, note, review['version'])

    def comment(self, actor, rid, note):
        if not note.strip() or len(note) > 5000:
            raise ValueError('Comments must contain 1–5,000 characters.')
        with self.db() as connection:
            review = self._review(connection, actor, rid)
            self._event(
                connection, rid, actor, 'Comment', note.strip(), review['version']
            )
