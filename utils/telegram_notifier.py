import os
import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Optional, List

from utils.logger import setup_logger

class TelegramNotifier:
    """
    cliente de notificaciones para telegram.
    envía mensajes formateados con emojis y métricas clave.
    """
    
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        # Deshabilitar si chat_id no es un número válido (ej: "PENDIENTE")
        chat_id_valid = bool(self.chat_id and self.chat_id.lstrip('-').isdigit())
        self.enabled = bool(self.token and chat_id_valid)
        
        # flags de qué notificar
        self.notify_pause = os.getenv("NOTIFY_ON_PAUSE", "true").lower() == "true"
        self.notify_reactivate = os.getenv("NOTIFY_ON_REACTIVATE", "true").lower() == "true"
        self.notify_rejected = os.getenv("NOTIFY_ON_SIGNAL_REJECTED", "true").lower() == "true"
        self.notify_error = os.getenv("NOTIFY_ON_ORDER_ERROR", "true").lower() == "true"
        self.notify_drawdown = os.getenv("NOTIFY_ON_CRITICAL_DRAWDOWN", "true").lower() == "true"
        
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None
        self.logger = setup_logger("telegram", "logs/telegram.log")
    
    async def _send_message(self, text: str, parse_mode: str = "html") -> bool:
        """
        envía mensaje a telegram via api.
        """
        if not self.enabled:
            return False
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    result = await response.json()
                    summary = text.replace('\n', ' ')[:50] + "..."
                    if result.get("ok"):
                        self.logger.info(f"{self.chat_id} | INFO | SENT | {summary} | {json.dumps(result)}")
                        return True
                    else:
                        self.logger.error(f"{self.chat_id} | ERROR | FAILED | {summary} | {json.dumps(result)}")
                        return False
        except Exception as e:
            self.logger.critical(f"{self.chat_id} | ERROR | EXCEPTION | {str(e)}")
            return False
    
    def _format_metrics(self, metrics: Dict) -> str:
        lines = []
        if "win_rate" in metrics:
            emoji = "🟢" if metrics["win_rate"] >= 45 else "🔴"
            lines.append(f"{emoji} win rate: {metrics['win_rate']:.1f}%")
        if "drawdown" in metrics:
            emoji = "🟢" if metrics["drawdown"] > -20 else "🔴"
            lines.append(f"{emoji} drawdown: {metrics['drawdown']:.1f}%")
        if "profit_factor" in metrics:
            emoji = "🟢" if metrics["profit_factor"] >= 1.05 else "🔴"
            lines.append(f"{emoji} profit factor: {metrics['profit_factor']:.22f}")
        return "\n".join(lines) if lines else "sin métricas disponibles"

    async def send_pause_alert(self, bot_id: str, reason: str, metrics: Dict):
        if not self.notify_pause: return
        message = (
            f"🛑 <b>bot pausado</b>\n"
            f"────────────────────\n"
            f"estrategia: <code>{bot_id}</code>\n"
            f"razón: {reason}\n"
            f"<b>métricas al pausar:</b>\n{self._format_metrics(metrics)}"
        )
        await self._send_message(message)

    async def send_reactivate_alert(self, bot_id: str, reason: str, metrics: Dict):
        if not self.notify_reactivate: return
        message = (
            f"✅ <b>bot reactivado</b>\n"
            f"────────────────────\n"
            f"estrategia: <code>{bot_id}</code>\n"
            f"razón: {reason}\n"
            f"<b>métricas al reactivar:</b>\n{self._format_metrics(metrics)}"
        )
        await self._send_message(message)

    async def send_signal_rejected(self, signal: Dict, bot_status: str):
        if not self.notify_rejected: return
        message = (
            f"⛔ <b>señal rechazada</b>\n"
            f"────────────────────\n"
            f"estrategia: <code>{signal.get('strategy_id')}</code>\n"
            f"símbolo: {signal.get('symbol')}\n"
            f"acción: {signal.get('action')}\n"
            f"motivo: bot está <b>{bot_status}</b>"
        )
        await self._send_message(message)

    async def send_order_error(self, bot_id: str, error: str, signal: Dict):
        if not self.notify_error: return
        message = (
            f"❌ <b>error en orden</b>\n"
            f"────────────────────\n"
            f"estrategia: <code>{bot_id}</code>\n"
            f"error: <code>{error}</code>"
        )
        await self._send_message(message)

    async def send_daily_summary(self, summary: Dict):
        if os.getenv("send_daily_summary", "true").lower() != "true": return
        
        regime = summary.get("regime", "unknown")
        message = (
            f"📋 <b>resumen diario - bot manager</b>\n"
            f"────────────────────\n"
            f"régimen: {regime.upper()}\n\n"
            f"🟢 activos: {len([b for b in summary['bots'] if b['status'] == 'active'])}\n"
            f"🔴 pausados: {len([b for b in summary['bots'] if b['status'] == 'paused'])}\n"
        )
        
        if summary.get("today_changes"):
            message += "\n<b>cambios hoy:</b>\n"
            for c in summary["today_changes"]:
                message += f"• {c['bot_id']}: {c['verdict']}\n"
        
        await self._send_message(message)

    async def send_startup_notification(self):
        mode = "live" if os.getenv("execute_orders", "false").lower() == "true" else "dry run"
        message = f"🤖 <b>bot iniciado</b>\nmodo: {'🔴' if mode == 'live' else '🟡'} {mode}"
        await self._send_message(message)

    async def send_test_message(self) -> bool:
        return await self._send_message("🧪 <b>mensaje de prueba</b>\nconfiguración correcta.")