import csv
from collections import Counter
from html import escape
from pathlib import Path
from statistics import median, quantiles

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
CHARTS = HERE / "charts"

INK = "#162842"
MUTED = "#475b73"
GRID = "#dce5ef"
BLUE = "#245dcc"
TEAL = "#087d75"
ORANGE = "#a34a15"
INTEREST = ("Да", "Скорее да", "Скорее нет", "Нет")


def read_csv(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows or any(None in row or not all(row.values()) for row in rows):
        raise ValueError(f"Пустые значения или неверное число полей в {name}")
    return rows


def number(value):
    return f"{value:g}".replace(".", ",")


def percent(part, total):
    return f"{100 * part / total:.1f}".replace(".", ",") + "%"


class Chart:
    def __init__(self, title, subtitle, height):
        self.height = height
        self.elements = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="920" height="{height}" '
            f'viewBox="0 0 920 {height}" role="img">',
            f"<title>{escape(title)}</title><desc>{escape(subtitle)}</desc>",
            '<g font-family="DejaVu Sans, Arial, sans-serif">',
        ]
        self.rect(0, 0, 920, height, "#ffffff")
        self.rect(28, 29, 5, 25, BLUE)
        self.label(44, 49, title, size=26, bold=True)
        self.label(44, 76, subtitle, fill=MUTED)

    def label(self, x, y, content, *, size=15, fill=INK, anchor="start", bold=False):
        weight = 700 if bold else 400
        self.elements.append(
            f'<text x="{x:g}" y="{y:g}" fill="{fill}" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{escape(str(content))}</text>'
        )

    def rect(self, x, y, width, height, fill):
        self.elements.append(
            f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" fill="{fill}"/>'
        )

    def line(self, x1, y1, x2, y2, fill=GRID, width=1, dashed=False):
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        self.elements.append(
            f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
            f'stroke="{fill}" stroke-width="{width}"{dash}/>'
        )

    def dot(self, x, y, color, hollow=False, radius=6):
        fill = "#ffffff" if hollow else color
        self.elements.append(
            f'<circle cx="{x:g}" cy="{y:g}" r="{radius}" fill="{fill}" '
            f'stroke="{color}" stroke-width="2"/>'
        )

    def x_axis(self, scale, ticks, top, bottom, unit):
        ticks = list(ticks)
        for tick in ticks:
            x = scale(tick)
            self.line(x, top, x, bottom)
            self.label(x, bottom + 22, tick, anchor="middle", fill=MUTED, size=13)
        self.line(scale(ticks[0]), bottom, scale(ticks[-1]), bottom, MUTED)
        self.label(scale(ticks[-1]), bottom + 43, unit, anchor="end", fill=MUTED, size=13)

    def save(self, name, footnote):
        self.line(28, self.height - 43, 892, self.height - 43)
        self.label(30, self.height - 20, footnote, fill=MUTED, size=13)
        (CHARTS / f"{name}.svg").write_text(
            "\n".join([*self.elements, "</g>", "</svg>", ""]), encoding="utf-8"
        )


def market_value(rows, indicator, year, unit):
    row, = [r for r in rows if (r["indicator"], r["year"], r["unit"])
            == (indicator, str(year), unit)]
    return tuple(float(part) for part in row["value"].split("–"))


def adoption_chart(market):
    russian = "Доля домохозяйств РФ с технологиями «умного дома»"
    world = "Доля домохозяйств в мире с технологиями «умного дома»"
    items = [
        ("Россия, 2019 · факт", market_value(market, russian, 2019, "%"), BLUE),
        ("Россия, 2024 · оценка", market_value(market, russian, 2024, "%"), BLUE),
        ("Мир, 2024 · оценка", market_value(market, world, 2024, "%"), TEAL),
        ("Россия, 2025 · прогноз", market_value(market, russian, 2025, "%"), ORANGE),
    ]
    chart = Chart("Распространённость технологий «умного дома»",
                  "Опубликованные показатели и исторический прогноз", 363)

    def x(value):
        return 280 + value * 16

    chart.x_axis(x, range(0, 36, 5), 106, 249, "Доля домохозяйств, %")
    for i, (label, values, color) in enumerate(items):
        y = 123 + i * 34
        chart.label(44, y + 5, label)
        if len(values) == 2:
            low, high = (x(value) for value in values)
            chart.line(low, y, high, y, color, 5)
            for endpoint in (low, high):
                chart.line(endpoint, y - 6, endpoint, y + 6, color, 2)
        else:
            chart.dot(x(values[0]), y, color, hollow=color == ORANGE)
        chart.label(x(values[-1]) + 14, y + 5, "–".join(map(number, values)) + "%", bold=True)
    chart.save("01_adoption", "Источники · BFM.ru (Statista), «Коммерсантъ Guide», Statista. Диапазон перенесён из источника.")


