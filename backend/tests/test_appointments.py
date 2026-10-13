"""Appointment CRUD, validation, double-booking protection and stats."""

from datetime import datetime, timedelta


def _create(client, payload):
    response = client.post("/api/appointments", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_appointment(client, booking):
    body = _create(client, booking)
    assert body["status"] == "scheduled"
    assert body["doctor"]["full_name"] == "Dr. Test Heart"
    assert body["patient_name"] == "Rahul Verma"


def test_get_appointment_by_id(client, booking):
    created = _create(client, booking)
    response = client.get(f"/api/appointments/{created['id']}")
    assert response.status_code == 200
    assert response.json()["reason"] == "Annual check-up"


def test_list_appointments_with_filters(client, booking, tomorrow_10am):
    _create(client, booking)
    later = tomorrow_10am + timedelta(hours=2)
    _create(client, booking | {"doctor_id": 2, "scheduled_at": later.isoformat()})

    assert len(client.get("/api/appointments").json()) == 2
    assert len(client.get("/api/appointments", params={"doctor_id": 2}).json()) == 1
    assert len(client.get("/api/appointments", params={"q": "rahul"}).json()) == 2
    assert client.get("/api/appointments", params={"status": "completed"}).json() == []
    day = tomorrow_10am.date().isoformat()
    assert len(client.get("/api/appointments", params={"date": day}).json()) == 2


def test_update_appointment_status_and_reschedule(client, booking, tomorrow_10am):
    created = _create(client, booking)
    new_time = (tomorrow_10am + timedelta(hours=3)).isoformat()
    response = client.put(
        f"/api/appointments/{created['id']}",
        json={"status": "checked_in", "scheduled_at": new_time},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "checked_in"
    assert datetime.fromisoformat(body["scheduled_at"]).hour == 13


def test_delete_appointment(client, booking):
    created = _create(client, booking)
    assert client.delete(f"/api/appointments/{created['id']}").status_code == 204
    assert client.get(f"/api/appointments/{created['id']}").status_code == 404


def test_double_booking_is_rejected(client, booking, tomorrow_10am):
    _create(client, booking)
    overlapping = (tomorrow_10am + timedelta(minutes=15)).isoformat()
    response = client.post(
        "/api/appointments", json=booking | {"patient_name": "Other", "scheduled_at": overlapping}
    )
    assert response.status_code == 409
    assert "already booked" in response.json()["detail"]


def test_back_to_back_slots_are_allowed(client, booking, tomorrow_10am):
    _create(client, booking)
    next_slot = (tomorrow_10am + timedelta(minutes=30)).isoformat()
    _create(client, booking | {"scheduled_at": next_slot})


def test_cancelled_slot_can_be_rebooked(client, booking):
    created = _create(client, booking)
    client.put(f"/api/appointments/{created['id']}", json={"status": "cancelled"})
    _create(client, booking | {"patient_name": "Walk-in Patient"})


def test_validation_errors_return_422(client, booking):
    bad_phone = client.post("/api/appointments", json=booking | {"patient_phone": "call me"})
    too_long = client.post("/api/appointments", json=booking | {"duration_minutes": 500})
    bad_status = client.put("/api/appointments/1", json={"status": "teleported"})
    assert bad_phone.status_code == too_long.status_code == bad_status.status_code == 422


def test_booking_unknown_doctor_returns_404(client, booking):
    response = client.post("/api/appointments", json=booking | {"doctor_id": 42})
    assert response.status_code == 404


def test_update_missing_appointment_returns_404(client):
    assert client.put("/api/appointments/123", json={"status": "completed"}).status_code == 404


def test_stats_aggregate_dashboard_kpis(client, booking, tomorrow_10am):
    first = _create(client, booking)
    second = _create(
        client, booking | {"scheduled_at": (tomorrow_10am + timedelta(hours=1)).isoformat()}
    )
    client.put(f"/api/appointments/{first['id']}", json={"status": "completed"})
    client.put(f"/api/appointments/{second['id']}", json={"status": "no_show"})
    _create(client, booking | {"doctor_id": 2})

    stats = client.get("/api/appointments/stats").json()
    assert stats["total"] == 3
    assert stats["upcoming"] == 1
    assert stats["by_status"]["completed"] == 1
    assert stats["completion_rate"] == 50.0
    assert stats["doctor_load"][0] == {
        "doctor_id": 2,
        "full_name": "Dr. Test Bone",
        "specialty": "Orthopaedics",
        "active_appointments": 1,
    }
