import json
import os
import csv
import glob
import html
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder

class DashboardGenerator:
    """
    Genera dashboard HTML interactivo con Plotly.
    Todo el output es un solo archivo HTML auto-contenido.
    """
    
    def __init__(self, template_path: str = "dashboard/template.html", output_dir: str = "dashboard/output"):
        # Rutas relativas al directorio de trabajo (raíz del proyecto)
        self.template_path = template_path if os.path.exists(template_path) else "dashboard/template.html"
        self.output_dir = output_dir
        self.public_dir = "dashboard"
        self.history_dir = os.path.join(self.public_dir, "history")
        self.history_json_path = os.path.join(self.public_dir, "dashboard_history.json")
        self.latest_output_path = os.path.join(self.output_dir, "latest.html")
        self.public_index_path = os.path.join(self.public_dir, "index.html")

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)
        
    def _load_template(self) -> str:
        with open(self.template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_data(self, report_path: str = "data/reports/latest.json") -> Dict:
        """
        Carga datos del reporte JSON generado por daily_runner.
        """
        try:
            with open(report_path, 'r') as f:
                raw = json.load(f)
            return self._normalize_report_data(raw)
        except FileNotFoundError:
            # Datos de ejemplo para demo
            return self._generate_demo_data()

    def _normalize_report_data(self, raw: Dict) -> Dict:
        """
        Adapta distintos formatos de reporte al esquema esperado por el dashboard.
        """
        # Si ya está en formato de dashboard, devolver tal cual
        required = {"fecha", "timestamp", "bots_activos", "bots_pausados", "total_bots", "win_rate_avg", "max_drawdown", "strategies", "decisions"}
        if isinstance(raw, dict) and required.issubset(set(raw.keys())):
            return raw

        # Formato de DailyRunner actual
        # {
        #   date, generated_at, regime, decisions, bots, hindsight_summary
        # }
        bots = raw.get("bots", []) if isinstance(raw, dict) else []
        decisions = raw.get("decisions", []) if isinstance(raw, dict) else []
        regime_raw = str(raw.get("regime", "UNKNOWN")) if isinstance(raw, dict) else "UNKNOWN"

        strategies = {}
        win_rates = []
        drawdowns = []

        # Curva sintética mínima para visualización cuando no hay equity histórico
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        date_labels = [d.strftime("%Y-%m-%d") for d in dates]

        for b in bots:
            sid = b.get("strategy_id", "unknown")
            metrics = b.get("metrics", {}) or {}
            wr = float(metrics.get("win_rate", 50))
            dd = float(metrics.get("drawdown", -10))
            pf = float(metrics.get("profit_factor", 1.0))
            status = str(b.get("status", "HOLD")).upper()

            win_rates.append(wr)
            drawdowns.append(dd)

            # Genera una serie simple en torno a 10k para no romper el chart
            drift = (wr - 50.0) / 10000.0
            noise = np.random.normal(drift, 0.003, len(date_labels))
            equity = 10000 * np.cumprod(1 + noise)

            strategies[sid] = {
                "dates": date_labels,
                "equity": equity.tolist(),
                "win_rate": round(wr, 2),
                "drawdown": round(dd, 2),
                "profit_factor": round(pf, 2),
                "sharpe": 0.0,
                "status": status,
                "adaptation_score": float(b.get("adaptation_score", (b.get("metrics") or {}).get("adaptation_score", 50.0))),
            }

        # Transformar decisiones al shape esperado por la tabla
        decisions_norm = []
        for d in decisions:
            sid = d.get("strategy_id", "unknown")
            verdict = str(d.get("verdict", "HOLD")).upper()
            metrics = d.get("metrics", {}) or {}

            decisions_norm.append({
                "date": str(raw.get("date", datetime.now().strftime("%Y-%m-%d"))),
                "bot": sid,
                "win_rate": round(float(metrics.get("win_rate", 50)), 1),
                "drawdown": round(float(metrics.get("drawdown", -10)), 1),
                "profit_factor": round(float(metrics.get("profit_factor", 1.0)), 2),
                "regime": str(d.get("regime", regime_raw)).lower(),
                "verdict": verdict,
                "reason": f"Decision engine verdict: {verdict}",
            })

        bots_activos = sum(1 for b in bots if str(b.get("status", "")).upper() == "ACTIVE")
        bots_pausados = sum(1 for b in bots if str(b.get("status", "")).upper() == "PAUSED")
        total_bots = len(bots)

        regime_name = regime_raw.replace("_", " ").title()
        regime_icon_map = {
            "BULL_TREND": "📈",
            "BEAR_TREND": "📉",
            "MEAN_REVERTING": "↔️",
            "HIGH_VOLATILITY": "⚡",
            "LOW_VOLATILITY": "😴",
            "UNKNOWN": "❔",
            "VOLATILE": "⚡",
        }

        history = []
        for i in range(30):
            history.append({
                "date": (datetime.now() - pd.Timedelta(days=(29 - i))).strftime("%Y-%m-%d"),
                "regime": regime_raw.lower(),
            })

        ts_raw = str(raw.get("generated_at", ""))
        try:
            ts_fmt = datetime.fromisoformat(ts_raw).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            ts_fmt = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        return {
            "fecha": str(raw.get("date", datetime.now().strftime("%Y-%m-%d"))),
            "timestamp": ts_fmt,
            "bots_activos": bots_activos,
            "bots_pausados": bots_pausados,
            "total_bots": total_bots,
            "win_rate_avg": round(float(np.mean(win_rates)) if win_rates else 0.0, 1),
            "max_drawdown": round(float(min(drawdowns)) if drawdowns else 0.0, 1),
            "regime_name": regime_name,
            "regime_icon": regime_icon_map.get(regime_raw.upper(), "❔"),
            "regime_confidence": 70.0,
            "regime_since": (datetime.now() - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "strategies": strategies,
            "decisions": decisions_norm,
            "regime_history": history,
        }
    
    def _generate_demo_data(self) -> Dict:
        """
        Genera datos de demostracion para testing.
        """
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
        
        # Equity curves simuladas
        strategies = ["RSI_MeanReversion", "MACD_Trend", "Bollinger_Breakout", "ML_Predictor"]
        equity_data = {}
        
        for strat in strategies:
            returns = np.random.normal(0.001, 0.02, 90)
            equity = 10000 * np.cumprod(1 + returns)
            equity_data[strat] = {
                "dates": [d.strftime("%Y-%m-%d") for d in dates],
                "equity": equity.tolist(),
                "win_rate": np.random.uniform(40, 65),
                "drawdown": np.random.uniform(-25, -5),
                "profit_factor": np.random.uniform(0.8, 1.8),
                "sharpe": np.random.uniform(-0.5, 2.0),
                "status": np.random.choice(["ACTIVE", "PAUSED", "HOLD"]),
                "adaptation_score": np.random.uniform(30, 95)
            }
        
        # Regimen actual
        regimes = ["bull_trend", "bear_trend", "mean_reverting", "high_volatility", "low_volatility"]
        regime_icons = {
            "bull_trend": "📈",
            "bear_trend": "📉", 
            "mean_reverting": "↔️",
            "high_volatility": "⚡",
            "low_volatility": "😴"
        }
        
        current_regime = np.random.choice(regimes)
        
        # Decision log
        decisions = []
        for i in range(10):
            decisions.append({
                "date": (datetime.now() - pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
                "bot": np.random.choice(strategies),
                "win_rate": round(np.random.uniform(35, 60), 1),
                "drawdown": round(np.random.uniform(-30, -10), 1),
                "profit_factor": round(np.random.uniform(0.9, 1.5), 2),
                "regime": np.random.choice(regimes),
                "verdict": np.random.choice(["PAUSE", "HOLD", "REACTIVATE", "INSUFFICIENT"]),
                "reason": np.random.choice([
                    "WR below 45%",
                    "DD exceeded -20%",
                    "PF below 1.05",
                    "Consecutive losses > 6",
                    "Metrics recovered",
                    "Not enough data"
                ])
            })
        
        return {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bots_activos": sum(1 for s in equity_data.values() if s["status"] == "ACTIVE"),
            "bots_pausados": sum(1 for s in equity_data.values() if s["status"] == "PAUSED"),
            "total_bots": len(strategies),
            "win_rate_avg": round(np.mean([s["win_rate"] for s in equity_data.values()]), 1),
            "max_drawdown": round(min([s["drawdown"] for s in equity_data.values()]), 1),
            "regime_name": current_regime.replace("_", " ").title(),
            "regime_icon": regime_icons[current_regime],
            "regime_confidence": round(np.random.uniform(60, 95), 1),
            "regime_since": (datetime.now() - pd.Timedelta(days=np.random.randint(1, 15))).strftime("%Y-%m-%d"),
            "strategies": equity_data,
            "decisions": decisions,
            "regime_history": [
                {"date": d.strftime("%Y-%m-%d"), "regime": np.random.choice(regimes)}
                for d in dates[-30:]
            ]
        }
    
    def _build_equity_traces(self, data: Dict) -> str:
        traces = []
        colors = ["#00d4ff", "#00ff88", "#ff4757", "#ffa502"]
        
        for i, (name, strat_data) in enumerate(data["strategies"].items()):
            color = colors[i % len(colors)]
            
            trace = {
                "x": strat_data["dates"],
                "y": strat_data["equity"],
                "type": "scatter",
                "mode": "lines",
                "name": f"{name} ({strat_data['status']})",
                "line": {"color": color, "width": 2},
                "hovertemplate": f"<b>{name}</b><br>Fecha: %{{x}}<br>Equity: $%{{y:,.0f}}<br>Status: {strat_data['status']}<extra></extra>"
            }
            traces.append(trace)
        
        return json.dumps(traces)
    
    def _build_adaptation_traces(self, data: Dict) -> str:
        avg_score = np.mean([s["adaptation_score"] for s in data["strategies"].values()])
        
        trace = {
            "type": "indicator",
            "mode": "gauge+number",
            "value": round(avg_score, 1),
            "title": {"text": "Score", "font": {"color": "#e0e0e0"}},
            "gauge": {
                "axis": {"range": [0, 100], "tickcolor": "#e0e0e0"},
                "bar": {"color": "#00d4ff"},
                "bgcolor": "#1a1a3e",
                "borderwidth": 2,
                "bordercolor": "#2a2a4a",
                "steps": [
                    {"range": [0, 40], "color": "rgba(255, 71, 87, 0.3)"},
                    {"range": [40, 70], "color": "rgba(255, 165, 2, 0.3)"},
                    {"range": [70, 100], "color": "rgba(0, 255, 136, 0.3)"}
                ],
                "threshold": {
                    "line": {"color": "white", "width": 4},
                    "thickness": 0.75,
                    "value": 70
                }
            },
            "number": {"font": {"color": "#e0e0e0", "size": 40}}
        }
        
        return json.dumps([trace])
    
    def _build_regime_traces(self, data: Dict) -> str:
        regime_history = data.get("regime_history", [])
        if not regime_history:
            return "[]"
        
        dates = [r["date"] for r in regime_history]
        regimes = list(set(r["regime"] for r in regime_history))
        
        traces = []
        colors_regime = {
            "bull_trend": "#00ff88",
            "bear_trend": "#ff4757",
            "mean_reverting": "#ffa502",
            "high_volatility": "#ff6b81",
            "low_volatility": "#74b9ff"
        }
        
        for regime in regimes:
            probs = [np.random.uniform(0.6, 0.9) if r["regime"] == regime else np.random.uniform(0.01, 0.2) for r in regime_history]
            
            trace = {
                "x": dates,
                "y": probs,
                "type": "scatter",
                "mode": "lines",
                "stackgroup": "one",
                "name": regime.replace("_", " ").title(),
                "fill": "tonexty",
                "line": {"width": 0.5},
                "fillcolor": colors_regime.get(regime, "#888")
            }
            traces.append(trace)
        
        return json.dumps(traces)
    
    def _build_metrics_traces(self, data: Dict) -> str:
        strategies = list(data["strategies"].keys())
        traces = [
            {"x": strategies, "y": [data["strategies"][s]["win_rate"] for s in strategies], "type": "bar", "name": "Win Rate %", "marker": {"color": "#00d4ff"}},
            {"x": strategies, "y": [abs(data["strategies"][s]["drawdown"]) for s in strategies], "type": "bar", "name": "Drawdown %", "marker": {"color": "#ff4757"}},
            {"x": strategies, "y": [data["strategies"][s]["profit_factor"] * 20 for s in strategies], "type": "bar", "name": "PF (x20)", "marker": {"color": "#00ff88"}}
        ]
        return json.dumps(traces)
    
    def _build_regret_traces(self, data: Dict) -> str:
        dates = [(datetime.now() - pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]
        regret_values = np.cumsum(np.random.normal(0.5, 2, 30))
        trace = {
            "x": dates[::-1], "y": regret_values.tolist(), "type": "scatter", "mode": "lines+markers", "name": "Regret Rate",
            "line": {"color": "#ffa502", "width": 2}, "marker": {"size": 6, "color": "#ffa502"}, "fill": "tozeroy", "fillcolor": "rgba(255, 165, 2, 0.1)"
        }
        return json.dumps([trace])

    def _load_history(self) -> List[Dict]:
        try:
            with open(self.history_json_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            return history if isinstance(history, list) else []
        except FileNotFoundError:
            return []

    def _save_history(self, history: List[Dict]):
        with open(self.history_json_path, 'w', encoding='utf-8') as f:
            json.dump(history[-365:], f, indent=2, ensure_ascii=False)

    def _append_snapshot(self, data: Dict):
        strategies = data.get("strategies", {}) or {}
        adaptation_values = [s.get("adaptation_score", 50.0) for s in strategies.values()]
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "bots_activos": int(data.get("bots_activos", 0)),
            "bots_pausados": int(data.get("bots_pausados", 0)),
            "total_bots": int(data.get("total_bots", 0)),
            "win_rate_avg": float(data.get("win_rate_avg", 0.0)),
            "max_drawdown": float(data.get("max_drawdown", 0.0)),
            "regime_name": data.get("regime_name", "Unknown"),
            "regime_confidence": float(data.get("regime_confidence", 0.0)),
            "adaptation_score_avg": float(np.mean(adaptation_values)) if adaptation_values else 50.0,
        }
        history = self._load_history()
        history.append(snapshot)
        self._save_history(history)

    def _compute_history_summary(self) -> Dict:
        history = self._load_history()
        if not history:
            return {
                "history_entries": 0,
                "week_win_rate_avg": 0.0,
                "month_win_rate_avg": 0.0,
                "week_drawdown_avg": 0.0,
                "month_drawdown_avg": 0.0,
                "history_traces": "[]",
            }

        dates = pd.to_datetime([h.get("date") for h in history], errors='coerce')
        now = pd.Timestamp(datetime.now().date())

        week_rows = [h for h, d in zip(history, dates) if pd.notna(d) and (now - d).days <= 7]
        month_rows = [h for h, d in zip(history, dates) if pd.notna(d) and (now - d).days <= 30]

        def avg(rows: List[Dict], key: str) -> float:
            vals = [float(r.get(key, 0.0)) for r in rows if key in r]
            return round(float(np.mean(vals)), 2) if vals else 0.0

        history_trace = {
            "x": [h.get("date") for h in history],
            "y": [float(h.get("win_rate_avg", 0.0)) for h in history],
            "type": "scatter",
            "mode": "lines+markers",
            "name": "WR Avg",
            "line": {"color": "#00d4ff", "width": 2},
        }
        dd_trace = {
            "x": [h.get("date") for h in history],
            "y": [float(h.get("max_drawdown", 0.0)) for h in history],
            "type": "scatter",
            "mode": "lines+markers",
            "name": "Max DD",
            "line": {"color": "#ff4757", "width": 2},
            "yaxis": "y2",
        }

        return {
            "history_entries": len(history),
            "week_win_rate_avg": avg(week_rows, "win_rate_avg"),
            "month_win_rate_avg": avg(month_rows, "win_rate_avg"),
            "week_drawdown_avg": avg(week_rows, "max_drawdown"),
            "month_drawdown_avg": avg(month_rows, "max_drawdown"),
            "history_traces": json.dumps([history_trace, dd_trace]),
        }

    def _build_log_config_rows(self) -> str:
        files = [
            ("logs/bot.log", "técnico", "eventos generales del bot", "siempre"),
            ("logs/apuesta/webhook_server.log", "técnico", "eventos webhook de TradingView", "siempre"),
            ("logs/apuesta/trades_log.txt", "evento", "signal/skip/order/close/error", "por webhook TV"),
            ("data/apuesta/trades_report.csv", "csv", "operaciones de TradingView (OPEN/WIN/LOSS)", "entry/close"),
            ("data/apuesta/paper_signals.csv", "csv", "todas las alertas TV", "cada alerta"),
            ("data/apuesta/paper_resolved.csv", "csv", "paper resuelto", "cuando se resuelve"),
            ("data/trades/*.jsonl", "jsonl", "operaciones/rechazos de rutinas", "por webhook rutina/github"),
        ]

        rows = []
        for path, ftype, desc, when in files:
            exists = bool(glob.glob(path)) if "*" in path else os.path.exists(path)
            badge = '<span class="status-badge status-active">OK</span>' if exists else '<span class="status-badge status-hold">PENDIENTE</span>'
            rows.append(
                f"<tr><td>{html.escape(path)}</td><td>{ftype}</td><td>{html.escape(desc)}</td><td>{html.escape(when)}</td><td>{badge}</td></tr>"
            )
        return "\n".join(rows)

    def _build_operations_section(self) -> Dict:
        ops = []

        # TradingView ops (CSV)
        tv_path = "data/apuesta/trades_report.csv"
        if os.path.exists(tv_path):
            with open(tv_path, "r", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    ts = row.get("close_time_utc") or row.get("open_time_utc") or ""
                    ops.append({
                        "ts": ts,
                        "source": "tradingview",
                        "symbol": row.get("symbol", ""),
                        "setup": row.get("setup", ""),
                        "side": row.get("side", ""),
                        "qty": row.get("qty", ""),
                        "entry": row.get("entry", ""),
                        "close_price": row.get("close_price", ""),
                        "pnl": row.get("pnl_usdt", ""),
                        "outcome": (row.get("outcome") or "").upper() or "OPEN",
                    })

        # Routine/GitHub ops (JSONL)
        trade_files = sorted(glob.glob("data/trades/*.jsonl"), reverse=True)
        for path in trade_files[:15]:
            with open(path, "r", encoding="utf-8") as f:
                for line in f.readlines()[-80:]:
                    try:
                        rec = json.loads(line.strip())
                    except Exception:
                        continue

                    if rec.get("_type") == "signal_rejected":
                        out = "REJECTED"
                        setup = "-"
                        symbol = (rec.get("signal") or {}).get("signal", {}).get("symbol", "")
                        side = "-"
                        qty = "-"
                    else:
                        out = str(rec.get("status", "FILLED")).upper()
                        setup = ((rec.get("original_signal") or {}).get("strategy_id") or rec.get("strategy_id") or "-")
                        symbol = rec.get("symbol", "")
                        side = str(rec.get("side", "")).upper()
                        qty = rec.get("qty", "")

                    ops.append({
                        "ts": rec.get("_logged_at", ""),
                        "source": str(rec.get("source", "routine")).lower(),
                        "symbol": symbol,
                        "setup": setup,
                        "side": side,
                        "qty": qty,
                        "entry": rec.get("filled_avg_price", ""),
                        "close_price": "",
                        "pnl": rec.get("pnl", ""),
                        "outcome": out,
                    })

        def parse_ts(v: str):
            if not v:
                return datetime.min
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(v[:26], fmt)
                except Exception:
                    continue
            return datetime.min

        ops_sorted = sorted(ops, key=lambda x: parse_ts(x.get("ts", "")), reverse=True)[:40]

        wins = sum(1 for o in ops_sorted if o["outcome"] == "WIN")
        losses = sum(1 for o in ops_sorted if o["outcome"] == "LOSS")
        open_ops = sum(1 for o in ops_sorted if o["outcome"] in {"OPEN", "NEW", "ACCEPTED"})

        rows = []
        for o in ops_sorted:
            outcome = o.get("outcome", "")
            cls = "status-hold"
            if outcome in {"WIN", "FILLED"}:
                cls = "status-active"
            elif outcome in {"LOSS", "REJECTED", "ERROR"}:
                cls = "status-paused"

            rows.append(
                "<tr>"
                f"<td>{html.escape(str(o.get('ts', '')))}</td>"
                f"<td>{html.escape(str(o.get('source', '')))}</td>"
                f"<td><strong>{html.escape(str(o.get('symbol', '')))}</strong></td>"
                f"<td>{html.escape(str(o.get('setup', '')))}</td>"
                f"<td>{html.escape(str(o.get('side', '')))}</td>"
                f"<td>{html.escape(str(o.get('qty', '')))}</td>"
                f"<td>{html.escape(str(o.get('entry', '')))}</td>"
                f"<td>{html.escape(str(o.get('close_price', '')))}</td>"
                f"<td>{html.escape(str(o.get('pnl', '')))}</td>"
                f"<td><span class=\"status-badge {cls}\">{html.escape(outcome)}</span></td>"
                "</tr>"
            )

        return {
            "ops_rows": "\n".join(rows) if rows else "<tr><td colspan='10' style='color:#888'>Sin operaciones aún</td></tr>",
            "ops_total": str(len(ops_sorted)),
            "ops_win": str(wins),
            "ops_loss": str(losses),
            "ops_open": str(open_ops),
        }
    
    def _build_decision_rows(self, data: Dict) -> str:
        rows = []
        for d in data["decisions"]:
            status_class = {"PAUSE": "status-paused", "HOLD": "status-hold", "REACTIVATE": "status-active"}.get(d["verdict"], "status-hold")
            wr_class = "metric-positive" if d["win_rate"] >= 45 else "metric-negative"
            dd_class = "metric-negative" if d["drawdown"] <= -20 else "metric-positive"
            pf_class = "metric-positive" if d["profit_factor"] >= 1.05 else "metric-negative"
            
            row = f"""<tr><td>{d['date']}</td><td><strong>{d['bot']}</strong></td><td class="{wr_class}">{d['win_rate']}%</td><td class="{dd_class}">{d['drawdown']}%</td><td class="{pf_class}">{d['profit_factor']}</td><td>{d['regime'].replace('_', ' ').title()}</td><td><span class="status-badge {status_class}">{d['verdict']}</span></td><td style="color: #888; font-size: 0.9em;">{d['reason']}</td></tr>"""
            rows.append(row)
        return "\n".join(rows)
    
    def generate(self, report_path: str = None, output_name: str = None) -> str:
        data = self._load_data(report_path) if report_path else self._generate_demo_data()
        self._append_snapshot(data)
        history_summary = self._compute_history_summary()
        operations_summary = self._build_operations_section()
        template = self._load_template()
        wr_val, dd_val = data["win_rate_avg"], data["max_drawdown"]
        status_badge = (
            '<span class="status-badge status-active">OPERATIVO</span>' if data["bots_activos"] > 0
            else '<span class="status-badge status-paused">PAUSADO</span>'
        )
        replacements = {
            "{{fecha}}": data["fecha"], "{{timestamp}}": data["timestamp"], "{{bots_activos}}": str(data["bots_activos"]), "{{bots_pausados}}": str(data["bots_pausados"]),
            "{{total_bots}}": str(data["total_bots"]), "{{win_rate_avg}}": str(data["win_rate_avg"]), "{{wr_class}}": "metric-positive" if wr_val >= 52 else "metric-negative" if wr_val < 45 else "metric-neutral",
            "{{wr_color}}": "#00ff88" if wr_val >= 52 else "#ff4757" if wr_val < 45 else "#ffa502", "{{max_drawdown}}": str(dd_val), "{{dd_bar_width}}": str(min(abs(dd_val) * 5, 100)),
            "{{regime_name}}": data["regime_name"], "{{regime_icon}}": data["regime_icon"], "{{regime_confidence}}": str(data["regime_confidence"]), "{{regime_since}}": data["regime_since"],
            "{{equity_traces}}": self._build_equity_traces(data), "{{adaptation_traces}}": self._build_adaptation_traces(data), "{{regime_traces}}": self._build_regime_traces(data),
            "{{metrics_traces}}": self._build_metrics_traces(data), "{{regret_traces}}": self._build_regret_traces(data), "{{decision_rows}}": self._build_decision_rows(data),
            "{{system_status_badge}}": status_badge,
            "{{history_entries}}": str(history_summary["history_entries"]),
            "{{week_win_rate_avg}}": str(history_summary["week_win_rate_avg"]),
            "{{month_win_rate_avg}}": str(history_summary["month_win_rate_avg"]),
            "{{week_drawdown_avg}}": str(history_summary["week_drawdown_avg"]),
            "{{month_drawdown_avg}}": str(history_summary["month_drawdown_avg"]),
            "{{history_traces}}": history_summary["history_traces"],
            "{{log_config_rows}}": self._build_log_config_rows(),
            "{{ops_rows}}": operations_summary["ops_rows"],
            "{{ops_total}}": operations_summary["ops_total"],
            "{{ops_win}}": operations_summary["ops_win"],
            "{{ops_loss}}": operations_summary["ops_loss"],
            "{{ops_open}}": operations_summary["ops_open"],
        }
        html = template
        for placeholder, value in replacements.items(): html = html.replace(placeholder, value)
        if output_name is None:
            output_name = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        versioned_output_path = os.path.join(self.output_dir, output_name)
        history_output_path = os.path.join(self.history_dir, output_name)

        for path in [versioned_output_path, self.latest_output_path, self.public_index_path, history_output_path]:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)

        return self.latest_output_path

if __name__ == "__main__":
    generator = DashboardGenerator()
    generator.generate()