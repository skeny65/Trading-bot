import json
import os
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
    
    def __init__(self, template_path: str = "dashboard_template.html", output_dir: str = "dashboard/output"):
        # Ajuste de rutas para el nuevo orden
        self.template_path = template_path if os.path.exists(template_path) else "dashboard_template.html"
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _load_template(self) -> str:
        with open(self.template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_data(self, report_path: str = "data/reports/latest.json") -> Dict:
        """
        Carga datos del reporte JSON generado por daily_runner.
        """
        try:
            with open(report_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Datos de ejemplo para demo
            return self._generate_demo_data()
    
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
        template = self._load_template()
        wr_val, dd_val = data["win_rate_avg"], data["max_drawdown"]
        replacements = {
            "{{fecha}}": data["fecha"], "{{timestamp}}": data["timestamp"], "{{bots_activos}}": str(data["bots_activos"]), "{{bots_pausados}}": str(data["bots_pausados"]),
            "{{total_bots}}": str(data["total_bots"]), "{{win_rate_avg}}": str(data["win_rate_avg"]), "{{wr_class}}": "metric-positive" if wr_val >= 52 else "metric-negative" if wr_val < 45 else "metric-neutral",
            "{{wr_color}}": "#00ff88" if wr_val >= 52 else "#ff4757" if wr_val < 45 else "#ffa502", "{{max_drawdown}}": str(dd_val), "{{dd_bar_width}}": str(min(abs(dd_val) * 5, 100)),
            "{{regime_name}}": data["regime_name"], "{{regime_icon}}": data["regime_icon"], "{{regime_confidence}}": str(data["regime_confidence"]), "{{regime_since}}": data["regime_since"],
            "{{equity_traces}}": self._build_equity_traces(data), "{{adaptation_traces}}": self._build_adaptation_traces(data), "{{regime_traces}}": self._build_regime_traces(data),
            "{{metrics_traces}}": self._build_metrics_traces(data), "{{regret_traces}}": self._build_regret_traces(data), "{{decision_rows}}": self._build_decision_rows(data)
        }
        html = template
        for placeholder, value in replacements.items(): html = html.replace(placeholder, value)
        if output_name is None: output_name = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_path = os.path.join(self.output_dir, output_name)
        with open(output_path, 'w', encoding='utf-8') as f: f.write(html)
        return output_path

if __name__ == "__main__":
    generator = DashboardGenerator()
    generator.generate()