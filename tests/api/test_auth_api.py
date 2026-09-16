from backend.services.auth_service import register_user


def test_register_creates_user_and_returns_bearer_token(
    unauthenticated_client,
    test_session,
):
    response = unauthenticated_client.post(
        "/api/auth/register",
        json={
            "email": "NEW@Example.com",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_register_rejects_duplicate_email(
    unauthenticated_client,
    test_session,
):
    register_user(test_session, "user@example.com", "Secret123!")

    response = unauthenticated_client.post(
        "/api/auth/register",
        json={
            "email": "USER@example.com",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "User with this email already exists."


def test_register_validates_email_and_password(unauthenticated_client):
    response = unauthenticated_client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "short"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "Validation Error"


def test_login_return_bearer_token(client, test_session):
    register_user(test_session, "uers@example.com", "Secret123!")

    response = client.post(
        "/api/auth/login",
        data={
            "username": "uers@example.com",
            "password": "Secret123!",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_rejects_invalid_password(client, test_session):
    register_user(test_session, "user@example.com", "Secret123!")

    response = client.post(
        "/api/auth/login",
        data={
            "username": "user@example.com",
            "password": "wrong",
        },
    )

    assert response.status_code == 401


def test_token_allows_access_to_protected_route(unauthenticated_client, test_session):
    register_user(test_session, "user@example.com", "Secret123!")

    login_response = unauthenticated_client.post(
        "/api/auth/login",
        data={
            "username": "user@example.com",
            "password": "Secret123!",
        },
    )

    token = login_response.json()["access_token"]

    response = unauthenticated_client.get(
        "/api/files/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

def test_invalid_token_is_rejected(unauthenticated_client):
    response = unauthenticated_client.get(
        "/api/files/",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
