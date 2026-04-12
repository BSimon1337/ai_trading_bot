from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from tradingbot.config.settings import BotConfig


class ReadinessStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


STATUS_EXIT_CODES = {
    ReadinessStatus.PASS: 0,
    ReadinessStatus.WARNING: 1,
    ReadinessStatus.FAIL: 2,
}


@dataclass(frozen=True)
class ReadinessCheckResult:
    name: str
    status: ReadinessStatus
    message: str
    details: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadinessReport:
    checks: tuple[ReadinessCheckResult, ...]

    @property
    def overall_status(self) -> ReadinessStatus:
        statuses = {check.status for check in self.checks}
        if ReadinessStatus.FAIL in statuses:
            return ReadinessStatus.FAIL
        if ReadinessStatus.WARNING in statuses:
            return ReadinessStatus.WARNING
        return ReadinessStatus.PASS

    @property
    def exit_code(self) -> int:
        return STATUS_EXIT_CODES[self.overall_status]

    def to_text(self) -> str:
        lines = [f"Preflight readiness: {self.overall_status.value}"]
        for check in self.checks:
            lines.append(f"- {check.status.value}: {check.name} - {check.message}")
        return "\n".join(lines)


def run_preflight(config: BotConfig, target_mode: str | None = None) -> ReadinessReport:
    """Temporary safe preflight route until detailed checks are implemented."""
    requested_mode = (target_mode or ("paper" if config.paper else "live")).strip().lower()
    return ReadinessReport(
        checks=(
            ReadinessCheckResult(
                name="preflight_foundation",
                status=ReadinessStatus.WARNING,
                message="Preflight CLI route is safe, but detailed readiness checks are not implemented yet.",
                details={"target_mode": requested_mode},
            ),
        )
    )
