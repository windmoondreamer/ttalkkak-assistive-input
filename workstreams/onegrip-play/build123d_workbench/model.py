"""Parametric build123d reconstruction of the simplified finger carriers."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable

from build123d import Box, Compound, Plane, Shape

from .source_of_truth import (
    BACKPLANE,
    BEAM_THICKNESS,
    BEAM_WIDTH,
    DOGLEG,
    I4_LINK_X_HINT,
    INDEX,
    INDEX_REAR,
    MIDDLE,
    MIDDLE_REAR,
    POST_SIZE,
    SHARED_LINKS,
    ButtonDatum,
    Vec3,
)


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def subtract(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(v: Vec3, factor: float) -> Vec3:
    return (v[0] * factor, v[1] * factor, v[2] * factor)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(v: Vec3) -> float:
    return sqrt(dot(v, v))


def normalize(v: Vec3) -> Vec3:
    magnitude = norm(v)
    if magnitude <= 1e-12:
        raise ValueError("Cannot normalize a zero-length vector")
    return scale(v, 1.0 / magnitude)


def back_node(button: ButtonDatum) -> Vec3:
    """Return the audited carrier contact point behind a button."""
    return subtract(button.center, scale(normalize(button.axis), BACKPLANE))


def _axis_x_hint(axis: Vec3) -> Vec3:
    hint = cross((0.0, 0.0, 1.0), normalize(axis))
    if norm(hint) <= 1e-9:
        return (1.0, 0.0, 0.0)
    return normalize(hint)


def oriented_box_between(
    p0: Vec3,
    p1: Vec3,
    x_hint: Vec3,
    width_x: float,
    width_y: float,
    *,
    label: str,
) -> Shape:
    """Create a centre-aligned rectangular prism between two world points."""
    delta = subtract(p1, p0)
    direction = normalize(delta)
    projected_x = subtract(x_hint, scale(direction, dot(x_hint, direction)))
    if norm(projected_x) <= 1e-9:
        projected_x = _axis_x_hint(direction)
    local_x = normalize(projected_x)
    midpoint = scale(add(p0, p1), 0.5)
    plane = Plane(origin=midpoint, x_dir=local_x, z_dir=direction)
    result = plane.location * Box(width_x, width_y, norm(delta))
    result.label = label
    return result


def contact_post(button: ButtonDatum, rear: float) -> Shape:
    axis = normalize(button.axis)
    p0 = subtract(button.center, scale(axis, rear - 0.10))
    p1 = subtract(button.center, scale(axis, BACKPLANE + 0.20))
    return oriented_box_between(
        p0,
        p1,
        _axis_x_hint(axis),
        POST_SIZE,
        POST_SIZE,
        label=f"{button.name}_contact_post",
    )


def _button_map() -> dict[str, ButtonDatum]:
    return {button.name: button for button in (*INDEX, *MIDDLE)}


@dataclass(slots=True)
class CarrierModel:
    name: str
    retainer_name: str
    components: dict[str, Shape]

    @property
    def compound(self) -> Compound:
        return Compound(children=list(self.components.values()), label=self.name)

    @property
    def volume(self) -> float:
        return sum(component.volume for component in self.components.values())


def build_shared_carrier_extension() -> CarrierModel:
    """Build the RWID-side I1-I3/M1-M3 extension as audited solids."""
    buttons = _button_map()
    components: dict[str, Shape] = {}
    for button in INDEX[:3]:
        components[f"{button.name}_post"] = contact_post(button, INDEX_REAR)
    for button in MIDDLE[:3]:
        components[f"{button.name}_post"] = contact_post(button, MIDDLE_REAR)

    node: dict[str, Vec3] = {
        name: back_node(button) for name, button in buttons.items()
    }
    node["DOGLEG"] = DOGLEG
    for number, (start, end, x_hint) in enumerate(SHARED_LINKS, start=1):
        label = f"JfD_backbone_{number}_{start}_{end}"
        components[f"backbone_{number}"] = oriented_box_between(
            node[start],
            node[end],
            x_hint,
            BEAM_WIDTH,
            BEAM_THICKNESS,
            label=label,
        )
    return CarrierModel("JfD_RWID_carrier_extension", "RWID", components)


def build_i4_carrier_extension() -> CarrierModel:
    """Build the independent RZKD-side I4/M4 extension as audited solids."""
    components = {
        "I4_post": contact_post(INDEX[3], INDEX_REAR),
        "M4_post": contact_post(MIDDLE[3], MIDDLE_REAR),
        "backbone_1": oriented_box_between(
            back_node(INDEX[3]),
            back_node(MIDDLE[3]),
            I4_LINK_X_HINT,
            BEAM_WIDTH,
            BEAM_THICKNESS,
            label="JaD_backbone_I4_M4",
        ),
    }
    return CarrierModel("JaD_RZKD_carrier_extension", "RZKD", components)


def build_all_carriers() -> tuple[CarrierModel, CarrierModel]:
    return build_shared_carrier_extension(), build_i4_carrier_extension()


def all_components(models: Iterable[CarrierModel]) -> Iterable[Shape]:
    for model in models:
        yield from model.components.values()
