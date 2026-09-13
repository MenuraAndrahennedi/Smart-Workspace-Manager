from backend.services.auth_service import authenticate_user, hash_password, register_user, verify_password


def test_hash_password_does_not_store_plain_password():
    hashed = hash_password("Secret123!")

    assert hashed != "Secret123!"
    assert verify_password("Secret123!", hashed)
    assert not verify_password("WrongPassword", hashed)


def test_register_user_normalizes_email(test_session):
    user = register_user(test_session, "USER@Example.COM ", "Secret123!")

    assert user.email == "user@example.com"
    assert verify_password("Secret123!", user.password_hash)


def test_authenticate_user_returns_user_for_valid_credentials(test_session):
    register_user(test_session, "user@example.com", "Secret123!")

    user = authenticate_user(test_session, "USER@example.com", "Secret123!")

    assert user is not None
    assert user.email == "user@example.com"