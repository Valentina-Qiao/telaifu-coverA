"""Render the fixed Telaifu A cover with the supplied headline and photographs."""

import argparse
import json
import math
from secrets import choice
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

ASSETS = Path(__file__).resolve().parents[1] / "assets"
CANVAS = (1080, 1920)
BRAND = "特徕福"
RESAMPLE = Image.Resampling.LANCZOS
TITLE_FONT = ASSETS / "KNMaiyuan-Regular.ttf"
FALLBACK_FONT = ASSETS / "MaokenAssortedSans.ttf"
STICKER_CORNERS = ((542, 1011), (956, 956), (973, 1079), (554, 1118))
STICKER_SIZE = (430, 135)
REFERENCE_TITLES = {
    ("特徕福招牌灯布", "翻新焕颜"): "reference-title-1.png",
    ("特徕福广告物料", "速出"): "reference-title-2.png",
}
GENERATED_TITLES = {
    ("特徕福门店招牌", "灯布换新"): "generated-title-storefront.png",
}
# Clockwise corners of the two photo openings in the fixed collage layer.
SLOTS = (
    (((179, 441), (725, 485), (695, 1186), (154, 1145)), (560, 724)),
    (((405, 1098), (979, 1155), (879, 1657), (321, 1567)), (583, 506)),
)


def cutout(image):
    return image.crop(image.getbbox())


def title_lines(title):
    """Respect supplied line breaks, or wrap Chinese by weighted display width."""
    explicit = title.splitlines()
    if len(explicit) > 1:
        return [line.strip() for line in explicit if line.strip()]
    lines = []
    text = title.strip()
    while text:
        limit = 7 if not lines and text.startswith(BRAND) else 8
        width = 0
        end = len(text)
        last_break = 0
        for index, char in enumerate(text):
            width += 1 if unicodedata.east_asian_width(char) in "FWA" else 0.55
            if width > limit:
                end = last_break or index
                break
            if char.isspace() or unicodedata.category(char).startswith("P"):
                last_break = index + 1
        while end < len(text) and text[end] in "，。！？、：；）》】":
            end += 1
        lines.append(text[:end].strip())
        text = text[end:].lstrip()
    return lines


def supports_glyph(font, char):
    glyph = font.getmask(char)
    missing = font.getmask("\U0010FFFF")
    return glyph.size != missing.size or bytes(glyph) != bytes(missing)


def row_mask(text):
    primary = ImageFont.truetype(str(TITLE_FONT), 140)
    fallback = ImageFont.truetype(str(FALLBACK_FONT), 140)
    fonts = []
    for char in text:
        font = primary if char.isspace() or supports_glyph(primary, char) else fallback
        if font is fallback and not supports_glyph(font, char):
            raise ValueError(f"The cover fonts do not contain {char!r}.")
        fonts.append(font)
    full_width = math.ceil(sum(font.getlength(char) for font, char in zip(fonts, text))) + 22
    mask = Image.new("L", (full_width, 184))
    x = 10.0
    for index, (font, char) in enumerate(zip(fonts, text)):
        advance = font.getlength(char)
        if not char.isspace():
            glyph = Image.new("L", (math.ceil(advance) + 36, 174))
            ink = np.asarray(font.getmask(char))
            weight = 3 if font is primary and np.count_nonzero(ink) < ink.size * .56 else 1
            ImageDraw.Draw(glyph).text((18, 147), char, font=font, anchor="ls",
                                       fill=255, stroke_width=weight)
            glyph = glyph.rotate((2.4, -2.6, 3.6, 0.5)[index % 4],
                                 resample=Image.Resampling.BICUBIC)
            mask.paste(glyph, (round(x) - 13, 3 - index % 3 * 2), glyph)
        x += advance
    # Smooth the small corner transitions where the rounded face meets the bevel.
    mask = mask.filter(ImageFilter.GaussianBlur(2.3)).point(
        lambda a: max(0, min(255, (a - 85) * 3))
    )
    return cutout(mask)


def offset(mask, dx, dy):
    shifted = Image.new("L", mask.size)
    shifted.paste(mask, (dx, dy))
    return shifted


def tone_image(size, top, bottom):
    strip = Image.new("RGB", (1, size[1]))
    strip.putdata([
        tuple(round(a + (b-a) * (y / max(1, size[1]-1))**1.3) for a, b in zip(top, bottom))
        for y in range(size[1])
    ])
    return strip.resize(size)


