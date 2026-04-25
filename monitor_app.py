from __future__ import annotations

from tradingbot.app.monitor import create_app, load_monitor_configuration


APP = create_app()


def main() -> int:
    config = load_monitor_configuration()
    app = create_app(instances=config.instances, refresh_seconds=config.refresh_seconds)
    app.run(host=config.dashboard_host, port=config.dashboard_port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
