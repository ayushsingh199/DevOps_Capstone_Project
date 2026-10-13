"""Operational endpoints used by Kubernetes probes, Prometheus and the UI."""


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_checks_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}


def test_info_exposes_build_version(client):
    body = client.get("/api/info").json()
    assert body["version"] == "test-sha"
    assert body["service"] == "MediSlot API"


def test_metrics_endpoint_is_prometheus_format(client):
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "http_requests_total" in response.text
    assert "medislot_appointments_booked_total" in response.text


def test_responses_carry_request_id(client):
    response = client.get("/api/doctors", headers={"x-request-id": "abc123"})
    assert response.headers["x-request-id"] == "abc123"
