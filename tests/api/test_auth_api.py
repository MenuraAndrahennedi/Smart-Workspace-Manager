from backend.services.auth_service import register_user


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