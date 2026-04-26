import csv
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from utils.logger import setup_logger


class TradingViewBridge:
    """
    Procesa webhooks de TradingView y los enruta a Alpaca via OrderRouter.

    Nota importante:
    - Se elimina totalmente el monitor loop continuo del bot previo.
    - Este modulo solo procesa alertas entrantes y ejecuta/cierra operaciones.
    """

    def __init__(
        self,
        order_router,
        bot_registry,
        trade_logger,
        logger,
        notifier=None,
        webhook_secret: Optional[str] = None,
        risk_usdt: float = 1.0,
        reward_usdt: float = 1.0,
        cooldown_min: int = 5,
        max_daily_losses: int = 10,
    ):
        self.order_router = order_router
        self.bot_registry = bot_registry
        self.trade_logger = trade_logger
        self.logger = logger
        self.notifier = notifier

        self.webhook_secret = webhook_secret or ""
        self.risk_usdt = float(risk_usdt)
        self.reward_usdt = float(reward_usdt)
        self.cooldown_min = int(cooldown_min)
        self.max_daily_losses = int(max_daily_losses)

        self.state_lock = threading.Lock()
        self.daily_losses = 0
        self.day = datetime.now(timezone.utc).date()
        self.paused = False
        self.last_action_ts: Dict[str, float] = {}
        self.active_positions: Dict[str, Dict] = {}

        self.base_dir = Path("apuesta")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir = Path("logs") / "apuesta"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = Path("data") / "apuesta"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.webhook_log_path = self.logs_dir / "webhook_server.log"
        self.webhook_logger = setup_logger("apuesta_webhook", str(self.webhook_log_path))
        self.text_log_path = self.logs_dir / "trades_log.txt"
        self.paper_signals_csv = self.data_dir / "paper_signals.csv"
        self.paper_resolved_csv = self.data_dir / "paper_resolved.csv"
        self.trades_report_csv = self.data_dir / "trades_report.csv"

        self._ensure_csv_headers()

    @staticmethod
    def is_tradingview_payload(payload: Dict) -> bool:
        return isinstance(payload, dict) and "symbol" in payload and "action" in payload

    def is_secret_valid(self, provided_secret: Optional[str]) -> bool:
        if not self.webhook_secret:
            return True
        return (provided_secret or "") == self.webhook_secret

    def get_health(self) -> Dict:
        now = time.time()
        cooldowns = {
            symbol: max(0, int((ts + self.cooldown_min * 60) - now))
            for symbol, ts in self.last_action_ts.items()
            if (ts + self.cooldown_min * 60) > now
        }
        return {
            "status": "ok",
            "paused": self.paused,
            "daily_losses": self.daily_losses,
            "day_utc": str(self.day),
            "risk_usdt": self.risk_usdt,
            "reward_usdt": self.reward_usdt,
            "cooldown_min": self.cooldown_min,
            "cooldown_seconds": cooldowns,
            "module": "apuesta/tradingview_bridge",
            "monitor_loop_enabled": False,
            "log_files": self.get_log_config(),
        }

    def get_log_config(self) -> Dict:
        return {
            "webhook_server_log": str(self.webhook_log_path).replace("\\", "/"),
            "trades_log_txt": str(self.text_log_path).replace("\\", "/"),
            "trades_report_csv": str(self.trades_report_csv).replace("\\", "/"),
            "paper_signals_csv": str(self.paper_signals_csv).replace("\\", "/"),
            "paper_resolved_csv": str(self.paper_resolved_csv).replace("\\", "/"),
            "monitor_loop": "disabled",
        }

    def unpause(self) -> Dict:
        with self.state_lock:
            prev_losses = self.daily_losses
            self.daily_losses = 0
            self.paused = False
        self._log_text("BOT_UNPAUSED", "-", "-", f"manual reset (prev_losses={prev_losses})")
        return {"status": "ok", "previous_losses": prev_losses}

    def get_report_csv(self) -> str:
        if not self.trades_report_csv.exists():
            return ""
        return self.trades_report_csv.read_text(encoding="utf-8")

    def get_paper_csv(self) -> str:
        if not self.paper_resolved_csv.exists():
            return ""
        return self.paper_resolved_csv.read_text(encoding="utf-8")

    def get_stats(self) -> Dict:
        rows = self._read_csv_rows(self.trades_report_csv)
        return self._aggregate_rows(rows)

    def get_paper_stats(self) -> Dict:
        rows = self._read_csv_rows(self.paper_resolved_csv)
        return self._aggregate_rows(rows)

    async def handle_payload(self, payload: Dict) -> Tuple[Dict, int]:
        self._roll_day()

        try:
            symbol = self._normalize_symbol(str(payload.get("symbol", "")))
            action = str(payload.get("action", "")).lower().strip()
            setup = str(payload.get("setup", "TV")).strip() or "TV"

            if action not in {"buy", "sell", "close"}:
                return {"status": "error", "detail": "action debe ser buy/sell/close"}, 400

            if not symbol:
                return {"status": "error", "detail": "symbol invalido"}, 400

            if action == "close":
                return await self._handle_close(symbol, setup)

            return await self._handle_entry(payload, symbol, action, setup)
        except Exception as e:
            self.logger.error(f"TradingView bridge error: {e}", exc_info=True)
            return {"status": "error", "detail": str(e)}, 500

    async def _handle_close(self, symbol: str, setup: str) -> Tuple[Dict, int]:
        result = await self.order_router.close_position(symbol)
        close_price = self._as_float(result.get("filled_avg_price"))
        payload = {"symbol": symbol, "action": "close", "price": close_price, "setup": setup}
        self._resolve_active_position(symbol, close_price)
        self._register_paper_resolved(payload, symbol, setup, "CLOSE", close_price)
        if self.trade_logger:
            self.trade_logger.log_trade({
                "source": "tradingview",
                "event": "close",
                "symbol": symbol,
                "setup": setup,
                "mode": result.get("execution_mode"),
                "filled_avg_price": close_price,
                "status": result.get("status"),
            })
        self._register_action(symbol)
        self._log_text("CLOSE", symbol, setup, "close_position")
        return {
            "status": "executed",
            "source": "tradingview",
            "symbol": symbol,
            "action": "close",
            "result": result,
        }, 200

    async def _handle_entry(self, payload: Dict, symbol: str, action: str, setup: str) -> Tuple[Dict, int]:
        with self.state_lock:
            if self.paused:
                self._register_paper_signal(payload, symbol, action, setup, executed=False, skip_reason="bot_paused")
                return {
                    "status": "rejected",
                    "source": "tradingview",
                    "reason": "bot paused by daily loss cap",
                }, 200

        strategy_id = self._strategy_id_for_setup(setup)
        if self.bot_registry and self.bot_registry.is_paused(strategy_id):
            self._register_paper_signal(payload, symbol, action, setup, executed=False, skip_reason="strategy_paused")
            return {
                "status": "rejected",
                "source": "tradingview",
                "reason": f"strategy {strategy_id} paused",
            }, 200

        if self._in_cooldown(symbol):
            self._register_paper_signal(payload, symbol, action, setup, executed=False, skip_reason="cooldown")
            return {
                "status": "skipped",
                "source": "tradingview",
                "reason": "cooldown active",
            }, 200

        if self._has_open_position(symbol):
            self._register_paper_signal(payload, symbol, action, setup, executed=False, skip_reason="open_position")
            return {
                "status": "skipped",
                "source": "tradingview",
                "reason": "open position detected",
            }, 200

        entry = self._as_float(payload.get("price"))
        sl = self._as_float(payload.get("sl"))
        tp = self._as_float(payload.get("tp"))

        qty = self._calculate_qty(entry, sl, payload.get("size"))
        tp_target = self._recalculate_tp(entry, sl, action, qty, tp)

        signal = {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "action": action,
            "confidence": max(self._as_float(payload.get("confidence"), default=0.7), 0.5),
            "size": qty,
            "order_type": "market",
            "time_in_force": "gtc",
        }

        # En live Alpaca admite brackets para market/limit con stop_loss y take_profit.
        if sl and sl > 0:
            signal["stop_loss"] = {"stop_price": round(sl, 4)}
        if tp_target and tp_target > 0:
            signal["take_profit"] = {"limit_price": round(tp_target, 4)}

        try:
            result = await self.order_router.place_order(signal)
            if self.bot_registry:
                self.bot_registry.record_trade(strategy_id, result)
            if self.trade_logger:
                self.trade_logger.log_trade({
                    "source": "tradingview",
                    "event": "order_placed",
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "side": action,
                    "qty": qty,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp_target,
                    "setup": setup,
                    "mode": result.get("execution_mode"),
                    "order_id": result.get("id"),
                })
            self._register_action(symbol)
            self.active_positions[symbol] = {
                "open_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "open_ts": time.time(),
                "symbol": symbol,
                "setup": setup,
                "side": action.upper(),
                "entry": entry,
                "sl": sl,
                "tp": tp_target,
                "qty": qty,
            }
            self._register_paper_signal(payload, symbol, action, setup, executed=True, skip_reason="")
            self._append_trades_report(symbol, setup, action, entry, sl, tp_target, qty, result)
            self._log_text("ORDER_PLACED", symbol, setup, f"qty={qty} mode={result.get('execution_mode')}")

            return {
                "status": "executed",
                "source": "tradingview",
                "symbol": symbol,
                "strategy_id": strategy_id,
                "order_id": result.get("id"),
                "qty": qty,
                "entry": entry,
                "sl": sl,
                "tp": tp_target,
                "mode": result.get("execution_mode"),
            }, 200
        except Exception as e:
            self._register_paper_signal(payload, symbol, action, setup, executed=False, skip_reason=f"error:{str(e)[:80]}")
            self._register_loss()
            if self.trade_logger:
                self.trade_logger.log_signal_rejected(
                    {"source": "tradingview", "payload": payload},
                    f"ERROR:{str(e)[:120]}"
                )
            if self.notifier and getattr(self.notifier, "enabled", False):
                await self.notifier.send_order_error(strategy_id, str(e), payload)
            self._log_text("ERROR", symbol, setup, str(e))
            return {"status": "error", "source": "tradingview", "detail": str(e)}, 500

    def _has_open_position(self, symbol: str) -> bool:
        positions_data = self.order_router.client.get_positions()
        positions = positions_data.get("positions", []) if isinstance(positions_data, dict) else []

        for pos in positions:
            pos_symbol = str(pos.get("symbol", "")).upper().replace("/", "")
            if pos_symbol != symbol:
                continue

            qty_candidates = [
                pos.get("qty"),
                pos.get("position_qty"),
                pos.get("positionAmt"),
            ]
            for value in qty_candidates:
                try:
                    if abs(float(value)) > 0:
                        return True
                except (TypeError, ValueError):
                    continue
        return False

    def _in_cooldown(self, symbol: str) -> bool:
        last_ts = self.last_action_ts.get(symbol, 0)
        return (time.time() - last_ts) < (self.cooldown_min * 60)

    def _register_action(self, symbol: str):
        self.last_action_ts[symbol] = time.time()

    def _roll_day(self):
        today = datetime.now(timezone.utc).date()
        if today != self.day:
            self.day = today
            self.daily_losses = 0
            self.paused = False

    def _register_loss(self):
        with self.state_lock:
            self.daily_losses += 1
            if self.daily_losses >= self.max_daily_losses:
                self.paused = True

    def _calculate_qty(self, entry: Optional[float], sl: Optional[float], incoming_size) -> float:
        if entry and sl and abs(entry - sl) > 0:
            qty = self.risk_usdt / abs(entry - sl)
            return max(round(qty, 6), 0.0001)

        try:
            size = float(incoming_size) if incoming_size is not None else 0.1
        except (TypeError, ValueError):
            size = 0.1
        return max(round(size, 6), 0.0001)

    def _recalculate_tp(
        self,
        entry: Optional[float],
        sl: Optional[float],
        action: str,
        qty: float,
        incoming_tp: Optional[float],
    ) -> Optional[float]:
        if not entry or qty <= 0:
            return incoming_tp

        if self.reward_usdt > 0:
            distance = self.reward_usdt / qty
            if action == "buy":
                return entry + distance
            return entry - distance

        if incoming_tp:
            return incoming_tp

        if sl and abs(entry - sl) > 0:
            distance = abs(entry - sl)
            if action == "buy":
                return entry + distance
            return entry - distance
        return None

    def _normalize_symbol(self, raw_symbol: str) -> str:
        symbol = raw_symbol.upper().replace(".P", "").replace("/", "")
        if symbol.endswith("USDT"):
            symbol = symbol[:-1]  # ETHUSDT -> ETHUSD (Alpaca crypto)
        return symbol

    def _strategy_id_for_setup(self, setup: str) -> str:
        normalized = "".join(ch if ch.isalnum() else "_" for ch in setup.lower()).strip("_")
        return f"apuesta_{normalized}" if normalized else "apuesta_tv"

    def _register_paper_signal(self, payload, symbol, action, setup, executed: bool, skip_reason: str):
        row = {
            "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "setup": setup,
            "side": action.upper(),
            "entry": self._as_float(payload.get("price")),
            "sl": self._as_float(payload.get("sl")),
            "tp": self._as_float(payload.get("tp")),
            "was_executed": "Y" if executed else "N",
            "skip_reason": skip_reason,
        }
        with self.paper_signals_csv.open("a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([
                row["ts_utc"], row["symbol"], row["setup"], row["side"],
                row["entry"], row["sl"], row["tp"], row["was_executed"], row["skip_reason"],
            ])

        if self.trade_logger and not executed and skip_reason:
            self.trade_logger.log_signal_rejected(
                {"source": "tradingview", "payload": payload},
                f"SKIP:{skip_reason}"
            )

    def _register_paper_resolved(self, payload, symbol, setup, outcome: str, close_price: Optional[float]):
        row = {
            "open_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "close_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "duration_sec": 0,
            "symbol": symbol,
            "setup": setup,
            "side": str(payload.get("action", "")).upper(),
            "entry": self._as_float(payload.get("price")),
            "sl": self._as_float(payload.get("sl")),
            "tp": self._as_float(payload.get("tp")),
            "close_price": close_price if close_price is not None else "",
            "outcome": outcome,
            "was_executed": "Y",
            "skip_reason": "",
        }
        with self.paper_resolved_csv.open("a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([
                row["open_time_utc"], row["close_time_utc"], row["duration_sec"], row["symbol"],
                row["setup"], row["side"], row["entry"], row["sl"], row["tp"],
                row["close_price"], row["outcome"], row["was_executed"], row["skip_reason"],
            ])

    def _append_trades_report(self, symbol, setup, action, entry, sl, tp, qty, result: Dict):
        row = {
            "open_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "close_time_utc": "",
            "duration_sec": "",
            "symbol": symbol,
            "setup": setup,
            "side": action.upper(),
            "entry": entry or "",
            "sl": sl or "",
            "tp": tp or "",
            "qty": qty,
            "leverage": "alpaca",
            "close_price": "",
            "pnl_usdt": "",
            "outcome": "OPEN",
            "risk_usdt": self.risk_usdt,
            "margin_usdt": "",
            "notional_usdt": "",
            "order_id": result.get("id"),
            "mode": result.get("execution_mode"),
        }

        with self.trades_report_csv.open("a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([
                row["open_time_utc"], row["close_time_utc"], row["duration_sec"], row["symbol"],
                row["setup"], row["side"], row["entry"], row["sl"], row["tp"], row["qty"],
                row["leverage"], row["close_price"], row["pnl_usdt"], row["outcome"],
                row["risk_usdt"], row["margin_usdt"], row["notional_usdt"],
                row["order_id"], row["mode"],
            ])

    def _resolve_active_position(self, symbol: str, close_price: Optional[float]):
        active = self.active_positions.pop(symbol, None)
        if not active:
            return

        now_ts = time.time()
        duration = int(now_ts - active["open_ts"])
        entry = active.get("entry")
        qty = active.get("qty")
        side = active.get("side", "BUY")
        pnl = ""
        outcome = "CLOSED"

        if close_price is not None and entry is not None and qty is not None:
            if side == "BUY":
                pnl_val = (close_price - entry) * qty
            else:
                pnl_val = (entry - close_price) * qty
            pnl = round(pnl_val, 4)
            if pnl_val > 0:
                outcome = "WIN"
            elif pnl_val < 0:
                outcome = "LOSS"
                self._register_loss()

        with self.trades_report_csv.open("a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow([
                active["open_time_utc"],
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                duration,
                symbol,
                active.get("setup", "TV"),
                side,
                active.get("entry", ""),
                active.get("sl", ""),
                active.get("tp", ""),
                active.get("qty", ""),
                "alpaca",
                close_price if close_price is not None else "",
                pnl,
                outcome,
                self.risk_usdt,
                "",
                "",
                "",
                "",
            ])

    def _log_text(self, event: str, symbol: str, setup: str, detail: str):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{ts}] | {event} | {symbol} | {setup} | {detail}\n"
        with self.text_log_path.open("a", encoding="utf-8") as f:
            f.write(line)
        self.webhook_logger.info(f"{event} | symbol={symbol} | setup={setup} | detail={detail}")
        self.logger.info(f"APUESTA {event} {symbol} setup={setup} detail={detail}")

    def _ensure_csv_headers(self):
        if not self.paper_signals_csv.exists() or self.paper_signals_csv.stat().st_size == 0:
            with self.paper_signals_csv.open("w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow([
                    "ts_utc", "symbol", "setup", "side", "entry", "sl", "tp", "was_executed", "skip_reason",
                ])

        if not self.paper_resolved_csv.exists() or self.paper_resolved_csv.stat().st_size == 0:
            with self.paper_resolved_csv.open("w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow([
                    "open_time_utc", "close_time_utc", "duration_sec", "symbol", "setup", "side",
                    "entry", "sl", "tp", "close_price", "outcome", "was_executed", "skip_reason",
                ])

        if not self.trades_report_csv.exists() or self.trades_report_csv.stat().st_size == 0:
            with self.trades_report_csv.open("w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerow([
                    "open_time_utc", "close_time_utc", "duration_sec", "symbol", "setup", "side",
                    "entry", "sl", "tp", "qty", "leverage", "close_price", "pnl_usdt", "outcome",
                    "risk_usdt", "margin_usdt", "notional_usdt", "order_id", "mode",
                ])

    @staticmethod
    def _as_float(value, default=None):
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _read_csv_rows(path: Path) -> list:
        if not path.exists() or path.stat().st_size == 0:
            return []
        with path.open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    @staticmethod
    def _aggregate_rows(rows: list) -> Dict:
        wins = sum(1 for r in rows if str(r.get("outcome", "")).upper() == "WIN")
        losses = sum(1 for r in rows if str(r.get("outcome", "")).upper() == "LOSS")
        open_ops = sum(1 for r in rows if str(r.get("outcome", "")).upper() == "OPEN")

        pnl = 0.0
        for r in rows:
            try:
                pnl += float(r.get("pnl_usdt", 0) or 0)
            except (TypeError, ValueError):
                continue

        total_closed = wins + losses
        return {
            "trades": len(rows),
            "wins": wins,
            "losses": losses,
            "open": open_ops,
            "winrate_pct": round((wins / total_closed) * 100, 2) if total_closed else 0.0,
            "pnl_usdt": round(pnl, 4),
        }
