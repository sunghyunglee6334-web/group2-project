"""목록의 동그란 상태 아이콘을 부드럽게(안티에일리어싱) 그린다.

Tk Canvas 의 원·선은 계단처럼 깨져 보인다 (X11 은 안티에일리어싱이 없음).
그래서 Pillow 로 4배 크게 그린 뒤 줄여서(슈퍼샘플링) 이미지로 붙인다.
같은 모양은 한 번만 만들어 재사용한다.

    icon_image(widget, "check", "#3182F6", 34)   # 파란 원 + 흰 체크
    icon_image(widget, "", "#E5E8EB", 34)        # 빈 회색 원 (대기)
"""
from __future__ import annotations

from PIL import Image, ImageColor, ImageDraw, ImageTk

SS = 4                      # 몇 배로 크게 그렸다 줄일지
_cache: dict = {}


def _rgb(color: str) -> tuple[int, int, int]:
    """'#3182F6' 이나 'white' 같은 색 이름 -> (r, g, b)"""
    return ImageColor.getrgb(color)[:3]


def _round_line(draw, pts, width, fill):
    """끝과 꺾이는 곳이 둥근 굵은 선."""
    draw.line(pts, fill=fill, width=width, joint="curve")
    r = width / 2
    for x, y in (pts[0], pts[-1]):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def _draw(kind: str, bg: str, fg: str, d: int) -> Image.Image:
    S = d * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(img)
    g.ellipse((0, 0, S - 1, S - 1), fill=_rgb(bg) + (255,))
    c = _rgb(fg) + (255,)
    u = S / 34                           # 34px 아이콘 기준 단위

    if kind == "check":                  # ✓
        _round_line(g, [(10 * u, 17.5 * u), (15 * u, 22.5 * u), (24 * u, 12 * u)], int(3.4 * u), c)
    elif kind == "check2":               # ✓ 위아래 두 개 = 검수 완료 (교차검수까지 한 번 더 확인)
        w = int(2.8 * u)
        for dy in (-3.3, 3.3):
            _round_line(g, [(11 * u, (17 + dy) * u), (15 * u, (20.5 + dy) * u), (23 * u, (13 + dy) * u)], w, c)
    elif kind == "edit":                 # 연필 (몸통 + 뾰족한 끝 + 지우개)
        body = [(21.5 * u, 9 * u), (25 * u, 12.5 * u), (14 * u, 23.5 * u), (10.5 * u, 20 * u)]
        g.polygon(body, fill=c)
        g.polygon([(10.5 * u, 20 * u), (14 * u, 23.5 * u), (8.5 * u, 25.5 * u)], fill=c)
        g.polygon([(22.5 * u, 8 * u), (24 * u, 6.5 * u), (27.5 * u, 10 * u), (26 * u, 11.5 * u)], fill=c)
    elif kind == "alert":                # !
        w = 3.6 * u
        g.rounded_rectangle((17 * u - w / 2, 8.5 * u, 17 * u + w / 2, 19.5 * u), radius=w / 2, fill=c)
        r = 2.2 * u
        g.ellipse((17 * u - r, 24 * u - r, 17 * u + r, 24 * u + r), fill=c)
    return img.resize((d, d), Image.LANCZOS)


def icon_image(widget, kind: str, bg: str, fg: str, d: int) -> ImageTk.PhotoImage:
    """kind: 'check' | 'check2' | 'edit' | 'alert' | '' (빈 원). 같은 값이면 만들어 둔 것을 돌려준다."""
    key = (str(widget.winfo_toplevel()), kind, bg, fg, d)
    photo = _cache.get(key)
    if photo is None:
        photo = ImageTk.PhotoImage(_draw(kind, bg, fg, d), master=widget)
        _cache[key] = photo
    return photo
