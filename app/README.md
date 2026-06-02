# NVIDIA FP&A Platform v3.0 — Light Theme Edition

## Overview

**Institutional-grade financial valuation dashboard** for NVIDIA with:
- ✅ Light theme (white background, accessible contrast)
- ✅ Filter bar (date range, segments, metrics, view modes)
- ✅ Annotated charts (callout boxes, tooltips)
- ✅ Donut center labels (percentage metrics)
- ✅ Combo stacked + line charts (revenue trends)
- ✅ Card shadows (subtle depth)
- ✅ Two-tone card headers (gradient accents)
- ✅ Big % KPI tiles (large, prominent displays)
- ✅ Waterfall charts with floating bars
- ✅ 3-scenario DCF modeling (base, upside, downside)
- ✅ Scenario-aware sensitivity matrix
- ✅ Comparable analysis + peer multiples

---

## File Structure

```
app/
├── app.py                    # Main entry point, routing, filter bar
├── components/
│   ├── __init__.py
│   ├── kpi_tile.py          # 3-scenario KPI cards (big %)
│   ├── sensitivity.py       # WACC/g sensitivity matrix
│   ├── drivers.py           # DCF bridge waterfall
│   ├── interactions.py      # WACC/g combinations
│   ├── summary.py           # DCF summary table
│   └── narrative.py         # Auto-generated commentary
├── views/
│   ├── __init__.py
│   ├── segments.py          # Revenue + geo, combo chart
│   ├── three_statement.py   # Income statement + FCFF
│   ├── kpis.py             # Traffic lights + margins
│   └── comps.py            # Peer analysis
├── style/
│   ├── __init__.py
│   └── theme.css           # Light theme (white bg, shadows, gradients)
```

---

## Setup & Deployment

### 1. Install Dependencies

```bash
pip install streamlit plotly pandas
```

### 2. Configure Streamlit

Create `.streamlit/config.toml`:

```toml
[theme]
base = "light"
primaryColor = "#0891b2"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f8fafc"
textColor = "#0f1419"
font = "sans serif"

[client]
showErrorDetails = false
toolbarMode = "minimal"

[server]
headless = true
port = 8501
```

### 3. Run the Dashboard

```bash
streamlit run app/app.py
```

Open browser → `http://localhost:8501`

---

## Key Features

### Light Theme
- **Colors**: White (#ffffff) background, soft grays (#f8fafc), dark text (#0f1419)
- **Accents**: Cyan (#0891b2), green (#10b981), red (#ef4444), amber (#f59e0b)
- **Shadows**: `--shadow-sm`, `--shadow-md`, `--shadow-lg` for card depth
- **Borders**: Soft dividers with `var(--br2)` (1px, light gray)

### Filter Bar
- Date range selector (FY2025, multi-year)
- Segment multiselect (Data Center, Gaming, etc.)
- Metrics dropdown (Revenue, EBITDA, FCF, Margins)
- View mode toggle (Summary, Detailed, Comparative)

### Chart Types
1. **KPI Cards** — Large %, big font, gradient top border, glow on active
2. **Stacked Bars** — Segment breakdown with labels outside narrow bars
3. **Waterfall** — FCFF build-up with floating bars, color-coded
4. **Combo Chart** — Stacked bars (segments) + line overlay (total revenue)
5. **Sensitivity Grid** — 9×9 WACC/g matrix, scenario-colored cells
6. **Line Charts** — Margin trends with annotations (FY2023 trough marked)

### Scenarios
- **Base**: WACC 12.91%, g 3.675%, standard assumptions
- **Upside**: WACC 11.91%, g 4.50%, +95% DC growth
- **Downside**: WACC 13.91%, g 3.00%, +50% DC growth

Each scenario shows:
- Implied share price (in KPI card)
- Active cell highlighting in sensitivity matrix
- Scenario-specific driver decomposition
- Auto-generated narrative commentary

---

## Data Flow

1. **Pipeline**: `modeling.engine.run_pipeline(scenario)` → returns dict with:
   - `dcf_valuation`: DCF metrics (price, WACC, terminal value, etc.)
   - `fcff`: DataFrame (years, FCFF, revenue, etc.)
   - `income_statement`: DataFrame (gross margin, EBIT, etc.)

2. **Session State**:
   - `st.session_state.scenario`: Active scenario (base/upside/downside)
   - `st.session_state.page`: Current tab (valuation/segments/3-statement/kpis/comps)

3. **Rendering**:
   - Components read from `results[scenario]` dict
   - CSS applied globally via `theme.css`
   - Inline styles override CSS for scenario colors

---

## Customization

### Change Colors
Edit `style/theme.css`:
```css
:root {
  --accent: #0891b2;      /* Primary accent */
  --green: #10b981;       /* Positive color */
  --red: #ef4444;         /* Negative color */
  /* ... */
}
```

### Update Assumptions
Edit component files (e.g., `kpi_tile.py`):
```python
_META = {
    "base": {
        "label": "Base case",
        "accent": "linear-gradient(90deg,#3b82f6,#60a5fa)",
        # ...
    }
}
```

### Add Charts
1. Create new component in `components/new_chart.py`
2. Import in `app.py`
3. Call render function in appropriate view or on valuation page

---

## Troubleshooting

**Chart not rendering?**
- Check `data_types` in Plotly calls (use `go.Bar`, `go.Scatter`, etc.)
- Verify `_L` layout dict is applied: `fig.update_layout(**_L, ...)`
- Ensure `config={"displayModeBar": False}` to hide Plotly toolbar

**Colors look wrong?**
- Check CSS variable spelling in `theme.css`
- Verify color hex codes (#0f1419, not #0f1a19)
- Inline styles override CSS — if inline style set, won't use CSS var

**Sidebar or topbar missing?**
- `st.set_page_config(initial_sidebar_state="collapsed")` hides sidebar
- Topbar rendered in `_render_topbar()` using custom HTML
- Both use `st.markdown(..., unsafe_allow_html=True)`

**Filter bar not working?**
- Filter selections stored in `filters` dict returned from `_render_filter_bar()`
- Currently passed to `_render_valuation()` but not used in components
- To implement: pass filters to render functions and conditionally show data

---

## Performance Tips

1. **Caching**: Use `@st.cache_data` for `_load_results()` to avoid re-running pipeline
2. **Charts**: Keep to <10 traces per chart; use `config={"displayModeBar": False}`
3. **Tables**: Use HTML tables (not DataFrames) for better styling control
4. **Responsive**: CSS includes `@media (max-width: ...)` for mobile

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 3.0 | 2025-05-24 | Light theme, filter bar, combo charts, annotations |
| 2.1 | 2025-10-17 | Active scenario highlighting, fixes for sidebar/topbar |
| 2.0 | 2025-09-01 | Initial DCF dashboard release |

---

## Support

For issues, questions, or feature requests:
- Check `app.py` for session state management
- Review `theme.css` for styling reference
- Inspect component files for rendering patterns
- Test locally with `streamlit run app/app.py --logger.level=debug`

---

**Built by Aditya Gupta** | NVIDIA FP&A Platform v3.0 | October 2025
