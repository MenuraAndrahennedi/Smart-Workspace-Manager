def test_public_settings_returns_only_frontend_safe_configuration(
    unauthenticated_client,
):
    response = unauthenticated_client.get("/api/settings/public")

    assert response.status_code == 200
    data = response.json()
    assert data["max_upload_size_mb"] > 0
    assert "csv" in data["supported_file_types"]
    assert "spreadsheets" in data["organizer_categories"]
    assert "database_url" not in data
    assert "secret_key" not in data
    assert "storage_provider" not in data
