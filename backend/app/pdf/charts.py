"""Tiny inline-SVG line charts for PDFs.

Only digits and short numeric dates are drawn inside the SVG; titles and Arabic labels are
regular HTML around it, where WeasyPrint shapes Arabic correctly.
"""
from datetime import date
from html import escape


def _fmt(v: float) -> str:
    return f"{v:.0f}" if abs(v) >= 100 or float(v).is_integer() else f"{v:.1f}"


def line_chart(points: list[tuple[date, float]], *, rtl: bool, color: str = "#F2550D", width: int = 520, height: int = 170) -> str:
    if not points:
        return ""
    pad_l, pad_r, pad_t, pad_b = (12, 40, 10, 22) if rtl else (40, 12, 10, 22)
    values = [v for _, v in points]
    lo, hi = min(values), max(values)
    if hi == lo:
        lo, hi = lo - 1, hi + 1
    span = hi - lo
    lo, hi = lo - span * 0.1, hi + span * 0.1
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    n = len(points)

    def x(i: int) -> float:
        frac = 0.5 if n == 1 else i / (n - 1)
        if rtl:  # time flows right → left in Arabic
            frac = 1 - frac
        return pad_l + frac * plot_w

    def y(v: float) -> float:
        return pad_t + (1 - (v - lo) / (hi - lo)) * plot_h

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    # horizontal grid + y labels
    axis_x = width - pad_r + 4 if rtl else pad_l - 4
    anchor = "start" if rtl else "end"
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        yy = y(v)
        parts.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width - pad_r}" y2="{yy:.1f}" stroke="#E4E1DB" stroke-width="0.6"/>')
        parts.append(f'<text x="{axis_x}" y="{yy + 3:.1f}" font-size="8" fill="#686870" text-anchor="{anchor}" font-family="Plex">{_fmt(v)}</text>')
    # x labels (at most ~8)
    step = max(1, n // 8)
    for i, (d, _) in enumerate(points):
        if i % step == 0 or i == n - 1:
            parts.append(
                f'<text x="{x(i):.1f}" y="{height - 6}" font-size="8" fill="#686870" text-anchor="middle" font-family="Plex">{d.day}/{d.month}</text>'
            )
    path = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(points))
    parts.append(f'<path d="{path}" fill="none" stroke="{escape(color)}" stroke-width="2" stroke-linejoin="round"/>')
    for i, (_, v) in enumerate(points):
        parts.append(f'<circle cx="{x(i):.1f}" cy="{y(v):.1f}" r="2.6" fill="{escape(color)}"/>')
    parts.append("</svg>")
    return "".join(parts)
