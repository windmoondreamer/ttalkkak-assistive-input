FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/*
 * ITS-1105 MIDDLE actual implementation.
 *
 * One atomic feature per button creates:
 *   - an 8.4 mm guided cap opening and axis-aligned stem bore,
 *   - a parameterized 6.4 mm switch seat,
 *   - an 8.0 mm local support ring (not a generic 6 mm cube holder),
 *   - four rigid-root channels with 0.08 mm metal clearance,
 *   - two integrated rear snap beams/hooks,
 *   - one independent 2.44 mm rear spacer,
 *   - one independent 8.0 mm cap with guided stem and two stop lugs.
 *
 * Existing shell is always first in positive UNION operations.  M1..M3 are
 * owned by JfD and M4 by JaD.  A global split-side trim prevents any new
 * positive support from bridging the two identity bodies.
 */

export enum ITSMiddleButton
{
    annotation { "Name" : "M1" } M1,
    annotation { "Name" : "M2" } M2,
    annotation { "Name" : "M3" } M3,
    annotation { "Name" : "M4" } M4
}

const BTN = [
    { "p" : vector(-19.835372272, -0.614991709, -11.125000000),
      "n" : vector(-0.961658811, -0.158356278, -0.223909849),
      "a" : vector(-0.837518998, -0.499950062, -0.220480981),
      "roll90" : true, "dom" : true },
    { "p" : vector(-12.899418190, -8.744828192, -14.125000000),
      "n" : vector(-0.486144819, -0.708160212, -0.512027664),
      "a" : vector(-0.601521153, -0.782846337, -0.159134899),
      "roll90" : true, "dom" : true },
    { "p" : vector(-3.537874175, -14.413708840, -11.125000000),
      "n" : vector(-0.103551539, -0.791264502, -0.602642155),
      "a" : vector(0.320428890, -0.733472608, -0.599452466),
      "roll90" : false, "dom" : true },
    { "p" : vector(7.444327590, -13.569623472, -11.125000000),
      "n" : vector(0.224859127, -0.772792774, -0.593489428),
      "a" : vector(0.224859127, -0.772792774, -0.593489428),
      "roll90" : false, "dom" : false }
];

const DOM_WALL_PT = vector(-4.8872, 0.0000, -35.0000);
const OPP_WALL_PT = vector(4.8859, 0.0000, -35.0000);

const TRIM_DEPTH = 2.80 * millimeter;
const SUPPORT_FROM = 2.20 * millimeter;
const BODY_FRONT = 5.279587617 * millimeter;
const BODY_REAR = 8.839587617 * millimeter;
const SPACER_REAR = 11.279587617 * millimeter;
const CHANNEL_TO = 12.279587617 * millimeter;
const POCKET = 6.40 * millimeter;
const OUTER_SUPPORT = 10.00 * millimeter;
const CAP_OPENING = 8.40 * millimeter;
const CAP_SIZE = 8.00 * millimeter;
const BODY_X = 6.18 * millimeter;
const ROOT_DEPTH = 1.80 * millimeter;
const ROOT_OUTER = 7.90 * millimeter;
const ROOT_PITCH = 4.50 * millimeter;
const METAL_U = 0.30 * millimeter;
const METAL_V = 0.70 * millimeter;
const CHANNEL_CLEARANCE = 0.08 * millimeter;
const KNEE_OVERLAP = 0.20 * millimeter;
const ACTUATOR_TOP = 2.839587617 * millimeter;
const CAP_FREE_NORMAL = 0.05 * millimeter;

function btnIndex(button is ITSMiddleButton) returns number
{
    if (button == ITSMiddleButton.M1) return 0;
    if (button == ITSMiddleButton.M2) return 1;
    if (button == ITSMiddleButton.M3) return 2;
    return 3;
}

function axesFor(b is map) returns map
{
    const zA = normalize(b.a);
    const u0 = normalize(cross(vector(0, 0, 1), zA));
    const v0 = normalize(cross(zA, u0));
    return { "u" : b.roll90 ? v0 : u0,
             "v" : b.roll90 ? -u0 : v0,
             "z" : zA };
}

