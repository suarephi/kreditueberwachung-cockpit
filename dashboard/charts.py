"""Reusable Plotly charts on the slate / bone palette."""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from . import geo, coords, style


CHOROPLETH_OPACITY = 0.92
MAP_STYLE         = "carto-positron"
MAP_CENTER        = {"lat": 46.83, "lon": 8.20}
MAP_ZOOM          = 6.85


def ch_choropleth(
    df: pd.DataFrame,
    metric_col: str,
    metric_label: str,
    *,
    color_scale=None,
):
    color_scale = color_scale or style.CHOROPLETH_STOPS
    if not df.empty and len(df) > 0:
        rng_low  = df[metric_col].min()
        rng_high = df[metric_col].quantile(0.97)
    else:
        rng_low, rng_high = 0, 1

    fig = px.choropleth_mapbox(
        df,
        geojson=geo.cantons_geojson(),
        locations="canton_code",
        featureidkey="properties.canton_code",
        color=metric_col,
        color_continuous_scale=color_scale,
        range_color=[rng_low, rng_high],
        mapbox_style=MAP_STYLE,
        center=MAP_CENTER,
        zoom=MAP_ZOOM,
        opacity=CHOROPLETH_OPACITY,
        hover_name="canton_name" if "canton_name" in df.columns else "canton_code",
        hover_data={c: True for c in df.columns
                    if c not in ("canton_code", metric_col)} | {metric_col: ":,.1f"},
        labels={metric_col: metric_label},
    )
    fig.update_traces(marker_line_color="#FFFFFF", marker_line_width=0.6)
    fig.update_layout(
        margin=dict(l=0, r=0, t=4, b=0),
        height=520,
        coloraxis_colorbar=dict(
            title=dict(text=metric_label, font=dict(color=style.INK_3, size=11)),
            len=0.6, thickness=12, outlinewidth=0,
            tickfont=dict(color=style.INK_4, family="JetBrains Mono", size=10),
            bgcolor="rgba(255,255,255,0.92)",
        ),
    )
    return fig


def ch_choropleth_with_plz_overlay(
    canton_df: pd.DataFrame,
    plz_df: pd.DataFrame,
    canton_metric: str,
    canton_label: str,
    plz_metric_size: str | None = None,
    plz_metric_color: str | None = None,
    color_scale=None,
):
    fig = ch_choropleth(canton_df, canton_metric, canton_label, color_scale=color_scale)
    if plz_df is not None and not plz_df.empty:
        df = plz_df.copy()
        if plz_metric_size:
            sz = df[plz_metric_size].fillna(0)
            sizes = (sz - sz.min()) / max(sz.max() - sz.min(), 1) * 28 + 6
        else:
            sizes = 9
        scatter = go.Scattermapbox(
            lat=df["lat"], lon=df["lon"],
            mode="markers",
            marker=dict(
                size=sizes,
                color=df[plz_metric_color] if plz_metric_color else style.ACCENT,
                colorscale=[
                    [0.0, "#3B5874"], [0.5, "#9BAFC2"], [1.0, "#B05541"],
                ] if plz_metric_color else None,
                opacity=0.78,
                showscale=False,
            ),
            text=df.apply(lambda r:
                f"<b>{r['city']} · {r['postal_code']}</b><br>"
                f"Kredite: {int(r.get('n_loans', 0)):,}<br>".replace(",", "'") +
                f"Engagement: {r.get('total_outstanding', 0)/1e6:,.1f} Mio. CHF<br>".replace(",", "'") +
                f"Ø Belehnung: {r.get('avg_ltv', 0):.1f} %<br>" +
                f"CHF/m²: {r.get('chf_per_sqm', 0):,.0f}".replace(",", "'"),
                axis=1),
            hoverinfo="text",
            name="PLZ",
        )
        fig.add_trace(scatter)
    return fig


def histogram(values: pd.Series, *, xlabel: str, nbins: int = 32,
              color=None, height: int = 220, danger_threshold: float | None = None,
              warn_threshold: float | None = None):
    """LTV-style histogram. If thresholds set, bins above warn → amber, above danger → red."""
    color = color or style.INK_2
    fig = px.histogram(values, nbins=nbins, color_discrete_sequence=[color])
    fig.update_traces(marker_line_width=0, opacity=0.9)
    fig.update_layout(showlegend=False, xaxis_title=xlabel, yaxis_title="",
                      bargap=0.06, height=height)
    return fig


def severity_bar(df: pd.DataFrame, x: str = "severity", y: str = "n"):
    df = df.copy()
    order = ["info", "low", "medium", "high", "critical"]
    df = df.sort_values(x, key=lambda s: s.map({k: i for i, k in enumerate(order)}))
    label_map = {"info": "Information", "low": "Niedrig", "medium": "Mittel",
                 "high": "Hoch", "critical": "Kritisch"}
    df["label"] = df[x].map(label_map)
    fig = px.bar(df, x="label", y=y, color=x,
                 color_discrete_map=style.SEVERITY_COLORS,
                 category_orders={x: order})
    fig.update_traces(marker_line_width=0)
    fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Ereignisse", height=300)
    return fig


def event_type_bar(df: pd.DataFrame):
    fig = px.bar(df.sort_values("n"), x="n", y="event_type", orientation="h",
                 color_discrete_sequence=[style.ACCENT])
    fig.update_traces(marker_line_width=0)
    fig.update_layout(xaxis_title="Ereignisse", yaxis_title="", height=460)
    return fig


