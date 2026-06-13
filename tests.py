#!/usr/bin/env python
from datetime import datetime, timezone, timedelta
import unittest
from app import create_app, db
from app.models import User, Post
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    ELASTICSEARCH_URL = None


class UserModelCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username='susan', email='susan@example.com')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_avatar(self):
        u = User(username='john', email='john@example.com')
        self.assertEqual(u.avatar(128), ('https://www.gravatar.com/avatar/'
                                         'd4c74594d841139328695756648b6bd6'
                                         '?d=identicon&s=128'))

    def test_follow(self):
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        following = db.session.scalars(u1.following.select()).all()
        followers = db.session.scalars(u2.followers.select()).all()
        self.assertEqual(following, [])
        self.assertEqual(followers, [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.following_count(), 1)
        self.assertEqual(u2.followers_count(), 1)
        u1_following = db.session.scalars(u1.following.select()).all()
        u2_followers = db.session.scalars(u2.followers.select()).all()
        self.assertEqual(u1_following[0].username, 'susan')
        self.assertEqual(u2_followers[0].username, 'john')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.following_count(), 0)
        self.assertEqual(u2.followers_count(), 0)

    def test_follow_posts(self):
        # create four users
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        u3 = User(username='mary', email='mary@example.com')
        u4 = User(username='david', email='david@example.com')
        db.session.add_all([u1, u2, u3, u4])

        # create four posts
        now = datetime.now(timezone.utc)
        p1 = Post(body="post from john", author=u1,
                  timestamp=now + timedelta(seconds=1))
        p2 = Post(body="post from susan", author=u2,
                  timestamp=now + timedelta(seconds=4))
        p3 = Post(body="post from mary", author=u3,
                  timestamp=now + timedelta(seconds=3))
        p4 = Post(body="post from david", author=u4,
                  timestamp=now + timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # setup the followers
        u1.follow(u2)  # john follows susan
        u1.follow(u4)  # john follows david
        u2.follow(u3)  # susan follows mary
        u3.follow(u4)  # mary follows david
        db.session.commit()

        # check the following posts of each user
        f1 = db.session.scalars(u1.following_posts()).all()
        f2 = db.session.scalars(u2.following_posts()).all()
        f3 = db.session.scalars(u3.following_posts()).all()
        f4 = db.session.scalars(u4.following_posts()).all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])


class APITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_user(self, username='john', email='john@example.com',
                     password='cat'):
        u = User(username=username, email=email)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        return u

    def _get_token(self, username, password):
        response = self.client.post(
            '/api/tokens',
            headers={'Authorization': 'Basic ' +
                     (username + ':' + password).encode('base64').decode()
                     .strip()})
        return response.get_json()['token']

    def _auth_header(self, token):
        return {'Authorization': 'Bearer ' + token}

    # --- create_user (POST /api/users) tests ---

    def test_create_user_valid_json(self):
        """POST /api/users with valid JSON should create user and return 201."""
        response = self.client.post(
            '/api/users',
            json={'username': 'john', 'email': 'john@example.com',
                  'password': 'cat'})
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['username'], 'john')

    def test_create_user_no_content_type(self):
        """POST /api/users without JSON Content-Type should return 4xx, not 500."""
        response = self.client.post(
            '/api/users',
            data='{"username": "john", "email": "john@example.com", '
                 '"password": "cat"}')
        # 415 Unsupported Media Type from Werkzeug, or 400 from our check
        self.assertIn(response.status_code, [400, 415])
        data = response.get_json()
        self.assertIn('error', data)

    def test_create_user_empty_body(self):
        """POST /api/users with empty body should return 400, not 500."""
        response = self.client.post(
            '/api/users',
            content_type='application/json',
            data='')
        self.assertEqual(response.status_code, 400)

    def test_create_user_invalid_json(self):
        """POST /api/users with malformed JSON should return 400, not 500."""
        response = self.client.post(
            '/api/users',
            content_type='application/json',
            data='{invalid json}')
        self.assertEqual(response.status_code, 400)

    def test_create_user_missing_fields(self):
        """POST /api/users with missing required fields should return 400."""
        response = self.client.post(
            '/api/users',
            json={'username': 'john'})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('must include', data['message'])

    # --- update_user (PUT /api/users/<id>) tests ---

    def test_update_user_valid_json(self):
        """PUT /api/users/<id> with valid JSON should update user."""
        u = self._create_user()
        token = u.get_token()
        db.session.commit()
        response = self.client.put(
            '/api/users/{}'.format(u.id),
            headers=self._auth_header(token),
            json={'username': 'john_updated'})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['username'], 'john_updated')

    def test_update_user_no_content_type(self):
        """PUT /api/users/<id> without JSON Content-Type should return 4xx, not 500."""
        u = self._create_user()
        token = u.get_token()
        db.session.commit()
        response = self.client.put(
            '/api/users/{}'.format(u.id),
            headers=self._auth_header(token),
            data='{"username": "john_updated"}')
        # 415 Unsupported Media Type from Werkzeug, or 400 from our check
        self.assertIn(response.status_code, [400, 415])
        data = response.get_json()
        self.assertIn('error', data)

    def test_update_user_empty_body(self):
        """PUT /api/users/<id> with empty body should return 400, not 500."""
        u = self._create_user()
        token = u.get_token()
        db.session.commit()
        response = self.client.put(
            '/api/users/{}'.format(u.id),
            headers=self._auth_header(token),
            content_type='application/json',
            data='')
        self.assertEqual(response.status_code, 400)

    def test_update_user_invalid_json(self):
        """PUT /api/users/<id> with malformed JSON should return 400, not 500."""
        u = self._create_user()
        token = u.get_token()
        db.session.commit()
        response = self.client.put(
            '/api/users/{}'.format(u.id),
            headers=self._auth_header(token),
            content_type='application/json',
            data='{invalid json}')
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main(verbosity=2)
