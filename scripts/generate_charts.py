import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
OUTPUT = ROOT / "docs" / "figures"
WIDTH, HEIGHT = 760, 440
LEFT, TOP, RIGHT, BOTTOM = 70, 45, 25, 70


def load_measurements() -> list[dict]:
    with (ROOT / "benchmark.json").open() as benchmark_file:
        return json.load(benchmark_file)["measurements"]


def svg_start(title: str, y_label: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{WIDTH / 2}" y="25" text-anchor="middle" font-family="sans-serif" font-size="18" font-weight="bold">{title}</text>',
        f'<text x="18" y="{HEIGHT / 2}" transform="rotate(-90 18 {HEIGHT / 2})" text-anchor="middle" font-family="sans-serif" font-size="13">{y_label}</text>',
        f'<line x1="{LEFT}" y1="{TOP}" x2="{LEFT}" y2="{HEIGHT - BOTTOM}" stroke="#333"/>',
        f'<line x1="{LEFT}" y1="{HEIGHT - BOTTOM}" x2="{WIDTH - RIGHT}" y2="{HEIGHT - BOTTOM}" stroke="#333"/>',
    ]


def point(index: int, value: float, count: int, y_max: float) -> tuple[float, float]:
    x = LEFT + index * (WIDTH - LEFT - RIGHT) / max(count - 1, 1)
    y = HEIGHT - BOTTOM - value / y_max * (HEIGHT - TOP - BOTTOM)
    return x, y


def line_chart(filename: str, title: str, y_label: str, values: list[float], ideal: list[float]) -> None:
    y_max = max(max(values), max(ideal), 1) * 1.15
    lines = svg_start(title, y_label)
    workers = [1, 2, 4, 8]
    for index, worker in enumerate(workers):
        x, _ = point(index, 0, len(workers), y_max)
        lines.append(f'<text x="{x}" y="{HEIGHT - BOTTOM + 25}" text-anchor="middle" font-family="sans-serif" font-size="12">{worker}</text>')
    for series, color, dash in ((ideal, "#888", 'stroke-dasharray="6 4"'), (values, "#2563eb", "")):
        points = " ".join(f"{point(i, value, len(series), y_max)[0]},{point(i, value, len(series), y_max)[1]}" for i, value in enumerate(series))
        lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3" {dash}/>')
        for i, value in enumerate(series):
            x, y = point(i, value, len(series), y_max)
            lines.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{color}"/>')
    lines.append('</svg>')
    (OUTPUT / filename).write_text("\n".join(lines))


def phase_chart(items: list[dict]) -> None:
    workers = [item["workers"] for item in items]
    phases = list(items[0]["phase_percentages"])
    colors = ["#2563eb", "#16a34a", "#d97706", "#dc2626"]
    lines = svg_start("Desglose temporal por fase", "Porcentaje del tiempo")
    bar_width = 75
    gap = (WIDTH - LEFT - RIGHT) / len(workers)
    for index, worker in enumerate(workers):
        x = LEFT + index * gap + gap / 2 - bar_width / 2
        bottom = HEIGHT - BOTTOM
        for phase, color in zip(phases, colors):
            value = items[index]["phase_percentages"][phase]
            height = value / 100 * (HEIGHT - TOP - BOTTOM)
            bottom -= height
            lines.append(f'<rect x="{x}" y="{bottom}" width="{bar_width}" height="{height}" fill="{color}"/>')
        lines.append(f'<text x="{x + bar_width / 2}" y="{HEIGHT - BOTTOM + 25}" text-anchor="middle" font-family="sans-serif" font-size="12">{worker}</text>')
    lines.append('</svg>')
    (OUTPUT / "phase_breakdown.svg").write_text("\n".join(lines))


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    items = load_measurements()
    line_chart("speedup.svg", "Speedup de la ingesta", "Speedup", [item["speedup"] for item in items], [item["workers"] for item in items])
    line_chart("efficiency.svg", "Eficiencia paralela", "Eficiencia", [item["efficiency"] for item in items], [1, 1, 1, 1])
    phase_chart(items)


if __name__ == "__main__":
    main()