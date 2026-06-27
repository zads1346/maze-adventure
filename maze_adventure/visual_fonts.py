from __future__ import annotations

import os

# Direct font file paths for WSL - check .ttc first (msyh), fallback to .ttf (simhei)
_FONT_PATHS = (
    "/mnt/c/Windows/Fonts/msyh.ttc",
    "/mnt/c/Windows/Fonts/simhei.ttf",
    "/mnt/c/Windows/Fonts/simsun.ttc",
    "/mnt/c/Windows/Fonts/simkai.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
)

CHINESE_FONT_NAMES = (
    "microsoftyahei",
    "simhei",
    "simsun",
    "notosanscjk",
    "wqy-microhei",
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
    "PingFang SC",
    "Arial Unicode MS",
)


def get_font(pygame, size: int, bold: bool = False):
    """Return a pygame Font that supports Chinese characters."""

    # 1) Try freetype module first (better CJK support)
    try:
        import pygame.freetype
        if not pygame.freetype.was_init():
            pygame.freetype.init()

        for path in _FONT_PATHS:
            if os.path.isfile(path):
                try:
                    font = pygame.freetype.Font(path, size=size)
                    font.antialiased = True
                    # Test CJK rendering
                    test_rect = font.get_rect("\u4e2d")
                    if test_rect.width > 4:
                        # Wrap as a pygame.font.Font-compatible object
                        return _FreetypeAdapter(font, size)
                except Exception:
                    continue

        # Try freetype SysFont
        for name in ("microsoftyahei", "simhei", "notosanscjk"):
            try:
                font = pygame.freetype.SysFont(name, size=size)
                test_rect = font.get_rect("\u4e2d")
                if test_rect.width > 4:
                    return _FreetypeAdapter(font, size)
            except Exception:
                continue
    except Exception:
        pass

    # 2) Try direct file paths with pygame.font.Font
    for path in _FONT_PATHS:
        if os.path.isfile(path):
            try:
                font = pygame.font.Font(path, size)
                test = font.render("\u4e2d", True, (255, 255, 255))
                if test.get_width() > 4:
                    return font
            except Exception:
                continue

    # 3) SysFont with Chinese verification
    for name in CHINESE_FONT_NAMES:
        try:
            font = pygame.font.SysFont(name, size, bold=bold)
            test = font.render("\u4e2d", True, (255, 255, 255))
            if test.get_width() > 4:
                return font
        except Exception:
            continue

    # 4) Fallback
    return pygame.font.SysFont(None, size, bold=bold)


class _FreetypeAdapter:
    """Adapt pygame.freetype.Font to look like pygame.font.Font."""

    def __init__(self, ft_font, size: int):
        self._ft = ft_font
        self._size = size

    def render(self, text: str, antialias: bool, color, background=None):
        fg = color
        bg = background
        surf, rect = self._ft.render(text, fg, bg, size=self._size)
        return surf

    def size(self, text: str):
        rect = self._ft.get_rect(text, size=self._size)
        return (rect.width, rect.height)