function axisCS(b is map) returns CoordSystem
{
    const zA = normalize(b.a);
    return coordSystem(b.p * millimeter,
        normalize(cross(vector(0, 0, 1), zA)), zA);
}

function normalCS(b is map) returns CoordSystem
{
    const zA = normalize(b.n);
    return coordSystem(b.p * millimeter,
        normalize(cross(vector(0, 0, 1), zA)), zA);
}

function depthBox(context is Context, boxId is Id, cs is CoordSystem,
    width is ValueWithUnits, height is ValueWithUnits,
    dFrom is ValueWithUnits, dTo is ValueWithUnits)
{
    fCuboid(context, boxId, {
                "corner1" : vector(-width / 2, -height / 2, -dTo),
                "corner2" : vector(width / 2, height / 2, -dFrom)
            });
    opTransform(context, boxId + "xf", {
                "bodies" : qCreatedBy(boxId, EntityType.BODY),
                "transform" : toWorld(cs)
            });
}

function offsetDepthBox(context is Context, boxId is Id, cs is CoordSystem,
    centerU is ValueWithUnits, centerV is ValueWithUnits,
    width is ValueWithUnits, height is ValueWithUnits,
    dFrom is ValueWithUnits, dTo is ValueWithUnits)
{
    fCuboid(context, boxId, {
                "corner1" : vector(centerU - width / 2, centerV - height / 2, -dTo),
                "corner2" : vector(centerU + width / 2, centerV + height / 2, -dFrom)
            });
    opTransform(context, boxId + "xf", {
                "bodies" : qCreatedBy(boxId, EntityType.BODY),
                "transform" : toWorld(cs)
            });
}

function segmentBox(context is Context, boxId is Id,
    p0 is Vector, p1 is Vector, xAxis is Vector,
    widthX is ValueWithUnits, widthY is ValueWithUnits)
{
    const direction = normalize(p1 - p0);
    const length = norm(p1 - p0);
    const cs = coordSystem((p0 + p1) / 2, normalize(xAxis), direction);
    fCuboid(context, boxId, {
                "corner1" : vector(-widthX / 2, -widthY / 2, -length / 2),
                "corner2" : vector(widthX / 2, widthY / 2, length / 2)
            });
    opTransform(context, boxId + "xf", {
                "bodies" : qCreatedBy(boxId, EntityType.BODY),
                "transform" : toWorld(cs)
            });
}

