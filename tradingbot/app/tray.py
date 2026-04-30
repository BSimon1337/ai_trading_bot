from __future__ import annotations

import argparse
import webbrowser
from dataclasses import dataclass, field
from typing import Any, Callable

from tradingbot.app.monitor import (
    MonitorConfiguration,
    TrayState,
    create_app,
    dashboard_status,
    load_monitor_configuration,
)
from tradingbot.config.settings import load_config


TRAY_MENU_ACTIONS = ("Open Dashboard", "Refresh Status", "Exit Monitor")
TRAY_READ_ONLY_MESSAGE = "Sentiment monitoring remains read-only."
TRAY_STATE_META = {
    "failed": ("AI Trading Bot Monitor (Critical)", "Critical monitor issue detected.", "#C0392B"),
    "blocked": ("AI Trading Bot Monitor (Blocked)", "A live safeguard blocked execution.", "#D35400"),
    "stale": ("AI Trading Bot Monitor (Stale)", "Monitor evidence is stale.", "#F39C12"),
    "no_data": ("AI Trading Bot Monitor (No Data)", "No runtime evidence found yet.", "#7F8C8D"),
    "live": ("AI Trading Bot Monitor (Live)", "Live evidence is updating.", "#27AE60"),
    "paper": ("AI Trading Bot Monitor (Paper)", "Paper evidence is updating.", "#2980B9"),
    "running": ("AI Trading Bot Monitor (Running)", "Monitor evidence is updating.", "#16A085"),
    "stopped": ("AI Trading Bot Monitor (Stopped)", "Managed runtimes are stopped.", "#7F8C8D"),
    "paused": ("AI Trading Bot Monitor (Paused)", "A managed runtime is paused.", "#F39C12"),
    "unavailable": ("AI Trading Bot Monitor", "Tray monitor is unavailable.", "#7F8C8D"),
}


@dataclass(frozen=True)
class TrayDependencies:
    available: bool
    reason: str = ""
    pystray: Any | None = None
    image_module: Any | None = None
    image_draw_module: Any | None = None


@dataclass
class TrayController:
    config: MonitorConfiguration = field(default_factory=load_monitor_configuration)
    payload_loader: Callable[[], dict[str, Any]] | None = None
    browser_opener: Callable[[str], Any] = webbrowser.open
    state: TrayState = field(default_factory=TrayState)
    dependencies: TrayDependencies = field(default_factory=lambda: load_tray_dependencies())
    icon: Any | None = None
    exit_requested: bool = False

    def refresh_status(self) -> TrayState:
        payload = self.payload_loader() if self.payload_loader is not None else dashboard_status(self.config.instances)
        self.state = tray_state_from_dashboard(payload)
        if self.icon is not None:
            if hasattr(self.icon, "title"):
                self.icon.title = self.state.tooltip
            if hasattr(self.icon, "icon") and self.dependencies.available:
                self.icon.icon = create_tray_image(
                    self.state,
                    image_module=self.dependencies.image_module,
                    image_draw_module=self.dependencies.image_draw_module,
                )
        return self.state

    def open_dashboard(self) -> str:
        url = build_dashboard_url(self.config)
        self.browser_opener(url)
        return url

    def exit_monitor(self) -> None:
        self.exit_requested = True
        if self.icon is not None and hasattr(self.icon, "stop"):
            self.icon.stop()

    def build_menu_model(self) -> tuple[dict[str, Callable[..., Any]], ...]:
        return (
            {"label": "Open Dashboard", "callback": self._menu_open_dashboard},
            {"label": "Refresh Status", "callback": self._menu_refresh_status},
            {"label": "Exit Monitor", "callback": self._menu_exit_monitor},
        )

    def create_icon(self) -> Any:
        if not self.dependencies.available:
            raise RuntimeError(self.dependencies.reason or "Tray dependencies are unavailable.")
        image = create_tray_image(
            self.state,
            image_module=self.dependencies.image_module,
            image_draw_module=self.dependencies.image_draw_module,
        )
        pystray = self.dependencies.pystray
        menu_items = [
            pystray.MenuItem(item["label"], item["callback"]) for item in self.build_menu_model()
        ]
        self.icon = pystray.Icon(
            "ai-trading-bot-monitor",
            image,
            self.state.label,
            pystray.Menu(*menu_items),
        )
        return self.icon

    def start(self, *, detached: bool = True) -> dict[str, Any]:
        self.refresh_status()
        if not self.dependencies.available:
            return {
                "mode": "degraded",
                "dashboard_url": build_dashboard_url(self.config),
                "reason": self.dependencies.reason or "Tray dependencies are unavailable.",
                "state": self.state.state,
                "read_only": True,
            }
        icon = self.create_icon()
        if detached and hasattr(icon, "run_detached"):
            icon.run_detached()
        return {
            "mode": "tray",
            "dashboard_url": build_dashboard_url(self.config),
            "reason": "",
            "state": self.state.state,
            "read_only": True,
        }

    def _menu_open_dashboard(self, icon: Any | None = None, item: Any | None = None) -> str:
        del icon, item
        return self.open_dashboard()

    def _menu_refresh_status(self, icon: Any | None = None, item: Any | None = None) -> TrayState:
        del icon, item
        return self.refresh_status()

    def _menu_exit_monitor(self, icon: Any | None = None, item: Any | None = None) -> None:
        del icon, item
        self.exit_monitor()


