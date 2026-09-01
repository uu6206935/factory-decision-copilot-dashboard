/* Lightweight dependency-free SVG chart renderers for the factory dashboard.
   Every function takes a container element + a plain-data options object and
   writes a self-contained <svg>. No canvas, no external chart library, so the
   dashboard keeps working fully offline. */
(function (global) {
  const NS = "http://www.w3.org/2000/svg";
  const FONT = "font-family:Inter,'Noto Sans JP',sans-serif";

  function el(tag, attrs, children) {
    const node = document.createElementNS(NS, tag);
    for (const k in attrs || {}) node.setAttribute(k, attrs[k]);
    (children || []).forEach((c) => c && node.appendChild(c));
    return node;
  }

  function text(x, y, str, attrs) {
    const t = el("text", { x, y, style: FONT, ...attrs });
    t.textContent = str;
    return t;
  }

  function niceMax(v) {
    if (v <= 0) return 10;
    const mag = Math.pow(10, Math.floor(Math.log10(v)));
    const n = v / mag;
    let f = 10;
    if (n <= 1) f = 1;
    else if (n <= 2) f = 2;
    else if (n <= 5) f = 5;
    return f * mag;
  }

  function mount(container, svg) {
    container.innerHTML = "";
    container.appendChild(svg);
  }

  // ------------------------------------------------------------------
  // Multi-series line chart (OEE trend, torque/angle time series)
  // ------------------------------------------------------------------
  function lineChart(container, opts) {
    const W = opts.width || 720, H = opts.height || 260;
    const padL = 40, padR = 14, padT = 14, padB = 26;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const labels = opts.labels || [];
    const seriesNames = Object.keys(opts.series || {});
    let yMin = opts.yMin, yMax = opts.yMax;
    if (yMin === undefined || yMax === undefined) {
      let lo = Infinity, hi = -Infinity;
      seriesNames.forEach((k) => (opts.series[k] || []).forEach((v) => { lo = Math.min(lo, v); hi = Math.max(hi, v); }));
      if (!isFinite(lo)) { lo = 0; hi = 1; }
      const pad = (hi - lo) * 0.12 || 1;
      yMin = opts.yMin !== undefined ? opts.yMin : Math.max(0, lo - pad);
      yMax = opts.yMax !== undefined ? opts.yMax : hi + pad;
    }
    const n = labels.length || 1;
    const x = (i) => padL + (plotW * i) / Math.max(1, n - 1);
    const y = (v) => padT + plotH * (1 - (v - yMin) / (yMax - yMin || 1));

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, preserveAspectRatio: "xMidYMid meet" });
    const grid = el("g");
    const ticks = 4;
    for (let t = 0; t <= ticks; t++) {
      const v = yMin + ((yMax - yMin) * t) / ticks;
      const gy = y(v);
      grid.appendChild(el("line", { x1: padL, x2: W - padR, y1: gy, y2: gy, stroke: "var(--chart-grid)", "stroke-width": 1 }));
      grid.appendChild(text(padL - 8, gy + 3, Math.round(v), { "text-anchor": "end", "font-size": 10, fill: "var(--chart-axis-text)" }));
    }
    svg.appendChild(grid);

    const xLabelEvery = Math.max(1, Math.ceil(n / (opts.xLabelCount || 8)));
    labels.forEach((lab, i) => {
      if (i % xLabelEvery !== 0 && i !== n - 1) return;
      svg.appendChild(text(x(i), H - 6, lab, { "text-anchor": "middle", "font-size": 10, fill: "var(--chart-axis-text)" }));
    });

    seriesNames.forEach((name) => {
      const vals = opts.series[name];
      const color = (opts.colors || {})[name] || "#6fa0ff";
      const d = vals.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
      svg.appendChild(el("path", { d, fill: "none", stroke: color, "stroke-width": opts.strokeWidth || 2, "stroke-linejoin": "round", "stroke-linecap": "round", opacity: opts.opacity ? opts.opacity[name] || 1 : 1 }));
      if (opts.markers) {
        vals.forEach((v, i) => svg.appendChild(el("circle", { cx: x(i), cy: y(v), r: opts.markerRadius || 3.5, fill: color })));
      }
    });

    mount(container, svg);
    if (opts.legend !== false) renderLegend(container, seriesNames.map((n2) => ({ label: (opts.legendLabels || {})[n2] || n2, color: (opts.colors || {})[n2] || "#6fa0ff" })));
  }

  function renderLegend(container, items) {
    const wrap = document.createElement("div");
    wrap.className = "chart-legend";
    items.forEach((it) => {
      const span = document.createElement("span");
      span.innerHTML = `<i style="background:${it.color}"></i>${it.label}`;
      wrap.appendChild(span);
    });
    container.appendChild(wrap);
  }

  // ------------------------------------------------------------------
  // Stacked bar chart with an optional dual-axis line overlay
  // (production progress / monthly uptime-downtime)
  // ------------------------------------------------------------------
  function stackedBarLine(container, opts) {
    const W = opts.width || 720, H = opts.height || 260;
    const padL = 44, padR = opts.line ? 44 : 14, padT = 14, padB = 26;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const labels = opts.labels || [];
    const n = labels.length || 1;
    const barCats = Object.keys(opts.series || {});
    const totals = labels.map((_, i) => barCats.reduce((s, k) => s + (opts.series[k][i] || 0), 0));
    const barMax = opts.barMax || niceMax(Math.max(...totals, 1));
    const bw = (plotW / n) * (opts.barWidthRatio || 0.62);
    const x = (i) => padL + (plotW * (i + 0.5)) / n;
    const yBar = (v) => padT + plotH * (1 - v / barMax);

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, preserveAspectRatio: "xMidYMid meet" });

    const ticks = 4;
    for (let t = 0; t <= ticks; t++) {
      const v = (barMax * t) / ticks;
      const gy = yBar(v);
      svg.appendChild(el("line", { x1: padL, x2: W - padR, y1: gy, y2: gy, stroke: "var(--chart-grid)", "stroke-width": 1 }));
      svg.appendChild(text(padL - 8, gy + 3, Math.round(v), { "text-anchor": "end", "font-size": 10, fill: "var(--chart-axis-text)" }));
    }

    labels.forEach((lab, i) => {
      let stackY = padT + plotH;
      barCats.forEach((cat) => {
        const v = opts.series[cat][i] || 0;
        const hgt = (plotH * v) / barMax;
        stackY -= hgt;
        svg.appendChild(el("rect", { x: x(i) - bw / 2, y: stackY, width: bw, height: Math.max(0, hgt), fill: (opts.colors || {})[cat] || "#6fa0ff" }));
      });
      const everyN = Math.max(1, Math.ceil(n / (opts.xLabelCount || 12)));
      if (i % everyN === 0 || i === n - 1) svg.appendChild(text(x(i), H - 6, lab, { "text-anchor": "middle", "font-size": 9.5, fill: "var(--chart-axis-text)" }));
    });

    if (opts.line) {
      const lineMax = opts.lineMax || niceMax(Math.max(...opts.line.values, ...(opts.line.values2 || [0])));
      const yLine = (v) => padT + plotH * (1 - v / lineMax);
      [{ vals: opts.line.values, color: opts.line.color || "#e6534a" }, opts.line.values2 && { vals: opts.line.values2, color: opts.line.color2 || "#3b7cff" }]
        .filter(Boolean)
        .forEach(({ vals, color }) => {
          const d = vals.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${yLine(v).toFixed(1)}`).join(" ");
          svg.appendChild(el("path", { d, fill: "none", stroke: color, "stroke-width": 2.2, "stroke-linecap": "round" }));
        });
      const rticks = 4;
      for (let t = 0; t <= rticks; t++) {
        const v = (lineMax * t) / rticks;
        svg.appendChild(text(W - padR + 6, yLine(v) + 3, formatCompact(v), { "font-size": 10, fill: "var(--chart-axis-text)" }));
      }
    }

    mount(container, svg);
    const legendItems = barCats.map((c) => ({ label: (opts.legendLabels || {})[c] || c, color: (opts.colors || {})[c] || "#6fa0ff" }));
    if (opts.line) legendItems.push({ label: opts.line.label || "実績", color: opts.line.color || "#e6534a" });
    if (opts.line && opts.line.label2) legendItems.push({ label: opts.line.label2, color: opts.line.color2 || "#3b7cff" });
    if (opts.legend !== false) renderLegend(container, legendItems);
  }

  function formatCompact(v) {
    if (v >= 1000) return Math.round(v / 1000) + "K";
    return String(Math.round(v));
  }

  // ------------------------------------------------------------------
  // Donut / pie chart (stop-reason breakdown, prediction factors)
  // ------------------------------------------------------------------
  function donut(container, opts) {
    const size = opts.size || 220;
    const cx = size / 2, cy = size / 2, r = size / 2 - 8, inner = r * (opts.innerRatio || 0.58);
    const total = (opts.segments || []).reduce((s, seg) => s + seg.value, 0) || 1;
    const svg = el("svg", { viewBox: `0 0 ${size} ${size}`, width: "100%", height: size, preserveAspectRatio: "xMidYMid meet" });
    let angle = -Math.PI / 2;
    (opts.segments || []).forEach((seg) => {
      const frac = seg.value / total;
      const a0 = angle, a1 = angle + frac * Math.PI * 2;
      angle = a1;
      const large = a1 - a0 > Math.PI ? 1 : 0;
      const p0o = [cx + r * Math.cos(a0), cy + r * Math.sin(a0)];
      const p1o = [cx + r * Math.cos(a1), cy + r * Math.sin(a1)];
      const p1i = [cx + inner * Math.cos(a1), cy + inner * Math.sin(a1)];
      const p0i = [cx + inner * Math.cos(a0), cy + inner * Math.sin(a0)];
      const d = `M${p0o[0]},${p0o[1]} A${r},${r} 0 ${large} 1 ${p1o[0]},${p1o[1]} L${p1i[0]},${p1i[1]} A${inner},${inner} 0 ${large} 0 ${p0i[0]},${p0i[1]} Z`;
      const path = el("path", { d, fill: seg.color });
      const title = el("title");
      title.textContent = `${seg.label}: ${seg.value}%`;
      path.appendChild(title);
      svg.appendChild(path);
      if (opts.showLabels !== false && frac > 0.05) {
        const mid = (a0 + a1) / 2;
        const lr = (r + inner) / 2;
        svg.appendChild(text(cx + lr * Math.cos(mid), cy + lr * Math.sin(mid) + 4, `${seg.value}%`, { "text-anchor": "middle", "font-size": 11.5, fill: "#fff", "font-weight": 700 }));
      }
    });
    if (opts.centerLabel || opts.centerValue !== undefined) {
      svg.appendChild(text(cx, cy - 3, opts.centerValue !== undefined ? String(opts.centerValue) : "", { "text-anchor": "middle", "font-size": 22, "font-weight": 800, fill: "var(--text)" }));
      svg.appendChild(text(cx, cy + 16, opts.centerLabel || "", { "text-anchor": "middle", "font-size": 10, fill: "var(--muted)" }));
    }
    mount(container, svg);
    if (opts.legend === false) return;
    const items = (opts.segments || []).map((s) => ({ label: opts.legendPercent ? `${s.label} ${s.value}%` : s.label, color: s.color }));
    if (opts.legendLayout === "list") renderLegendList(container, items, opts.legendTitle);
    else renderLegend(container, items);
  }

  function renderLegendList(container, items, title) {
    const wrap = document.createElement("div");
    wrap.className = "chart-legend-list";
    if (title) {
      const h = document.createElement("div");
      h.className = "chart-legend-list-title";
      h.textContent = title;
      wrap.appendChild(h);
    }
    items.forEach((it) => {
      const row = document.createElement("div");
      row.className = "chart-legend-list-row";
      row.innerHTML = `<i style="background:${it.color}"></i><span>${it.label}</span>`;
      wrap.appendChild(row);
    });
    container.appendChild(wrap);
  }

  // ------------------------------------------------------------------
  // Gauge / dial (rotation speed, flow rate, anomaly score)
  // ------------------------------------------------------------------
  function gauge(container, opts) {
    const size = opts.size || 200;
    const cx = size / 2, cy = size / 2 + size * 0.08, r = size * 0.42;
    const min = opts.min !== undefined ? opts.min : 0;
    const max = opts.max !== undefined ? opts.max : 100;
    const value = Math.max(min, Math.min(max, opts.value));
    const startA = Math.PI * 0.82, endA = Math.PI * 2.18; // ~148deg sweep on each side
    const frac = (value - min) / (max - min || 1);
    const valA = startA + (endA - startA) * frac;
    const arcPoint = (a, radius) => [cx + radius * Math.cos(a), cy + radius * Math.sin(a)];
    const svg = el("svg", { viewBox: `0 0 ${size} ${size}`, width: "100%", height: size, preserveAspectRatio: "xMidYMid meet" });

    const zones = opts.zones || [{ upTo: 1, color: "var(--chart-grid)" }];
    let za = startA;
    const totalSweep = endA - startA;
    zones.forEach((z) => {
      const zEndA = startA + totalSweep * z.upTo;
      const large = zEndA - za > Math.PI ? 1 : 0;
      const p0 = arcPoint(za, r), p1 = arcPoint(zEndA, r);
      svg.appendChild(el("path", { d: `M${p0[0]},${p0[1]} A${r},${r} 0 ${large} 1 ${p1[0]},${p1[1]}`, fill: "none", stroke: z.color, "stroke-width": 12, "stroke-linecap": "butt" }));
      za = zEndA;
    });

    const needleLen = r * 0.86;
    const tip = arcPoint(valA, needleLen);
    svg.appendChild(el("line", { x1: cx, y1: cy, x2: tip[0], y2: tip[1], stroke: "var(--text)", "stroke-width": 3, "stroke-linecap": "round" }));
    svg.appendChild(el("circle", { cx, cy, r: 5, fill: "var(--text)" }));

    svg.appendChild(text(cx, cy + size * 0.22, opts.valueLabel !== undefined ? opts.valueLabel : value, { "text-anchor": "middle", "font-size": size * 0.15, "font-weight": 800, fill: "var(--text)" }));
    if (opts.unit) svg.appendChild(text(cx, cy + size * 0.34, opts.unit, { "text-anchor": "middle", "font-size": 11, fill: "var(--muted)" }));
    svg.appendChild(text(cx - r, cy + 14, String(min), { "text-anchor": "middle", "font-size": 10, fill: "var(--chart-axis-text)" }));
    svg.appendChild(text(cx + r, cy + 14, String(max), { "text-anchor": "middle", "font-size": 10, fill: "var(--chart-axis-text)" }));

    mount(container, svg);
  }

  // ------------------------------------------------------------------
  // Horizontal segmented status timeline (today's run/stop per device)
  // ------------------------------------------------------------------
  function timeline(container, opts) {
    const rows = opts.rows || [];
    const rowH = opts.rowHeight || 26, gap = 8;
    const W = opts.width || 720;
    const labelW = 56;
    const H = rows.length * (rowH + gap) + 10;
    const toMin = (t) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
    const dayStart = toMin(opts.dayStart || "08:00"), dayEnd = toMin(opts.dayEnd || "20:00");
    const plotW = W - labelW - 10;
    const x = (t) => labelW + (plotW * (toMin(t) - dayStart)) / (dayEnd - dayStart);

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, preserveAspectRatio: "xMidYMid meet" });
    rows.forEach((row, ri) => {
      const y = 6 + ri * (rowH + gap);
      svg.appendChild(text(0, y + rowH / 2 + 4, row.label, { "font-size": 11, fill: "var(--soft)", "font-weight": 700 }));
      svg.appendChild(el("rect", { x: labelW, y, width: plotW, height: rowH, rx: 0, fill: "var(--chart-grid)" }));
      row.segments.forEach((seg) => {
        const sx = x(seg.start), ex = x(seg.end);
        const rect = el("rect", { x: sx, y, width: Math.max(1, ex - sx), height: rowH, rx: 0, fill: (opts.stateColors || {})[seg.state] || "#666" });
        const title = el("title");
        title.textContent = `${seg.state} ${seg.start}-${seg.end}`;
        rect.appendChild(title);
        svg.appendChild(rect);
      });
    });
    mount(container, svg);
    if (opts.legend !== false) {
      const states = [...new Set(rows.flatMap((r) => r.segments.map((s) => s.state)))];
      renderLegend(container, states.map((s) => ({ label: s, color: (opts.stateColors || {})[s] || "#666" })));
    }
  }

  // ------------------------------------------------------------------
  // Pareto chart: bars (left axis) + cumulative % line (right axis, 0-100)
  // ------------------------------------------------------------------
  function pareto(container, opts) {
    const W = opts.width || 480, H = opts.height || 240;
    const padL = 40, padR = 34, padT = 14, padB = 30;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const labels = opts.labels || [];
    const n = labels.length || 1;
    const barMax = niceMax(Math.max(...opts.values, 1));
    const bw = (plotW / n) * 0.5;
    const x = (i) => padL + (plotW * (i + 0.5)) / n;
    const yBar = (v) => padT + plotH * (1 - v / barMax);
    const yPct = (v) => padT + plotH * (1 - v / 100);

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, preserveAspectRatio: "xMidYMid meet" });
    for (let t = 0; t <= 4; t++) {
      const gy = padT + (plotH * t) / 4;
      svg.appendChild(el("line", { x1: padL, x2: W - padR, y1: gy, y2: gy, stroke: "var(--chart-grid)", "stroke-width": 1 }));
      svg.appendChild(text(padL - 8, gy + 3, Math.round(barMax - (barMax * t) / 4), { "text-anchor": "end", "font-size": 9.5, fill: "var(--chart-axis-text)" }));
      svg.appendChild(text(W - padR + 6, gy + 3, Math.round(100 - (100 * t) / 4), { "font-size": 9.5, fill: "var(--chart-axis-text)" }));
    }
    labels.forEach((lab, i) => {
      const hgt = plotH * (opts.values[i] / barMax);
      svg.appendChild(el("rect", { x: x(i) - bw / 2, y: yBar(opts.values[i]), width: bw, height: hgt, fill: opts.barColor || "#3b7cff", rx: 0 }));
      svg.appendChild(text(x(i), H - 8, lab, { "text-anchor": "middle", "font-size": 9.5, fill: "var(--chart-axis-text)" }));
    });
    const d = opts.cumPct.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${yPct(v).toFixed(1)}`).join(" ");
    svg.appendChild(el("path", { d, fill: "none", stroke: opts.lineColor || "#f0a63e", "stroke-width": 2.2 }));
    opts.cumPct.forEach((v, i) => svg.appendChild(el("circle", { cx: x(i), cy: yPct(v), r: 3, fill: opts.lineColor || "#f0a63e" })));
    mount(container, svg);
  }

  // ------------------------------------------------------------------
  // Dual-axis filled area/line chart with an optional horizontal
  // threshold line (anomaly-detection style monitoring chart)
  // ------------------------------------------------------------------
  function dualAxisAreaChart(container, opts) {
    const W = opts.width || 1200, H = opts.height || 300;
    const padL = 44, padR = 46, padT = 16, padB = 26;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const labels = opts.labels || [];
    const n = labels.length || 1;
    const x = (i) => padL + (plotW * i) / Math.max(1, n - 1);

    const left = opts.left, right = opts.right;
    const leftMax = left.max !== undefined ? left.max : niceMax(Math.max(...left.values));
    const leftMin = left.min || 0;
    const rightMax = right.max !== undefined ? right.max : niceMax(Math.max(...right.values));
    const rightMin = right.min || 0;
    const yLeft = (v) => padT + plotH * (1 - (v - leftMin) / (leftMax - leftMin || 1));
    const yRight = (v) => padT + plotH * (1 - (v - rightMin) / (rightMax - rightMin || 1));

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, preserveAspectRatio: "xMidYMid meet" });

    const ticks = 4;
    for (let t = 0; t <= ticks; t++) {
      const lv = leftMin + ((leftMax - leftMin) * t) / ticks;
      const rv = rightMin + ((rightMax - rightMin) * t) / ticks;
      const gy = yLeft(lv);
      svg.appendChild(el("line", { x1: padL, x2: W - padR, y1: gy, y2: gy, stroke: "var(--chart-grid)", "stroke-width": 1 }));
      svg.appendChild(text(padL - 8, gy + 3, Math.round(lv), { "text-anchor": "end", "font-size": 10, fill: "var(--chart-axis-text)" }));
      svg.appendChild(text(W - padR + 8, yRight(rv) + 3, Math.round(rv), { "font-size": 10, fill: "var(--chart-axis-text)" }));
    }

    const xLabelEvery = Math.max(1, Math.ceil(n / (opts.xLabelCount || 14)));
    (opts.dateLabels || labels).forEach((lab, i) => {
      if (i % xLabelEvery !== 0 && i !== n - 1) return;
      svg.appendChild(text(x(i), H - 6, lab, { "text-anchor": "middle", "font-size": 10, fill: "var(--chart-axis-text)" }));
    });

    [{ s: left, y: yLeft }, { s: right, y: yRight }].forEach(({ s, y }) => {
      const line = s.values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
      const area = `${line} L${x(n - 1).toFixed(1)},${(padT + plotH).toFixed(1)} L${x(0).toFixed(1)},${(padT + plotH).toFixed(1)} Z`;
      svg.appendChild(el("path", { d: area, fill: s.color, opacity: 0.22, stroke: "none" }));
      svg.appendChild(el("path", { d: line, fill: "none", stroke: s.color, "stroke-width": 1.6 }));
    });

    if (opts.threshold) {
      const th = opts.threshold;
      const ty = th.axis === "left" ? yLeft(th.value) : yRight(th.value);
      svg.appendChild(el("line", { x1: padL, x2: W - padR, y1: ty, y2: ty, stroke: th.color || "#e6197a", "stroke-width": 2 }));
    }

    mount(container, svg);
    if (opts.legend !== false) {
      const items = [{ label: left.label, color: left.color }];
      if (opts.threshold) items.push({ label: opts.threshold.label || "閾値", color: opts.threshold.color || "#e6197a" });
      items.push({ label: right.label, color: right.color });
      renderLegend(container, items);
    }
  }

  global.FDCharts = { lineChart, stackedBarLine, donut, gauge, timeline, pareto, dualAxisAreaChart };
})(window);
