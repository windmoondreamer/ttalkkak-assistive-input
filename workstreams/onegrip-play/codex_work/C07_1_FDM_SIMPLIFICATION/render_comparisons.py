"""Eight same-camera C07 / C07.1 comparison renders."""
from __future__ import annotations

import json
import shutil
import struct
import sys
from pathlib import Path

import numpy as np
from build123d import import_step
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REV_I = ROOT / "thumb_inner_housing_lab" / "REV_I_SOURCE_FAITHFUL_THUMB_PROTOTYPE"
REV_J = ROOT / "thumb_inner_housing_lab" / "REV_J_DOCS101_REVALIDATION"
sys.path.insert(0, str(REV_I / "10_scripts"))
import labutil as L  # noqa: E402
import labrender as R  # noqa: E402
from i02_original_external_stack import frame  # noqa: E402

C07_PATH = REV_I / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.step"
C07_STL = REV_I / "07_prototype" / "C07_SOURCE_FAITHFUL_THUMB_CORE_REFINED.stl"
C071_PATH = HERE / "outputs" / "C07_1_SOURCE_FAITHFUL_THUMB_CORE_SIMPLIFIED.step"
OUT = HERE / "renders"
TMP = OUT / "_panels"

GREEN = (92, 179, 126)
BLUE = (82, 145, 222)
REMOVED = (226, 76, 70)
ADDED = (243, 166, 58)
SHELL_A = (150, 178, 132)
SHELL_B = (126, 158, 176)
SWITCH = (222, 103, 86)


def font(size: int):
    for name in ("consola.ttf", "arial.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def fit_box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return np.asarray([[x, y, z] for x in (lo[0], hi[0])
                       for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])


def binary_stl_triangles(path: Path):
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    dt = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (9,)), ("attr", "<u2")])
    return np.frombuffer(raw, dtype=dt, offset=84, count=count)["vertices"].astype(float).reshape(-1, 3, 3)