def gold_word(text, max_width, max_height):
    word = row_mask(text)
    face = Image.new("L", (word.width + 36, word.height + 49))
    face.paste(word, (17, 12))
    rim = face.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(.9))
    edge = rim.filter(ImageFilter.MaxFilter(3))
    title = Image.new("RGBA", face.size)
    title.paste((31, 13, 10, 196), mask=offset(edge, 2, 21).filter(ImageFilter.GaussianBlur(4)))
    for depth in range(19, -1, -1):
        dx = depth // 6
        if depth in (19, 13, 8):
            title.paste("#703015", mask=offset(edge, dx, depth))
        color = {
            19: "#92421c", 16: "#e8a051", 13: "#ffcf87",
            11: "#ad5323", 8: "#843812", 5: "#d17c39", 2: "#a96837",
            0: "#cf9c58",
        }
        if depth in color:
            title.paste(color[depth], mask=offset(rim, dx, depth))
    title.paste("#fff6d0", mask=ImageChops.subtract(rim, offset(rim, 1, 3)))
    title.paste("#f6d182", mask=face.filter(ImageFilter.MaxFilter(3)))
    title.paste(tone_image(face.size, (255, 255, 245), (255, 238, 148)), mask=face)
    title.paste("#fffef4", mask=ImageChops.subtract(face, offset(face, 1, 4)))
    title = cutout(title.rotate(4.7, resample=Image.Resampling.BICUBIC, expand=True))
    return ImageOps.contain(title, (max_width, max_height), RESAMPLE)


