"""Doctor endpoints."""


def test_list_doctors_returns_seeded_roster(client):
    response = client.get("/api/doctors")
    assert response.status_code == 200
    assert [d["full_name"] for d in response.json()] == ["Dr. Test Bone", "Dr. Test Heart"]


def test_create_and_fetch_doctor(client):
    created = client.post(
        "/api/doctors",
        json={"full_name": "Dr. New Joiner", "specialty": "ENT", "room": "E-1"},
    )
    assert created.status_code == 201
    doctor_id = created.json()["id"]
    assert client.get(f"/api/doctors/{doctor_id}").json()["specialty"] == "ENT"


def test_unknown_doctor_returns_404(client):
    response = client.get("/api/doctors/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Doctor 999 not found"


def test_cannot_delete_doctor_with_appointments(client, booking):
    client.post("/api/appointments", json=booking)
    response = client.delete("/api/doctors/1")
    assert response.status_code == 409


def test_delete_doctor_without_history(client):
    assert client.delete("/api/doctors/2").status_code == 204
    assert client.get("/api/doctors/2").status_code == 404