def sales_chart(market):
    indicator = "Объём продаж устройств «умного дома» в России"
    first, = market_value(market, indicator, 2022, "млрд долл.")
    last, = market_value(market, indicator, 2025, "млрд долл.")
    chart = Chart("Продажи устройств умного дома в России",
                  "Оценка и прогноз из одной публикации НТЦ ГРЦ", 377)

    def y(value):
        return 286 - value * 49

    for tick in range(4):
        chart.line(135, y(tick), 790, y(tick))
        chart.label(121, y(tick) + 5, tick, anchor="end", fill=MUTED, size=13)
    chart.label(135, 116, "Млрд долл. США", fill=MUTED, size=13)
    chart.line(270, y(first), 650, y(last), ORANGE, 3, dashed=True)
    for x, value, label, color, forecast in (
        (270, first, "2022 · оценка", BLUE, False),
        (650, last, "2025 · прогноз", ORANGE, True),
    ):
        chart.dot(x, y(value), color, hollow=forecast)
        chart.label(x, y(value) - 14, number(value), anchor="middle", bold=True)
        chart.label(x, 310, label, anchor="middle")
    chart.save("02_sales", "Источник · НТЦ ГРЦ в публикации Rozetked. Пунктир показывает прогноз, промежуточных данных нет.")


def heatmap(rows):
    counts = Counter((r["interested_in_installation"], r["ready_to_leave_online_request"]) for r in rows)
    chart = Chart("Интерес к установке и готовность оставить заявку",
                  f"Синтетический опрос · n = {len(rows)} · число анкет и доля внутри строки", 470)
    for i, answer in enumerate(("Да", "Нет")):
        chart.label(425 + 283 * i, 140, f"Готовность к заявке · {answer.lower()}", anchor="middle", bold=True)
    chart.label(44, 140, "Интерес к установке", bold=True)
    for i, interest in enumerate(INTEREST):
        y = 158 + i * 60
        total = sum(counts[interest, answer] for answer in ("Да", "Нет"))
        chart.label(44, y + 25, interest, bold=True)
        chart.label(44, y + 44, f"n = {total}", fill=MUTED, size=13)
        for j, answer in enumerate(("Да", "Нет")):
            count = counts[interest, answer]
            ratio = count / total if total else 0
            fill = "#dce8f9"
            if ratio >= 0.65:
                fill = "#1d4d9e"
            elif ratio >= 0.35:
                fill = "#a9c6f0"
            center = 425 + j * 283
            chart.rect(center - 132, y, 264, 51, fill)
            value = f"{count} · {percent(count, total)}" if total else "—"
            chart.label(center, y + 32, value, anchor="middle",
                        fill="#ffffff" if ratio >= 0.65 else INK, bold=True)
    chart.save("03_interest_request", "Чем темнее ячейка, тем выше доля ответа в данной группе интереса.")