def lettering(title):
    lines = title_lines(title)
    has_brand = lines[0].startswith(BRAND)
    body = Image.new("RGBA", (854, 277))
    if has_brand:
        brand = Image.open(ASSETS / "brand.png").convert("RGBA")
        body.alpha_composite(brand, (1, 2))
        lead = lines[0][len(BRAND):].strip()
        following = lines[1:]
        if lead:
            word = gold_word(lead, 382, 142)
            body.alpha_composite(word, (447, 7 + (142 - word.height) // 3))
        if following:
            region = 129
            height = region // len(following)
            for i, line in enumerate(following):
                word = gold_word(line, 490, height)
                word = word.resize((min(490, round(word.width * 1.1)), word.height), RESAMPLE)
                body.alpha_composite(word, (792 - word.width, 141 + i * height))
    else:
        height = min(180, 271 // len(lines))
        for i, line in enumerate(lines):
            word = gold_word(line, 820, height)
            x = (body.width - word.width) // 2 if i == 0 else 817 - word.width
            body.alpha_composite(word, (x, i * height))
    return cutout(body)

def open_photo(path):
    with Image.open(path) as original:
        if getattr(original, "n_frames", 1) != 1:
            raise ValueError(f"Provide a still photo: {path}")
        return ImageOps.exif_transpose(original).convert("RGBA")


def perspective(output_corners, input_corners):
    equations = []
    samples = []
    for (x, y), (u, v) in zip(output_corners, input_corners):
        equations.extend([
            [x, y, 1, 0, 0, 0, -u*x, -u*y],
            [0, 0, 0, x, y, 1, -v*x, -v*y],
        ])
        samples.extend([u, v])
    return np.linalg.solve(equations, samples)


def sticker_text(request):
    explicit = request.get("sticker")
    candidates = request.get("sticker_candidates", [])
    if explicit is not None and candidates:
        raise ValueError("Use sticker or sticker_candidates.")
    if explicit is not None:
        candidates = [explicit]
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Provide a title-related four-character sticker or sticker_candidates.")
    for phrase in candidates:
        if (not isinstance(phrase, str) or len(phrase) != 4
                or any(not unicodedata.name(char, "").startswith("CJK UNIFIED IDEOGRAPH")
                       for char in phrase)):
            raise ValueError("Each sticker phrase must contain exactly four Chinese characters.")
    return choice(candidates)


def place_sticker(group, text):
    font = ImageFont.truetype(str(FALLBACK_FONT), 123)
    for char in text:
        if not supports_glyph(font, char):
            raise ValueError(f"The sticker font does not contain {char!r}.")
    word = Image.new("L", (math.ceil(font.getlength(text)) + 55, 163))
    ImageDraw.Draw(word).text((17, 125), text, font=font, anchor="ls", fill=255, stroke_width=1)
    # Right-leaning headline with the same in-frame proportions as the sample.
    word = word.transform(word.size, Image.Transform.AFFINE, (1, .17, -23, 0, 1, 0),
                          resample=Image.Resampling.BICUBIC)
    word = cutout(word).resize((350, 101), RESAMPLE)
    face = Image.new("L", STICKER_SIZE)
    face.paste(word, (48, 12))
    outline = face.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(.45))
    sticker = Image.new("RGBA", STICKER_SIZE)
    sticker.paste((23, 37, 48, 130), mask=offset(outline, 1, 4).filter(ImageFilter.GaussianBlur(1.6)))
    sticker.paste("#14222f", mask=outline)
    sticker.paste(tone_image(STICKER_SIZE, (255, 255, 255), (170, 213, 244)), mask=face)
    sticker.paste("#ffffff", mask=ImageChops.subtract(face, offset(face, 0, 2)))

    left = min(x for x, _ in STICKER_CORNERS)
    top = min(y for _, y in STICKER_CORNERS)
    right = max(x for x, _ in STICKER_CORNERS)
    bottom = max(y for _, y in STICKER_CORNERS)
    w, h = STICKER_SIZE
    local = [(x-left, y-top) for x, y in STICKER_CORNERS]
    transform = perspective(local, [(0, 0), (w, 0), (w, h), (0, h)])
    sticker = sticker.transform((right-left, bottom-top), Image.Transform.PERSPECTIVE, transform,
                                resample=Image.Resampling.BICUBIC)
    group.alpha_composite(sticker, (left, top))


def place_photo(layer, photo, slot, focus, mode):
    corners, size = slot
    picture = Image.new("RGBA", size, "#102d46")
    if mode == "auto":
        aspect_ratio = (photo.width / photo.height) / (size[0] / size[1])
        mode = "contain" if not 0.7 <= aspect_ratio <= 1.4 else "cover"
    if mode == "contain":
        backfill = ImageOps.fit(photo, size, RESAMPLE, centering=focus)
        picture.alpha_composite(backfill.filter(ImageFilter.GaussianBlur(28)))
        picture.alpha_composite(Image.new("RGBA", size, (10, 28, 46, 95)))
        foreground = ImageOps.contain(photo, size, RESAMPLE)
        picture.alpha_composite(foreground, ((size[0] - foreground.width) // 2,
                                             (size[1] - foreground.height) // 2))
    else:
        picture.alpha_composite(ImageOps.fit(photo, size, RESAMPLE, centering=focus))

    # Map all four corners to the original photo opening. Pad edge colors
    # to cover the paper's antialiased borders without zooming the photograph.
    pad = 12
    left = min(x for x, _ in corners) - pad
    top = min(y for _, y in corners) - pad
    right = max(x for x, _ in corners) + pad
    bottom = max(y for _, y in corners) + pad
    local = [(x-left, y-top) for x, y in corners]
    w, h = size
    target = [(pad,pad), (w+pad,pad), (w+pad,h+pad), (pad,h+pad)]
    transform = perspective(local, target)
    padded = Image.fromarray(np.pad(np.asarray(picture), ((pad,pad),(pad,pad),(0,0)), mode="edge"))
    warped = padded.transform((right - left, bottom - top), Image.Transform.PERSPECTIVE,
                               transform, resample=Image.Resampling.BICUBIC,
                               fillcolor="#102d46")
    visible = Image.new("L", warped.size)
    tl, tr, br, bl = corners
    bleed = [(tl[0]-4,tl[1]-5), (tr[0]+5,tr[1]-5), (br[0]+5,br[1]+5), (bl[0]-5,bl[1]+5)]
    ImageDraw.Draw(visible).polygon([(x-left,y-top) for x,y in bleed], fill=255)
    warped.putalpha(visible)
    layer.alpha_composite(warped, (left, top))


def fixed_collage(paths, focus, modes):
    collage = Image.open(ASSETS / "collage.png").convert("RGBA")
    shadow_mask = Image.open(ASSETS / "collage-shadow.png").convert("L")
    shadow = Image.new("RGBA", CANVAS, "#031024")
    shadow.putalpha(shadow_mask.point(lambda a: a * 0.5))
    layer = Image.new("RGBA", CANVAS)
    layer.alpha_composite(shadow, (1, 10))
    photos = [open_photo(path) for path in paths]
    for i, slot in enumerate(SLOTS):
        photo = photos[min(i, len(photos) - 1)]
        if i == 1 and len(photos) == 1:
            if min(photo.size) >= 450:
                # The second frame shows a closer view of the same real photo.
                px, py = focus[i]
                w, h = round(photo.width * .82), round(photo.height * .82)
                left, top = round((photo.width - w) * px), round((photo.height - h) * py)
                photo = photo.crop((left, top, left + w, top + h))
        place_photo(layer, photo, slot, focus[i], modes[i])
    layer.alpha_composite(collage)
    return layer


def open_headline(path, max_size=(866, 272)):
    with Image.open(path) as artwork:
        if artwork.format != "PNG" or artwork.mode != "RGBA":
            raise ValueError("Headline artwork must be an RGBA PNG.")
        alpha = artwork.getchannel("A")
        if alpha.getextrema()[0] != 0:
            raise ValueError("Headline artwork must have a transparent background.")
        bounds = alpha.point(lambda a: 255 if a >= 32 else 0).getbbox()
        if bounds is None:
            raise ValueError("Headline artwork has no visible lettering.")
        heading = artwork.crop(bounds)
    return ImageOps.contain(heading, tuple(max_size), RESAMPLE)


def render(request, out):
    title = request["title"].strip()
    photos = [Path(path) for path in request["photos"]]
    if not title or not 1 <= len(photos) <= 2 or any(not path.is_file() for path in photos):
        raise ValueError("Provide a nonempty title and one or two existing photo paths.")
    focus = request.get("focus", [[.5, .42], [.5, .48]])
    modes = request.get("fit")
    if modes is None:
        modes = ["auto", "cover"] if len(photos) == 1 else ["cover", "cover"]
    elif len(modes) != 2 or any(m not in {"cover", "contain"} for m in modes):
        raise ValueError("fit must contain two values, each cover or contain.")
    if len(focus) != 2 or any(len(p) != 2 or any(not 0 <= v <= 1 for v in p) for p in focus):
        raise ValueError("focus must contain two pairs of coordinates from 0 to 1.")
    sticker = sticker_text(request)
    # Headline sizing: defaults preserved; allow a larger headline to fill the
    # top frame. headline_bottom is the y of the headline's bottom edge.
    headline_max = request.get("headline_max_size", [866, 272])
    if (not isinstance(headline_max, list) or len(headline_max) != 2
            or any(not isinstance(v, int) or v <= 0 for v in headline_max)):
        raise ValueError("headline_max_size must be two positive integers [width, height].")
    headline_bottom = request.get("headline_bottom", 419)
    if not isinstance(headline_bottom, int) or not 0 <= headline_bottom <= CANVAS[1]:
        raise ValueError("headline_bottom must be an integer within the canvas height.")

    group = fixed_collage(photos, focus, modes)
    place_sticker(group, sticker)
    lines = tuple(title_lines(title))
    exact_artwork = REFERENCE_TITLES.get(lines)
    cached_artwork = GENERATED_TITLES.get(lines)
    custom_artwork = request.get("headline_image")
    if custom_artwork is None and exact_artwork:
        with Image.open(ASSETS / exact_artwork) as headline:
            group.alpha_composite(headline, (98, 145))
    else:
        with Image.open(ASSETS / "gold-brush.png") as brush:
            group.alpha_composite(brush, (548, 342))
        if custom_artwork is not None:
            headline = open_headline(Path(custom_artwork), headline_max)
        elif cached_artwork:
            headline = open_headline(ASSETS / cached_artwork, headline_max)
        else:
            headline = lettering(title)
        group.alpha_composite(headline, ((CANVAS[0] - headline.width) // 2,
                                         headline_bottom - headline.height))
    # Measure all nonempty foreground layers together, excluding only the faint
    # outside edge of the shadow. Then fit and position the combined artwork.
    meaningful = group.getchannel("A").point(lambda a: 255 if a >= 24 else 0).getbbox()
    group = group.crop(meaningful)
    scale = min(1, 980 / group.width, 1600 / group.height)
    if scale < 1:
        group = group.resize(tuple(round(n * scale) for n in group.size), RESAMPLE)
    position = tuple((outer - inner) // 2 for outer, inner in zip(CANVAS, group.size))
    result = Image.open(ASSETS / "starfield.jpg").convert("RGBA")
    result.alpha_composite(group, position)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.convert("RGB").save(out, format="PNG")
    print(json.dumps({
        "size": CANVAS,
        "content_box": [*position, position[0] + group.width, position[1] + group.height],
        "top_px": position[1],
        "bottom_px": CANVAS[1] - position[1] - group.height,
        "scale": round(scale, 4),
        "sticker": sticker,
    }))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path, help="UTF-8 JSON input")
    parser.add_argument("--output", required=True, type=Path, help="Output PNG path")
    args = parser.parse_args()
    try:
        render(json.loads(args.request.read_text(encoding="utf-8-sig")), args.output)
    except (OSError, ValueError, KeyError, TypeError) as err:
        parser.exit(2, f"{err}\n")


if __name__ == "__main__":
    main()