def paired(index, slug, camera, up, fit, title, subtitle,
           extra_left=None, extra_right=None, lines=None, left_core_alpha=1.0):
    left = [(TC07, GREEN, left_core_alpha, "C07 authority")]
    right = [(TC071, BLUE, 1.0, "C07.1 candidate")]
    left += extra_left or []
    right += extra_right or []
    common = dict(camera_dir=tuple(camera), up_hint=tuple(up),
                  subtitle=subtitle,
                  footer="Isolated C07.1 FDM simplification | exact same camera and fit",
                  size=(750, 650), ss=2, fit=fit, world_lines=lines)
    lp = TMP / f"{index:02d}_L.png"
    rp = TMP / f"{index:02d}_R.png"
    R.render(lp, left, title=f"C07 | {title}", **common)
    R.render(rp, right, title=f"C07.1 | {title}", **common)
    a, b = Image.open(lp).convert("RGB"), Image.open(rp).convert("RGB")
    canvas = Image.new("RGB", (1500, 700), (232, 235, 239))
    canvas.paste(a, (0, 50)); canvas.paste(b, (750, 50))
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 0, 1500, 50), fill=(17, 21, 27))
    d.text((20, 10), f"{index}. {title} — SAME CAMERA C07 vs C07.1",
           font=font(24), fill=(255, 255, 255))
    canvas.save(OUT / f"{index:02d}_{slug}.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*.png"):
        p.unlink()
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir()

    global TC07, TC071
    c07, _ = L.as_single_solid(import_step(str(C07_PATH)), "C07")
    c071, _ = L.as_single_solid(import_step(str(C071_PATH)), "C07.1")
    TC07 = L.triangles(c07, 0.035, 0.08)
    TC071 = L.triangles(c071, 0.035, 0.08)
    removed = c07.cut(c071)
    added = c071.cut(c07)
    Trem = L.triangles(removed, 0.03, 0.07)
    Tadd = L.triangles(added, 0.03, 0.07)

    joyj = json.loads((REV_I / "06_current_core" / "i06b_joystick_current_stack.json").read_text(encoding="utf-8"))
    corej = json.loads((REV_I / "06_current_core" / "i06_current_core.json").read_text(encoding="utf-8"))
    jw = L.unit(np.asarray(joyj["joyAxisWorld"], float))
    jc = np.asarray(joyj["knobCentreWorld"], float)
    jex, jey = frame(jw)
    iso = L.unit(L.DATUM_U * .50 + L.DATUM_V * -.36 + jw * -.79)
    full_fit = fit_box(np.minimum(TC07.min((0, 1)), TC071.min((0, 1))) - 3,
                       np.maximum(TC07.max((0, 1)), TC071.max((0, 1))) + 3)
    centres = np.asarray([x["capUndersideWorld"] for x in corej["seats"].values()], float)
    carrier_fit = fit_box(centres.min(0) - np.array([12, 12, 13]),
                          centres.max(0) + np.array([12, 12, 13]))
    joy_fit = np.asarray([jc + jex*a + jey*b + jw*c for a in (-28, 28)
                          for b in (-28, 28) for c in (-31, 10)])

    paired(1, "full_core", iso, jw, full_fit, "FULL CORE",
           "overall topology and envelope", [(Trem, REMOVED, .92, "removed")],
           [(Tadd, ADDED, .92, "added")])
    paired(2, "button_carrier", -jw, -L.DATUM_V, carrier_fit, "CARRIER",
           "10 explicit bridges replace the 16-edge generated graph",
           [(Trem, REMOVED, .92, "removed")], [(Tadd, ADDED, .92, "added")])
    paired(3, "joystick_region", -jey, jw, joy_fit, "JOYSTICK REGION",
           "frozen 3.0 mm deck, 12.0 mm aperture and JOY axis",
           [(Trem, REMOVED, .92, "removed")], [(Tadd, ADDED, .92, "added")])
    paired(4, "underside", L.unit(L.DATUM_U*.25 + L.DATUM_V*.15 + jw*.96), -jw,
           full_fit, "UNDERSIDE", "standoffs removed; final export remains one solid",
           [(Trem, REMOVED, .92, "removed")], [(Tadd, ADDED, .92, "added")])
    bed0 = np.min(TC071.reshape(-1, 3) @ jw)
    bed_c = jc + jw * (bed0 - float(jc @ jw))
    bed_lines = [(bed_c-jex*33, bed_c+jex*33, (40, 40, 40, 255), 3, "bed")]
    paired(5, "joy_axis_up_print", -jey, jw, full_fit, "JOY_AXIS_UP PRINT VIEW",
           "bed contact 969.505 mm2; one first-layer component", lines=bed_lines)
    # Exact independently audited C07 STL region (triangle IDs 651-660 set).
    risk_ids = np.asarray([651, 660, 652, 654, 653, 655, 656, 658, 657, 659], int)
    Trisk = binary_stl_triangles(C07_STL)[risk_ids]
    risk_pts = Trisk.reshape(-1, 3)
    risk_fit = fit_box(risk_pts.min(0)-4, risk_pts.max(0)+4)
    paired(6, "removed_blocker_region", jw, jey, risk_fit, "BLOCKER REGION",
           "C07 trapped region 14.607 mm2 -> C07.1 non-removable regions 0",
           [(Trisk - jw*.20, REMOVED, 1.0, "exact audited 14.607 mm2 region")], [],
           left_core_alpha=.22)
    paired(7, "joystick_deck_underside", jey, -jw, joy_fit,
           "DECK UNDERSIDE",
           "predicted support landing on deck top 19.44 mm2 -> 0.00 mm2",
           [(Trem, REMOVED, .92, "removed")], [(Tadd, ADDED, .92, "added")])

    # docs/101 closest N1 interface: both frozen shell halves.
    d101 = ROOT / "build123d_workbench" / "out" / "direct_embedded_finger_switch_final_candidate"
    jad, _ = L.as_single_solid(import_step(str(d101 / "ONEGRIP_DIRECT_EMBEDDED_JaD.step")), "JaD")
    jfd, _ = L.as_single_solid(import_step(str(d101 / "ONEGRIP_DIRECT_EMBEDDED_JfD.step")), "JfD")
    TA, TB = L.triangles(jad, .07, .14), L.triangles(jfd, .07, .14)
    dat = json.loads((ROOT / "build123d_workbench" / "out" / "lower15_true_bare_finger_base" /
                      "finger_button_frozen_datums.json").read_text(encoding="utf-8"))
    n1c = np.asarray(dat["controls"]["N1"]["centerMm"], float)
    n1a = L.unit(np.asarray(dat["controls"]["N1"]["pressAxis"], float))
    ex1, ey1 = frame(n1a)
    fitn = np.asarray([n1c + ex1*a + ey1*b + n1a*c for a in (-18, 18)
                      for b in (-18, 18) for c in (-20, 12)])
    extras = [(R.clip_half(TA, n1c, ey1), SHELL_A, .30, "docs/101 JaD"),
              (R.clip_half(TB, n1c, ey1), SHELL_B, .30, "docs/101 JfD")]
    # Clip the cores for the same section view.
    old0, new0 = TC07, TC071
    TC07, TC071 = R.clip_half(TC07, n1c, ey1), R.clip_half(TC071, n1c, ey1)
    paired(8, "docs101_n1_interface", -ey1, n1a, fitn, "docs/101 CLOSEST N1 INTERFACE",
           "clearance C07 0.5217 mm -> C07.1 0.5225 mm; interference 0",
           extras, extras)
    TC07, TC071 = old0, new0

    shutil.rmtree(TMP)
    print(f"wrote {len(list(OUT.glob('*.png')))} comparison renders")


if __name__ == "__main__":
    main()
