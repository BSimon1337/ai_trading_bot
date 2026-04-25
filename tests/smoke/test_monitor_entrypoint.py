from __future__ import annotations

import monitor_app


def test_monitor_app_root_entrypoint_exposes_app():
    assert monitor_app.APP is not None
    assert monitor_app.APP.test_client().get("/health").status_code == 200


def test_monitor_dashboard_renders_no_data_state():
    client = monitor_app.create_app(instances=()).test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Trading Bot Monitor" in response.data
    assert b"No monitored instances" in response.data
