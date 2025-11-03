"""명령행 인터페이스를 갖춘 간단한 풍하중 계산기."""
from __future__ import annotations

import argparse
import math
from typing import Dict, Iterable, Tuple


SHAPE_PRESSURE_COEFFICIENTS: Dict[str, Dict[str, float]] = {
    "rectangular": {"Cp": 0.8, "설명": "직육면체 구조물"},
    "circular": {"Cp": 0.7, "설명": "원형/원통형 구조물"},
    "triangular": {"Cp": 0.6, "설명": "삼각 단면 구조물"},
}

IMPORTANCE_FACTORS: Dict[str, Dict[str, float]] = {
    "보통": {"Iw": 1.0, "설명": "일반 건축물"},
    "중요": {"Iw": 1.1, "설명": "중요 시설"},
    "매우중요": {"Iw": 1.2, "설명": "재난대비 및 특수 시설"},
}

EXPOSURE_FACTORS: Dict[str, Dict[str, Iterable[Tuple[float, float]]]] = {
    "도심": {
        "description": "고밀도 도심지 및 숲이 우거진 지역",
        "table": (
            (15.0, 0.70),
            (30.0, 0.85),
            (60.0, 1.00),
            (120.0, 1.10),
        ),
    },
    "교외": {
        "description": "저층 건물이 산재한 교외 및 평지",
        "table": (
            (15.0, 0.80),
            (30.0, 1.15),
            (60.0, 1.25),
            (120.0, 1.35),
        ),
    },
    "해안": {
        "description": "해안 및 노출된 평야",
        "table": (
            (15.0, 0.90),
            (30.0, 1.10),
            (60.0, 1.25),
            (120.0, 1.40),
        ),
    },
}

DEFAULT_GUST_EFFECT = 0.85


def lookup_exposure_factor(exposure: str, height: float) -> float:
    """주어진 높이에 대한 풍속압계수 Kz를 조회한다."""
    table = EXPOSURE_FACTORS[exposure]["table"]
    for limit, value in table:
        if height <= limit:
            return value
    return table[-1][1]


def compute_effective_area(shape: str, height: float, width: float, length: float) -> float:
    """풍하중이 작용하는 유효 면적 A를 계산한다."""
    if shape == "rectangular":
        return height * width
    if shape == "circular":
        radius = width / 2.0
        return height * math.pi * radius
    if shape == "triangular":
        return 0.5 * height * width
    raise ValueError(f"Unknown shape '{shape}'")


def calculate_design_wind_load(
    shape: str,
    height: float,
    width: float,
    length: float,
    basic_wind_speed: float,
    exposure: str,
    importance: str,
    gust_factor: float,
) -> Dict[str, float]:
    q = 0.613 * basic_wind_speed ** 2
    cp = SHAPE_PRESSURE_COEFFICIENTS[shape]["Cp"]
    iw = IMPORTANCE_FACTORS[importance]["Iw"]
    kz = lookup_exposure_factor(exposure, height)
    area = compute_effective_area(shape, height, width, length)
    design_pressure = q * cp * iw * kz * gust_factor
    design_force = design_pressure * area
    return {
        "q": q,
        "Cp": cp,
        "Iw": iw,
        "Kz": kz,
        "G": gust_factor,
        "Area": area,
        "Pressure": design_pressure,
        "Force": design_force,
    }


def format_table(result: Dict[str, float]) -> str:
    headers = ("항목", "값", "단위/설명")
    rows = [
        ("기본풍압 q", f"{result['q']:.3f}", "kN/m² (0.613·V²)"),
        ("형상계수 Cp", f"{result['Cp']:.2f}", "형상별 압력계수"),
        ("중요도계수 Iw", f"{result['Iw']:.2f}", "사용자 선택"),
        ("풍속압계수 Kz", f"{result['Kz']:.2f}", "노출조건·높이"),
        ("거스트계수 G", f"{result['G']:.2f}", "KDS 41 17 00 참조"),
        ("유효면적 A", f"{result['Area']:.3f}", "m²"),
        ("설계풍압 p", f"{result['Pressure']:.3f}", "kN/m²"),
        ("설계풍하중 F", f"{result['Force']:.3f}", "kN"),
    ]

    col_widths = [max(len(row[i]) for row in [headers, *rows]) for i in range(3)]
    lines = [
        " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers)),
        "-+-".join("-" * col_widths[i] for i in range(3)),
    ]
    for row in rows:
        lines.append(" | ".join(str(row[i]).ljust(col_widths[i]) for i in range(3)))
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KDS 기반 단순화 설계 풍하중 계산")
    parser.add_argument("--shape", choices=SHAPE_PRESSURE_COEFFICIENTS.keys(), required=True, help="구조물 형상")
    parser.add_argument("--height", type=float, required=True, help="구조물 높이 (m)")
    parser.add_argument("--width", type=float, required=True, help="풍방향 유효 폭 또는 직경 (m)")
    parser.add_argument("--length", type=float, default=0.0, help="구조물 길이 (m), 필요 시")
    parser.add_argument("--basic-wind-speed", type=float, required=True, help="설계 기본풍속 V (m/s)")
    parser.add_argument(
        "--exposure",
        choices=EXPOSURE_FACTORS.keys(),
        default="교외",
        help="KDS 노출 범주",
    )
    parser.add_argument(
        "--importance",
        choices=IMPORTANCE_FACTORS.keys(),
        default="보통",
        help="중요도계수 구분",
    )
    parser.add_argument(
        "--gust-factor",
        type=float,
        default=DEFAULT_GUST_EFFECT,
        help="거스트 계수 (기본 0.85)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = calculate_design_wind_load(
        shape=args.shape,
        height=args.height,
        width=args.width,
        length=args.length,
        basic_wind_speed=args.basic_wind_speed,
        exposure=args.exposure,
        importance=args.importance,
        gust_factor=args.gust_factor,
    )
    print("\n설계 풍하중 계산 결과")
    print("=" * 28)
    print(format_table(result))


if __name__ == "__main__":
    main()