def load_tray_dependencies() -> TrayDependencies:
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception as exc:
        return TrayDependencies(available=False, reason=str(exc))
    return TrayDependencies(
        available=True,
        reason="",
        pystray=pystray,
        image_module=Image,
        image_draw_module=ImageDraw,
    )


def build_dashboard_url(config: MonitorConfiguration) -> str:
    return f"http://{config.dashboard_host}:{config.dashboard_port}/"


def tray_state_from_dashboard(payload: dict[str, Any]) -> TrayState:
    aggregate_state = str(payload.get("aggregate_state", "unavailable") or "unavailable")
    label, summary, _color = TRAY_STATE_META.get(aggregate_state, TRAY_STATE_META["unavailable"])
    instances = payload.get("instances", []) or []
    issues = payload.get("issues", []) or []
    notes = payload.get("notes", []) or []
    recent_control_actions = payload.get("recent_control_actions", []) or []
    historical_context = payload.get("historical_context", {}) or {}
    issue_count = len(issues)
    note_count = len(notes)
    instance_count = len(instances)
    historical_issue_count = int(historical_context.get("historical_issue_count", 0) or 0)
    critical_count = sum(1 for issue in issues if issue.get("severity") == "critical")
    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    running_runtime_count = sum(1 for instance in instances if instance.get("runtime_state") == "running")
    failed_runtime_count = sum(1 for instance in instances if instance.get("runtime_state") == "failed")
    live_control_count = sum(
        1
        for instance in instances
        if (instance.get("runtime_mode_context") or instance.get("control_mode_context")) == "live"
    )
    paper_control_count = sum(
        1
        for instance in instances
        if (instance.get("runtime_mode_context") or instance.get("control_mode_context")) == "paper"
    )
    latest_runtime_refresh = max(
        (
            str(instance.get("runtime_last_seen_utc", "") or "")
            for instance in instances
            if instance.get("runtime_last_seen_utc")
        ),
        default="",
    )
    if critical_count:
        issue_summary = f"Critical: {critical_count}. Warnings: {warning_count}."
    elif warning_count:
        issue_summary = f"Warnings: {warning_count}."
    else:
        issue_summary = f"Issues: {issue_count}."
    historical_summary = f" Historical: {historical_issue_count}." if historical_issue_count else ""
    runtime_summary = f" Running runtimes: {running_runtime_count}. Failed runtimes: {failed_runtime_count}."
    mode_summary = f" Live controls: {live_control_count}. Paper controls: {paper_control_count}."
    latest_control_summary = ""
    if recent_control_actions:
        latest = recent_control_actions[0]
        latest_control_summary = (
            f" Latest control: {latest.get('requested_action', 'unknown')} "
            f"{latest.get('symbol', 'unknown')} ({latest.get('asset_class', 'unknown')}) "
            f"{latest.get('outcome_state', 'unknown')}."
        )
    refresh_summary = f" Runtime refresh: {latest_runtime_refresh}." if latest_runtime_refresh else ""
    tooltip = (
        f"{summary} Instances: {instance_count}. {issue_summary} Notes: {note_count}."
        f"{runtime_summary}{mode_summary}{latest_control_summary}{refresh_summary}{historical_summary} {TRAY_READ_ONLY_MESSAGE}"
    )
    return TrayState(
        label=label,
        state=aggregate_state,
        tooltip=tooltip,
        last_updated_at=payload.get("status_updated_utc"),
        menu_actions=TRAY_MENU_ACTIONS,
    )


def create_tray_image(
    state: TrayState,
    *,
    image_module: Any,
    image_draw_module: Any,
    size: int = 64,
) -> Any:
    if image_module is None or image_draw_module is None:
        raise RuntimeError("Pillow image dependencies are unavailable.")
    _label, _summary, color = TRAY_STATE_META.get(state.state, TRAY_STATE_META["unavailable"])
    image = image_module.new("RGBA", (size, size), (18, 24, 31, 255))
    draw = image_draw_module.Draw(image)
    draw.rounded_rectangle((6, 6, size - 6, size - 6), radius=12, fill=(29, 40, 52, 255))
    draw.ellipse((18, 18, size - 18, size - 18), fill=color)
    return image