def ranked_bars(name, title, subtitle, rows, column, footnote):
    counts = sorted(Counter(r[column] for r in rows).items(), key=lambda item: (-item[1], item[0]))
    bottom = 115 + len(counts) * 35
    chart = Chart(title, subtitle, bottom + 108)
    maximum = max(10, ((counts[0][1] * 100 // len(rows)) // 10 + 1) * 10)

    def x(value):
        return 330 + value / maximum * 460

    chart.x_axis(x, range(0, maximum + 1, 10), 104, bottom, "Доля анкет, %")
    for i, (label, count) in enumerate(counts):
        y = 115 + i * 35
        right = x(count * 100 / len(rows))
        chart.label(44, y + 17, label)
        chart.rect(x(0), y, right - x(0), 23, BLUE if i == 0 else TEAL)
        chart.label(right + 10, y + 17, f"{count} · {percent(count, len(rows))}", bold=True)
    chart.save(name, footnote)


def housing_chart(groups):
    chart = Chart("Интерес и заявки по типу жилья",
                  "Синтетический опрос · доля от всех анкет каждого типа жилья", 431)

    def x(value):
        return 224 + value * 5.7

    chart.x_axis(x, range(0, 101, 20), 139, 324, "Доля анкет в группе, %")
    for i, (label, color) in enumerate((("Интерес к установке", BLUE), ("Готовность к заявке", TEAL))):
        chart.rect(224 + i * 250, 104, 16, 12, color)
        chart.label(248 + i * 250, 115, label)
    for i, (housing, group) in enumerate(groups):
        top = 145 + i * 60
        chart.label(44, top + 20, housing, bold=True)
        chart.label(44, top + 41, f"n = {len(group)}", fill=MUTED, size=13)
        for j, (count, color) in enumerate((
            (sum(r["interested_in_installation"] in INTEREST[:2] for r in group), BLUE),
            (sum(r["ready_to_leave_online_request"] == "Да" for r in group), TEAL),
        )):
            y = top + 23 * j
            right = x(count * 100 / len(group))
            chart.rect(x(0), y, right - x(0), 17, color)
            chart.label(right + 8, y + 14, percent(count, len(group)), size=13, bold=True)
    chart.save("06_housing", "Интерес включает ответы «Да» и «Скорее да». Группы различаются по размеру.")


def budget_chart(groups):
    chart = Chart("Бюджет на установку по типу жилья",
                  "Синтетический опрос · только заинтересованные с положительным бюджетом", 396)
    budgets = [(housing, sorted(int(r["budget_rub"]) / 1000 for r in group
                                if r["interested_in_installation"] in INTEREST[:2]
                                and int(r["budget_rub"]) > 0))
               for housing, group in groups]
    maximum = max(100, (int(max(max(values) for _, values in budgets)) // 100 + 1) * 100)

    def x(value):
        return 220 + value / maximum * 645

    chart.x_axis(x, range(0, maximum + 1, 100), 108, 300, "Бюджет, тыс. руб.")
    for i, (housing, values) in enumerate(budgets):
        low, mid, high = quantiles(values, n=4, method="inclusive") if len(values) > 1 else values * 3
        spread = 1.5 * (high - low)
        inside = [value for value in values if low - spread <= value <= high + spread]
        left, right = x(min(inside)), x(max(inside))
        y = 132 + i * 63
        chart.label(44, y + 4, housing, bold=True)
        chart.label(44, y + 23, f"n = {len(values)}", fill=MUTED, size=13)
        chart.line(left, y, right, y, MUTED, 2)
        for endpoint in (left, right):
            chart.line(endpoint, y - 7, endpoint, y + 7, MUTED, 2)
        chart.rect(x(low), y - 11, max(1, x(high) - x(low)), 22, "#a9c6f0")
        chart.line(x(mid), y - 12, x(mid), y + 12, BLUE, 3)
        chart.label(x(mid), y + 29, number(median(values)), anchor="middle", bold=True, size=13)
        for value in sorted(set(values) - set(inside)):
            chart.dot(x(value), y, MUTED, hollow=True, radius=3)
    chart.save("07_budget", "Коробка · средние 50%; черта и число · медиана; усы · до 1,5 межквартильного размаха.")


def main():
    market = read_csv("smart_home_market_russia.csv")
    survey = read_csv("potential_clients_survey_synthetic.csv")
    ids = {row["respondent_id"] for row in survey}
    if len(ids) != len(survey):
        raise ValueError("В опросе есть повторяющиеся идентификаторы")
    if any(row["interested_in_installation"] not in INTEREST or
           row["ready_to_leave_online_request"] not in ("Да", "Нет") for row in survey):
        raise ValueError("Неизвестный вариант ответа об интересе или заявке")
    group_counts = Counter(row["housing_type"] for row in survey)
    groups = [(housing, [row for row in survey if row["housing_type"] == housing])
              for housing, _ in group_counts.most_common()]
    interested = [row for row in survey if row["interested_in_installation"] in INTEREST[:2]]
    leads = [row for row in interested if row["ready_to_leave_online_request"] == "Да"]

    CHARTS.mkdir(exist_ok=True)
    adoption_chart(market)
    sales_chart(market)
    heatmap(survey)
    ranked_bars("04_functions", "Приоритетные функции умного дома",
                f"Синтетический опрос · заинтересованные в установке · n = {len(interested)}",
                interested, "priority_function", "В каждой анкете указана одна приоритетная функция.")
    ranked_bars("05_contact", "Предпочтительный способ связи",
                f"Синтетический опрос · заинтересованные и готовые к онлайн-заявке · n = {len(leads)}",
                leads, "preferred_contact", "Доля рассчитана среди анкет, где одновременно указаны интерес и готовность к заявке.")
    housing_chart(groups)
    budget_chart(groups)
    print(f"Построено 7 графиков. Рыночные показатели: {len(market)}; анкеты: {len(survey)}.")


if __name__ == "__main__":
    main()