def ltv_dsti_scatter(df: pd.DataFrame):
    fig = px.scatter(
        df, x="ltv_pct", y="dsti_pct",
        color="pd_1y", color_continuous_scale=[
            [0.0, style.SEV_GREEN], [0.5, style.SEV_AMBER], [1.0, style.SEV_RED],
        ],
        size="current_outstanding", size_max=22,
        hover_data=["loan_id", "last_name", "canton", "expected_loss"],
        labels={"ltv_pct": "Belehnung (%)", "dsti_pct": "Tragbarkeit (%)", "pd_1y": "PD 1J"},
    )
    fig.add_hline(y=33, line_dash="dot", line_color=style.INK_4,
                  annotation_text="Tragbarkeit 33 %", annotation_font_color=style.INK_4)
    fig.add_vline(x=80, line_dash="dot", line_color=style.INK_4,
                  annotation_text="Belehnung 80 %", annotation_font_color=style.INK_4)
    fig.update_layout(height=520,
                      coloraxis_colorbar=dict(title="PD 1J", thickness=12, len=0.6))
    return fig


def stress_kpi_lines(kpi_df: pd.DataFrame):
    if kpi_df.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=kpi_df["period"], y=kpi_df["expected_loss_total"]/1e6,
                             name="Erwarteter Verlust (Mio. CHF)", mode="lines+markers",
                             line=dict(width=3, color=style.ACCENT),
                             marker=dict(size=7, color=style.ACCENT)))
    fig.add_trace(go.Scatter(x=kpi_df["period"], y=kpi_df["share_ltv_gt80"]*100,
                             name="Anteil Belehnung > 80 %", mode="lines+markers", yaxis="y2",
                             line=dict(width=2, color=style.INK_3, dash="dot"),
                             marker=dict(size=5, color=style.INK_3)))
    fig.add_trace(go.Scatter(x=kpi_df["period"], y=kpi_df["share_dsti_gt33"]*100,
                             name="Anteil Tragbarkeit > 33 %", mode="lines+markers", yaxis="y2",
                             line=dict(width=2, color=style.INK_4, dash="dot"),
                             marker=dict(size=5, color=style.INK_4)))
    fig.update_layout(
        yaxis=dict(title=dict(text="Erwarteter Verlust (Mio. CHF)",
                              font=dict(color=style.ACCENT))),
        yaxis2=dict(title=dict(text="Anteil (%)", font=dict(color=style.INK_3)),
                    overlaying="y", side="right"),
        legend=dict(orientation="h", y=-0.18),
        height=380,
    )
    return fig


TRANCHE_COLORS = {"saron": style.INK_2, "fix": style.ACCENT, "variable": style.SEV_GREEN}


def tranche_pie(df: pd.DataFrame):
    if df.empty:
        return None
    fig = px.pie(df, values="amount", names="tranche_type",
                 color="tranche_type", color_discrete_map=TRANCHE_COLORS, hole=0.55)
    fig.update_traces(textinfo="label+percent",
                      textfont=dict(color="#FFFFFF", size=12),
                      marker=dict(line=dict(color="#FFFFFF", width=2)))
    fig.update_layout(height=260, showlegend=False)
    return fig


def tranche_ladder_bar(df: pd.DataFrame):
    if df.empty:
        return None
    df = df.copy().sort_values("maturity_date")
    df["label"] = df.apply(
        lambda r: f"{r['tranche_type'].upper()} · {r['amount']/1000:,.0f}k @ "
                  f"{r['interest_rate_pct']:.2f} %".replace(",", "'"),
        axis=1,
    )
    fig = go.Figure()
    for _, r in df.iterrows():
        c = TRANCHE_COLORS.get(r["tranche_type"], style.INK_3)
        fig.add_trace(go.Scatter(
            x=[r["rate_fixing_date"], r["maturity_date"]],
            y=[r["label"], r["label"]],
            mode="lines+markers",
            line=dict(color=c, width=14),
            marker=dict(size=10, color=c, line=dict(color="#FFFFFF", width=2)),
            hoverinfo="text",
            text=f"{r['tranche_type']} · {r['amount']/1000:,.0f}k CHF · "
                 f"{r['interest_rate_pct']:.2f} %"
                 f"<br>{r['rate_fixing_date']} → {r['maturity_date']}",
            showlegend=False,
        ))
    fig.update_layout(height=80 + 38 * len(df), xaxis_title="", yaxis_title="",
                      plot_bgcolor=style.SURFACE)
    return fig


def tranche_count_distribution(df: pd.DataFrame):
    if df.empty:
        return None
    fig = px.bar(df, x="n_tranches", y="n_loans", text="n_loans",
                 color_discrete_sequence=[style.INK_2])
    fig.update_traces(texttemplate="%{text:,}", textposition="outside",
                      marker_line_width=0,
                      textfont=dict(color=style.INK_4, family="JetBrains Mono"))
    fig.update_layout(height=240, xaxis_title="Tranchen pro Kredit",
                      yaxis_title="Kredite", showlegend=False, bargap=0.40)
    return fig


def valuation_history(df: pd.DataFrame):
    if df.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(df["valuation_date"]) + list(df["valuation_date"])[::-1],
        y=list(df["confidence_band_high"]) + list(df["confidence_band_low"])[::-1],
        fill="toself", fillcolor="rgba(59,88,116,0.08)", line=dict(width=0),
        name="Konfidenzband", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=df["valuation_date"], y=df["market_value"],
        mode="lines+markers", name="Marktwert",
        line=dict(width=3, color=style.ACCENT),
        marker=dict(size=7, color=style.ACCENT),
    ))
    fig.add_trace(go.Scatter(
        x=df["valuation_date"], y=df["mortgage_lending_value"],
        mode="lines+markers", name="Belehnungswert",
        line=dict(width=2, dash="dot", color=style.SEV_RED),
        marker=dict(size=6, color=style.SEV_RED),
    ))
    fig.update_layout(xaxis_title="", yaxis_title="CHF",
                      height=380, legend=dict(orientation="h", y=-0.18))
    return fig
