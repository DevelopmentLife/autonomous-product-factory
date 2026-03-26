import pytest
from apf_orchestrator.core.auth import (
    hash_password, verify_password, create_access_token, decode_token
)

SECRET = 'test-secret'
ALGO = 'HS256'


def test_hash_and_verify_password():
    hashed = hash_password('mypassword')
    assert verify_password('mypassword', hashed) is True


def test_wrong_password_fails_verify():
    hashed = hash_password('correct')
    assert verify_password('wrong', hashed) is False


def test_create_and_decode_token():
    token = create_access_token({'sub': 'user-1', 'email': 'a@b.com'}, SECRET, ALGO, 60)
    payload = decode_token(token, SECRET, ALGO)
    assert payload['sub'] == 'user-1'
    assert payload['email'] == 'a@b.com'


def test_token_contains_expiry():
    from jose import jwt
    token = create_access_token({'sub': 'user-1'}, SECRET, ALGO, 60)
    payload = jwt.decode(token, SECRET, algorithms=[ALGO])
    assert 'exp' in payload
