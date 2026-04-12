from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Mapping

import joblib

from tradingbot.config.settings import BotConfig, infer_asset_class
from tradingbot.execution.safeguards import RuntimeGuardrailError, resolve_runtime_state


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

    @property
    def failed_checks(self) -> tuple[ReadinessCheckResult, ...]:
        return tuple(check for check in self.checks if check.status == ReadinessStatus.FAIL)

    @property
    def warning_checks(self) -> tuple[ReadinessCheckResult, ...]:
        return tuple(check for check in self.checks if check.status == ReadinessStatus.WARNING)

    def to_text(self) -> str:
        lines = [f"Preflight readiness: {self.overall_status.value}"]
        for check in self.checks:
            lines.append(f"- {check.status.value}: {check.name} - {check.message}")
        return "\n".join(lines)


def run_preflight(config: BotConfig, target_mode: str | None = None) -> ReadinessReport:
    requested_mode = (target_mode or ("paper" if config.paper else "live")).strip().lower()
    checks = [
        _check_credentials(config),
        _check_symbols(config),
        check_log_paths(config),
        _check_trading_access(config),
        _check_market_data_access(config),
        _check_news_access(config),
        _check_live_safeguards(config, requested_mode),
        _check_required_dependencies(),
        _check_optional_sentiment_dependencies(),
        check_model_loadability(config),
    ]
    return ReadinessReport(tuple(checks))


def _check_credentials(config: BotConfig) -> ReadinessCheckResult:
    missing = []
    if not config.api_key:
        missing.append("API_KEY")
    if not config.api_secret:
        missing.append("API_SECRET")
    if missing:
        return ReadinessCheckResult(
            name="credentials",
            status=ReadinessStatus.FAIL,
            message=f"Missing required credential values: {', '.join(missing)}.",
            details={"missing": tuple(missing)},
        )
    return ReadinessCheckResult(
        name="credentials",
        status=ReadinessStatus.PASS,
        message="Alpaca credential values are present.",
        details={"base_url": config.base_url},
    )


def _check_symbols(config: BotConfig) -> ReadinessCheckResult:
    if not config.symbols:
        return ReadinessCheckResult(
            name="symbols",
            status=ReadinessStatus.FAIL,
            message="No symbols are configured.",
        )
    classifications = {symbol: infer_asset_class(symbol) for symbol in config.symbols if symbol.strip()}
    if len(classifications) != len(config.symbols):
        return ReadinessCheckResult(
            name="symbols",
            status=ReadinessStatus.FAIL,
            message="One or more configured symbols are empty.",
            details={"symbols": config.symbols},
        )
    return ReadinessCheckResult(
        name="symbols",
        status=ReadinessStatus.PASS,
        message=f"Configured symbols are parseable: {classifications}.",
        details={"asset_classes": classifications},
    )


def check_log_paths(config: BotConfig) -> ReadinessCheckResult:
    paths = config.log_paths
    failures: list[str] = []
    for label, path in paths.items():
        try:
            _check_path_writable(path)
        except OSError as exc:
            failures.append(f"{label}={path}: {exc}")
    if failures:
        return ReadinessCheckResult(
            name="log_paths",
            status=ReadinessStatus.FAIL,
            message=f"One or more log paths are not writable: {'; '.join(failures)}",
        )
    return ReadinessCheckResult(
        name="log_paths",
        status=ReadinessStatus.PASS,
        message="Runtime log paths are writable or creatable.",
        details={label: str(path) for label, path in paths.items()},
    )


def _check_path_writable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_dir():
        raise OSError("path is a directory")
    probe = path.parent / f".{path.name}.preflight.tmp"
    probe.write_text("preflight", encoding="utf-8")
    probe.unlink(missing_ok=True)


def _check_trading_access(config: BotConfig) -> ReadinessCheckResult:
    try:
        from alpaca.trading.client import TradingClient

        client = TradingClient(
            config.api_key,
            config.api_secret,
            paper=config.paper,
            url_override=config.base_url or None,
        )
        account = client.get_account()
    except Exception as exc:
        return ReadinessCheckResult(
            name="alpaca_trading_access",
            status=ReadinessStatus.WARNING,
            message=f"Trading access probe did not complete: {exc}",
        )
    status = getattr(account, "status", "unknown")
    return ReadinessCheckResult(
        name="alpaca_trading_access",
        status=ReadinessStatus.PASS,
        message=f"Trading account probe completed with status {status}.",
    )


def _check_market_data_access(config: BotConfig) -> ReadinessCheckResult:
    symbol = config.symbol
    try:
        if infer_asset_class(symbol) == "crypto":
            from alpaca.data.historical import CryptoHistoricalDataClient
            from alpaca.data.requests import CryptoLatestQuoteRequest

            client = CryptoHistoricalDataClient(config.api_key, config.api_secret)
            client.get_crypto_latest_quote(CryptoLatestQuoteRequest(symbol_or_symbols=symbol))
        else:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockLatestQuoteRequest

            client = StockHistoricalDataClient(config.api_key, config.api_secret)
            client.get_stock_latest_quote(StockLatestQuoteRequest(symbol_or_symbols=symbol))
    except Exception as exc:
        return ReadinessCheckResult(
            name="alpaca_market_data_access",
            status=ReadinessStatus.WARNING,
            message=f"Market data probe did not complete for {symbol}: {exc}",
        )
    return ReadinessCheckResult(
        name="alpaca_market_data_access",
        status=ReadinessStatus.PASS,
        message=f"Market data probe completed for {symbol}.",
    )