def create_tray_controller(
    *,
    config: MonitorConfiguration | None = None,
    payload_loader: Callable[[], dict[str, Any]] | None = None,
    browser_opener: Callable[[str], Any] = webbrowser.open,
    dependencies: TrayDependencies | None = None,
) -> TrayController:
    return TrayController(
        config=config or load_monitor_configuration(),
        payload_loader=payload_loader,
        browser_opener=browser_opener,
        dependencies=dependencies or load_tray_dependencies(),
    )


def start_monitor_tray(
    *,
    config: MonitorConfiguration | None = None,
    payload_loader: Callable[[], dict[str, Any]] | None = None,
    browser_opener: Callable[[str], Any] = webbrowser.open,
    dependencies: TrayDependencies | None = None,
    detached: bool = True,
) -> tuple[TrayController, dict[str, Any]]:
    controller = create_tray_controller(
        config=config,
        payload_loader=payload_loader,
        browser_opener=browser_opener,
        dependencies=dependencies,
    )
    return controller, controller.start(detached=detached)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local trading bot monitor dashboard and tray.")
    parser.add_argument("--host", default=None, help="Dashboard host override. Defaults to monitor configuration.")
    parser.add_argument("--port", type=int, default=None, help="Dashboard port override. Defaults to monitor configuration.")
    parser.add_argument(
        "--refresh-seconds",
        type=int,
        default=None,
        help="Dashboard refresh cadence in seconds. Defaults to monitor configuration.",
    )
    parser.add_argument(
        "--no-tray",
        action="store_true",
        help="Run the dashboard without creating a system tray icon.",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Explicitly affirm read-only monitor mode. This monitor never places orders.",
    )
    return parser.parse_args(argv)


def _config_with_overrides(
    config: MonitorConfiguration,
    *,
    host: str | None = None,
    port: int | None = None,
    refresh_seconds: int | None = None,
    read_only: bool = True,
    tray_enabled: bool | None = None,
) -> MonitorConfiguration:
    return MonitorConfiguration(
        dashboard_host=host or config.dashboard_host,
        dashboard_port=port or config.dashboard_port,
        refresh_seconds=refresh_seconds or config.refresh_seconds,
        tray_enabled=config.tray_enabled if tray_enabled is None else tray_enabled,
        read_only=read_only,
        runtime_registry_path=config.runtime_registry_path,
        recent_control_actions=config.recent_control_actions,
        instances=config.instances,
    )


def _safe_bot_config():
    try:
        return load_config()
    except Exception:
        return None


def run_dashboard_only(
    config: MonitorConfiguration,
    *,
    app_factory: Callable[..., Any] = create_app,
) -> Any:
    bot_config = _safe_bot_config()
    try:
        app = app_factory(
            instances=config.instances,
            config=bot_config,
            recent_control_actions=config.recent_control_actions,
            refresh_seconds=config.refresh_seconds,
            refresh_runtime_state=True,
        )
    except TypeError:
        app = app_factory(instances=config.instances, refresh_seconds=config.refresh_seconds)
    app.run(host=config.dashboard_host, port=config.dashboard_port, debug=False, use_reloader=False)
    return app


def run_monitor(
    *,
    argv: list[str] | None = None,
    config: MonitorConfiguration | None = None,
    app_factory: Callable[..., Any] = create_app,
    tray_launcher: Callable[..., tuple[TrayController, dict[str, Any]]] = start_monitor_tray,
) -> int:
    args = parse_args(argv)
    bot_config = _safe_bot_config()
    base_config = config or load_monitor_configuration(config=bot_config)
    runtime_config = _config_with_overrides(
        base_config,
        host=args.host,
        port=args.port,
        refresh_seconds=args.refresh_seconds,
        read_only=True if args.read_only or True else True,
        tray_enabled=False if args.no_tray else base_config.tray_enabled,
    )

    if args.no_tray:
        run_dashboard_only(runtime_config, app_factory=app_factory)
        return 0

    tray_launcher(config=runtime_config)
    try:
        app = app_factory(
            instances=runtime_config.instances,
            config=bot_config,
            recent_control_actions=runtime_config.recent_control_actions,
            refresh_seconds=runtime_config.refresh_seconds,
            refresh_runtime_state=True,
        )
    except TypeError:
        app = app_factory(instances=runtime_config.instances, refresh_seconds=runtime_config.refresh_seconds)
    app.run(host=runtime_config.dashboard_host, port=runtime_config.dashboard_port, debug=False, use_reloader=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    return run_monitor(argv=argv)


if __name__ == "__main__":
    raise SystemExit(main())
