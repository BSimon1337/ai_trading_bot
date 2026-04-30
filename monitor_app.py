from __future__ import annotations

from tradingbot.app.monitor import create_app, load_monitor_configuration
from tradingbot.config.settings import load_config


APP = create_app()


def _safe_bot_config():
    try:
        return load_config()
    except Exception:
        return None


def main() -> int:
    bot_config = _safe_bot_config()
    try:
        monitor_config = load_monitor_configuration(config=bot_config)
    except TypeError:
        monitor_config = load_monitor_configuration()
    try:
        app = create_app(
            instances=monitor_config.instances,
            config=bot_config,
            recent_control_actions=monitor_config.recent_control_actions,
            refresh_seconds=monitor_config.refresh_seconds,
            refresh_runtime_state=True,
        )
    except TypeError:
        app = create_app(
            instances=monitor_config.instances,
            refresh_seconds=monitor_config.refresh_seconds,
        )
    app.run(host=monitor_config.dashboard_host, port=monitor_config.dashboard_port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