def _check_news_access(config: BotConfig) -> ReadinessCheckResult:
    try:
        from alpaca.data.historical import NewsClient
        from alpaca.data.requests import NewsRequest

        client = NewsClient(config.api_key, config.api_secret)
        now = datetime.now(timezone.utc)
        client.get_news(NewsRequest(symbols=config.symbol, start=now, end=now, limit=1))
    except Exception as exc:
        return ReadinessCheckResult(
            name="alpaca_news_access",
            status=ReadinessStatus.WARNING,
            message=f"News access probe did not complete for {config.symbol}: {exc}",
        )
    return ReadinessCheckResult(
        name="alpaca_news_access",
        status=ReadinessStatus.PASS,
        message=f"News access probe completed for {config.symbol}.",
    )


def _check_live_safeguards(config: BotConfig, requested_mode: str) -> ReadinessCheckResult:
    if requested_mode != "live":
        return ReadinessCheckResult(
            name="live_safeguards",
            status=ReadinessStatus.PASS,
            message=f"Live safeguards not required for {requested_mode} readiness.",
        )
    if config.paper:
        return ReadinessCheckResult(
            name="live_safeguards",
            status=ReadinessStatus.FAIL,
            message="Live readiness is blocked because PAPER_TRADING is enabled.",
        )
    try:
        runtime_state = resolve_runtime_state(config, "live")
    except RuntimeGuardrailError as exc:
        return ReadinessCheckResult(
            name="live_safeguards",
            status=ReadinessStatus.FAIL,
            message=str(exc),
        )
    if runtime_state.execution_mode != "live":
        return ReadinessCheckResult(
            name="live_safeguards",
            status=ReadinessStatus.FAIL,
            message=f"Live readiness is blocked because runtime resolved to {runtime_state.execution_mode}.",
        )
    return ReadinessCheckResult(
        name="live_safeguards",
        status=ReadinessStatus.PASS,
        message="Live safeguards are satisfied for explicit live readiness.",
    )


def _check_required_dependencies() -> ReadinessCheckResult:
    required_modules = ("lumibot", "alpaca", "pandas", "joblib", "dotenv")
    missing = _missing_modules(required_modules)
    if missing:
        return ReadinessCheckResult(
            name="required_dependencies",
            status=ReadinessStatus.FAIL,
            message=f"Missing required Python dependencies: {', '.join(missing)}.",
            details={"missing": tuple(missing)},
        )
    return ReadinessCheckResult(
        name="required_dependencies",
        status=ReadinessStatus.PASS,
        message="Required Python dependencies are importable.",
        details={"checked": required_modules},
    )


def _check_optional_sentiment_dependencies() -> ReadinessCheckResult:
    optional_modules = ("transformers", "torch")
    missing = _missing_modules(optional_modules)
    if missing:
        return ReadinessCheckResult(
            name="optional_sentiment_dependencies",
            status=ReadinessStatus.WARNING,
            message=(
                "Optional local FinBERT sentiment dependencies are unavailable: "
                f"{', '.join(missing)}. Core strategy can still use fallback sentiment paths."
            ),
            details={"missing": tuple(missing)},
        )
    return ReadinessCheckResult(
        name="optional_sentiment_dependencies",
        status=ReadinessStatus.PASS,
        message="Optional local FinBERT sentiment dependencies are importable.",
        details={"checked": optional_modules},
    )


def check_model_loadability(config: BotConfig) -> ReadinessCheckResult:
    if not config.use_model_signal:
        return ReadinessCheckResult(
            name="model_loadability",
            status=ReadinessStatus.PASS,
            message="Model signal is disabled; no saved model load is required.",
        )
    model_path = Path(config.model_path)
    if not model_path.exists():
        return ReadinessCheckResult(
            name="model_loadability",
            status=ReadinessStatus.WARNING,
            message=f"Model file is not present at {model_path}; strategy will fall back to sentiment rules.",
            details={"model_path": str(model_path)},
        )
    try:
        joblib.load(model_path)
    except Exception as exc:
        return ReadinessCheckResult(
            name="model_loadability",
            status=ReadinessStatus.WARNING,
            message=f"Model file at {model_path} could not be loaded; strategy will fall back to sentiment rules. Error: {exc}",
            details={"model_path": str(model_path), "error": str(exc)},
        )
    return ReadinessCheckResult(
        name="model_loadability",
        status=ReadinessStatus.PASS,
        message=f"Model file loaded successfully from {model_path}.",
        details={"model_path": str(model_path)},
    )


def _missing_modules(module_names: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for module_name in module_names:
        try:
            importlib.import_module(module_name)
        except Exception:
            missing.append(module_name)
    return missing
