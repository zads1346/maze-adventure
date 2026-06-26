from __future__ import annotations


CHINESE_FONT_CANDIDATES = (
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    "Microsoft YaHei",
    "SimHei",
    "PingFang SC",
    "Arial Unicode MS",
    "DejaVu Sans",
)


def get_font(pygame, size: int, bold: bool = False):
    for name in CHINESE_FONT_CANDIDATES:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)