annotation { "Feature Type Name" : "ITS-1105 MIDDLE button" }
export const its1105Middle = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Button" }
        definition.button is ITSMiddleButton;
    }
    {
        const index = btnIndex(definition.button);
        const b = BTN[index];
        const p = b.p * millimeter;
        const a = normalize(b.a);
        const n = normalize(b.n);
        const axes = axesFor(b);
        const acs = axisCS(b);
        const ncs = normalCS(b);
        const shell = qContainsPoint(qAllSolidBodies(),
            (b.dom ? DOM_WALL_PT : OPP_WALL_PT) * millimeter);

        // ITS-specific positive support: local seat ring plus two snap beams
        // and rear hooks.  All components overlap; no generic 6 mm cube body.
        depthBox(context, id + "ring", acs, OUTER_SUPPORT, OUTER_SUPPORT,
            SUPPORT_FROM, BODY_REAR + 0.40 * millimeter);
        for (var sign in [-1, 1])
        {
            var railU = sign * 4.60 * millimeter;
            var hookU = sign * 2.75 * millimeter;
            if (index == 2 && sign == 1)
                railU = 3.20 * millimeter;
            if (index == 3 && sign == -1)
            {
                railU = -3.80 * millimeter;
                hookU = -2.50 * millimeter;
            }
            offsetDepthBox(context, id + ("beam" ~ sign), acs,
                railU, 0 * millimeter,
                0.80 * millimeter, 3.20 * millimeter,
                SUPPORT_FROM, SPACER_REAR + 0.40 * millimeter);
            offsetDepthBox(context, id + ("hook" ~ sign), acs,
                hookU, 0 * millimeter,
                3.10 * millimeter, 3.20 * millimeter,
                SPACER_REAR, SPACER_REAR + 0.70 * millimeter);
        }

        // The 10.0 mm ring leaves a 0.80 mm structural annulus around the
        // 8.40 mm cap guide.  M3/M4 ring material is split-trimmed before union.
        var ringQuery = qCreatedBy(id + "ring", EntityType.BODY);
        if (index == 2 || index == 3)
        {
            fCuboid(context, id + "splitClip", {
                        "corner1" : index == 2
                            ? vector(-0.50 * millimeter, -100 * millimeter, -100 * millimeter)
                            : vector(-100 * millimeter, -100 * millimeter, -100 * millimeter),
                        "corner2" : index == 2
                            ? vector(100 * millimeter, 100 * millimeter, 100 * millimeter)
                            : vector(0.50 * millimeter, 100 * millimeter, 100 * millimeter)
                    });
            opBoolean(context, id + "supportTrim", {
                        "tools" : qCreatedBy(id + "splitClip", EntityType.BODY),
                        "targets" : qCreatedBy(id + "ring", EntityType.BODY),
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
            // The subtraction modifies the original ring; it does not create a
            // new body owned by supportTrim.  Keep the original tracking query.
        }
        var ringTools = [shell, ringQuery];
        if (index == 2)
        {
            // Local -u is the INDEX-clear side.  This small anchor overlaps
            // the native JfD wall volumetrically (not merely at a tangent),
            // while staying 5.8 mm from the frozen INDEX keep-out.
            offsetDepthBox(context, id + "shellAnchor", acs,
                -4.40 * millimeter, 0 * millimeter,
                1.60 * millimeter, 1.60 * millimeter,
                1.20 * millimeter, 3.60 * millimeter);
            ringTools = append(ringTools,
                qCreatedBy(id + "shellAnchor", EntityType.BODY));
        }
        // Establish ring ownership first.  Then absorb the two continuous side
        // rail/hook clusters independently so a disconnected tool can never
        // hide inside a large multi-body boolean.
        opBoolean(context, id + "ringAdd", {
                    "tools" : qUnion(ringTools),
                    "operationType" : BooleanOperationType.UNION
                });
        for (var sign in [-1, 1])
        {
            opBoolean(context, id + ("sideAdd" ~ sign), {
                        "tools" : qUnion([shell,
                            qCreatedBy(id + ("beam" ~ sign), EntityType.BODY),
                            qCreatedBy(id + ("hook" ~ sign), EntityType.BODY)]),
                        "operationType" : BooleanOperationType.UNION
                    });
        }

        // Cap guide opening, axis-aligned stem bore, and 6.4 body seat.
        depthBox(context, id + "opening", ncs, CAP_OPENING, CAP_OPENING,
            -0.50 * millimeter, TRIM_DEPTH);
        opBoolean(context, id + "openingCut", {
                    "tools" : qCreatedBy(id + "opening", EntityType.BODY),
                    "targets" : shell,
                    "operationType" : BooleanOperationType.SUBTRACTION
                });
        fCylinder(context, id + "bore", {
                    "topCenter" : p + a * 0.60 * millimeter,
                    "bottomCenter" : p - a * (BODY_FRONT + 0.20 * millimeter),
                    "radius" : 2.25 * millimeter
                });
        opBoolean(context, id + "boreCut", {
                    "tools" : qCreatedBy(id + "bore", EntityType.BODY),
                    "targets" : shell,
                    "operationType" : BooleanOperationType.SUBTRACTION
                });
        depthBox(context, id + "seat", acs, POCKET, POCKET,
            BODY_FRONT, BODY_REAR + 0.20 * millimeter);
        opBoolean(context, id + "seatCut", {
                    "tools" : qCreatedBy(id + "seat", EntityType.BODY),
                    "targets" : shell,
                    "operationType" : BooleanOperationType.SUBTRACTION
                });

        // Four drawing-nominal fixed roots.  Each slanted root overlaps its
        // straight rear path by 0.20 mm to prevent zero-distance knee wedges.
        var channels = [];
        var k = 0;
        const startU = BODY_X / 2 + METAL_U / 2;
        const kneeU = (ROOT_OUTER - METAL_U) / 2;
        const widthV = METAL_V + 2 * CHANNEL_CLEARANCE;
        const widthT = METAL_U + 2 * CHANNEL_CLEARANCE;
        for (var su in [-1, 1])
        {
            for (var sv in [-1, 1])
            {
                const root0 = p + axes.u * (su * startU) + axes.v * (sv * ROOT_PITCH / 2)
                    - axes.z * (BODY_REAR - 0.10 * millimeter);
                const root1 = p + axes.u * (su * kneeU) + axes.v * (sv * ROOT_PITCH / 2)
                    - axes.z * (BODY_REAR + ROOT_DEPTH);
                const rear = p + axes.u * (su * kneeU) + axes.v * (sv * ROOT_PITCH / 2)
                    - axes.z * CHANNEL_TO;
                const rootDirection = normalize(root1 - root0);
                segmentBox(context, id + ("root" ~ k), root0,
                    root1 + rootDirection * KNEE_OVERLAP, axes.v, widthV, widthT);
                channels = append(channels, qCreatedBy(id + ("root" ~ k), EntityType.BODY));
                k += 1;
                segmentBox(context, id + ("rear" ~ k), root1 + axes.z * KNEE_OVERLAP,
                    rear, axes.v, widthV, widthT);
                channels = append(channels, qCreatedBy(id + ("rear" ~ k), EntityType.BODY));
                k += 1;
            }
        }
        opBoolean(context, id + "channelCut", {
                    "tools" : qUnion(channels),
                    "targets" : shell,
                    "operationType" : BooleanOperationType.SUBTRACTION
                });

        // Independent body-contact spacer; rear hooks retain its back face.
        fCylinder(context, id + "spacer", {
                    "topCenter" : p - a * BODY_REAR,
                    "bottomCenter" : p - a * SPACER_REAR,
                    "radius" : 1.80 * millimeter
                });

        // Independent guided cap.  The two offset stop lugs meet the 2.80 mm
        // opening floor after 0.45 mm normal travel.  The minimum projected
        // actuator travel is 0.363 mm (> drawing upper travel 0.35 mm).
        depthBox(context, id + "cap", ncs, CAP_SIZE, CAP_SIZE,
            -0.20 * millimeter, 1.60 * millimeter);
        const cosine = dot(n, a);
        fCylinder(context, id + "stem", {
                    "topCenter" : p + a * 0.80 * millimeter,
                    "bottomCenter" : p - a * (ACTUATOR_TOP - CAP_FREE_NORMAL * cosine),
                    "radius" : 1.50 * millimeter
                });
        const capU = normalize(cross(vector(0, 0, 1), n));
        var capTools = [qCreatedBy(id + "cap", EntityType.BODY),
                        qCreatedBy(id + "stem", EntityType.BODY)];
        for (var sign in [-1, 1])
        {
            const lugPoint = p + capU * (sign * 3.00 * millimeter);
            fCylinder(context, id + ("lug" ~ sign), {
                        "topCenter" : lugPoint - n * 1.55 * millimeter,
                        "bottomCenter" : lugPoint - n * 2.35 * millimeter,
                        "radius" : 0.45 * millimeter
                    });
            capTools = append(capTools, qCreatedBy(id + ("lug" ~ sign), EntityType.BODY));
        }
        opBoolean(context, id + "capMerge", {
                    "tools" : qUnion(capTools),
                    "operationType" : BooleanOperationType.UNION
                });
    });
