from __future__ import annotations

import webbrowser
from dataclasses import dataclass, field
from typing import Any, Callable

from tradingbot.app.monitor import (
    MonitorConfiguration,
    TrayState,
    dashboard_status,
    load_monitor_configuration,
)


TRAY_MENU_ACTIONS = ("Open Dashboard", "Refresh Status", "Exit Monitor")
TRAY_STATE_META = {
    "failed": ("AI Trading Bot Monitor (Critical)", "Critical monitor issue detected.", "#C0392B"),
    "blocked": ("AI Trading Bot Monitor (Blocked)", "A live safeguard blocked execution.", "#D35400"),
    "stale": ("AI Trading Bot Monitor (Stale)", "Monitor evidence is stale.", "#F39C12"),
    "no_data": ("AI Trading Bot Monitor (No Data)", "No runtime evidence found yet.", "#7F8C8D"),
    "live": ("AI Trading Bot Monitor (Live)", "Live evidence is updating.", "#27AE60"),
    "paper": ("AI Trading Bot Monitor (Paper)", "Paper evidence is updating.", "#2980B9"),
    "running": ("AI Trading Bot Monitor (Running)", "Monitor evidence is updating.", "#16A085"),
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
            }
        icon = self.create_icon()
        if detached and hasattr(icon, "run_detached"):
            icon.run_detached()
        return {
            "mode": "tray",
            "dashboard_url": build_dashboard_url(self.config),
            "reason": "",
            "state": self.state.state,
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
    issue_count = len(issues)
    instance_count = len(instances)
    tooltip = f"{summary} Instances: {instance_count}. Issues: {issue_count}."
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
