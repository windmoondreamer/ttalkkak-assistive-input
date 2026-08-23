FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/*
 * OneGrip simplified INDEX/MIDDLE internals.
 *
 * Preconditions outside this feature:
 *   - suppress the four legacy ITS-1105 MIDDLE atomic features;
 *   - suppress the four legacy INDEX SPACER features only;
 *   - keep INDEX openings/holders/channels/caps, RWID/RZKD fastening and THUMB.
 *
 * Result:
 *   - no independent finger spacers;
 *   - no MIDDLE 0.80 mm side beams or 0.70 mm hooks;
 *   - RWID becomes the common I1-I3 + M1-M3 clamp carrier;
 *   - RZKD becomes the common I4 + M4 clamp carrier;
 *   - MIDDLE uses clean open-rear seats and INDEX-style plain caps;
 *   - visible cap target is 7.6 mm and +1.4 mm exposure.
 */

const INDEX = [
    { "p" : vector(-22.224, -17.494, 9.000),
      "a" : vector(-0.847667872, -0.506166919, -0.158915794),
      "n" : vector(-0.9291, -0.2385, -0.2828), "dom" : true },
    { "p" : vector(-15.970, -26.208, 9.000),
      "a" : vector(-0.387542111, -0.574231284, -0.721158474),
      "n" : vector(-0.4724, -0.7368, -0.4838), "dom" : true },
    { "p" : vector(-5.496, -29.325, 9.000),
      "a" : vector(-0.068454195, -0.997609880, 0.009410170),
      "n" : vector(-0.0383, -0.9556, -0.2921), "dom" : true },
    { "p" : vector(5.496, -29.325, 9.000),
      "a" : vector(0.024161000, -0.968017000, -0.249718000),
      "n" : vector(0.0383, -0.9556, -0.2921), "dom" : false }
];

const MIDDLE = [
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

const BACKPLANE = 14.50 * millimeter;
const POST = 3.60 * millimeter;
const BEAM_W = 3.20 * millimeter;
const BEAM_T = 4.00 * millimeter;
const INDEX_REAR = 8.86 * millimeter;

const SUPPORT_FROM = 2.20 * millimeter;
const BODY_FRONT = 5.279587617 * millimeter;
const BODY_REAR = 8.839587617 * millimeter;
const CHANNEL_TO = 12.279587617 * millimeter;
const POCKET = 6.40 * millimeter;
const OUTER_SUPPORT = 10.00 * millimeter;
const CAP_OPENING = 8.00 * millimeter;
const CAP_SIZE = 7.60 * millimeter;
const ROOT_DEPTH = 1.80 * millimeter;
const ROOT_OUTER = 7.90 * millimeter;
const ROOT_PITCH = 4.50 * millimeter;
const BODY_X = 6.18 * millimeter;
const METAL_U = 0.30 * millimeter;
const METAL_V = 0.70 * millimeter;
const CHANNEL_CLEARANCE = 0.08 * millimeter;
const KNEE_OVERLAP = 0.20 * millimeter;
const ACTUATOR_TOP = 2.839587617 * millimeter;
const CAP_FREE_NORMAL = 0.05 * millimeter;
const HOLDER_FRONT_TRIM = 2.20 * millimeter;

const DOGLEG = vector(-3.181, 5.414, -1.125) * millimeter;

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

function rolledAxes(b is map) returns map
{
    const zA = normalize(b.a);
    const u0 = normalize(cross(vector(0, 0, 1), zA));
    const v0 = normalize(cross(zA, u0));
    return { "u" : b.roll90 ? v0 : u0,
             "v" : b.roll90 ? -u0 : v0,
             "z" : zA };
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
    // The supplied vector is an orientation hint.  Project it onto the
    // segment-normal plane so coordSystem receives exactly perpendicular
    // axes even after decimal rounding of the audited direction data.
    const xPerpendicular = normalize(xAxis - direction * dot(xAxis, direction));
    const cs = coordSystem((p0 + p1) / 2, xPerpendicular, direction);
    fCuboid(context, boxId, {
                "corner1" : vector(-widthX / 2, -widthY / 2, -length / 2),
                "corner2" : vector(widthX / 2, widthY / 2, length / 2)
            });
    opTransform(context, boxId + "xf", {
                "bodies" : qCreatedBy(boxId, EntityType.BODY),
                "transform" : toWorld(cs)
            });
}

function backNode(b is map) returns Vector
{
    return b.p * millimeter - normalize(b.a) * BACKPLANE;
}

function addPost(context is Context, postId is Id, b is map,
    rear is ValueWithUnits)
{
    depthBox(context, postId, axisCS(b), POST, POST,
        rear - 0.10 * millimeter, BACKPLANE + 0.20 * millimeter);
}

function trimSplitRing(context is Context, id is Id, ringId is Id, index is number)
{
    if (index != 2 && index != 3)
        return;
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
                "targets" : qCreatedBy(ringId, EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
            });
}

function rebuildMiddleButton(context is Context, id is Id, b is map, index is number)
{
    const p = b.p * millimeter;
    const a = normalize(b.a);
    const n = normalize(b.n);
    const axes = rolledAxes(b);
    const acs = axisCS(b);
    const ncs = normalCS(b);
    const shell = qContainsPoint(qAllSolidBodies(),
        (b.dom ? DOM_WALL_PT : OPP_WALL_PT) * millimeter);

    depthBox(context, id + "ring", acs, OUTER_SUPPORT, OUTER_SUPPORT,
        SUPPORT_FROM, BODY_REAR + 0.40 * millimeter);
    trimSplitRing(context, id, id + "ring", index);
    var supportTargets = [qCreatedBy(id + "ring", EntityType.BODY)];
    if (index == 2)
    {
        offsetDepthBox(context, id + "shellAnchor", acs,
            -4.40 * millimeter, 0 * millimeter,
            1.60 * millimeter, 1.60 * millimeter,
            1.20 * millimeter, 3.60 * millimeter);
        supportTargets = append(supportTargets,
            qCreatedBy(id + "shellAnchor", EntityType.BODY));
    }

    // INDEX-style front trim.  The holder axis may differ from the shell
    // normal, but no holder corner is allowed to emerge through the skin.
    // Keeping material behind 2.20 mm still leaves positive overlap with the
    // nominal 3.0-mm shell wall.
    depthBox(context, id + "frontTrim", ncs,
        20.00 * millimeter, 20.00 * millimeter,
        -20.00 * millimeter, HOLDER_FRONT_TRIM);
    opBoolean(context, id + "supportFrontTrim", {
                "tools" : qCreatedBy(id + "frontTrim", EntityType.BODY),
                "targets" : qUnion(supportTargets),
                "operationType" : BooleanOperationType.SUBTRACTION
            });

    var ringTools = [shell];
    for (var target in supportTargets)
        ringTools = append(ringTools, target);
    opBoolean(context, id + "ringAdd", {
                "tools" : qUnion(ringTools),
                "operationType" : BooleanOperationType.UNION
            });

    depthBox(context, id + "opening", ncs, CAP_OPENING, CAP_OPENING,
        -0.50 * millimeter, 2.80 * millimeter);
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
            segmentBox(context, id + ("rear" ~ k),
                root1 + axes.z * KNEE_OVERLAP, rear, axes.v, widthV, widthT);
            channels = append(channels, qCreatedBy(id + ("rear" ~ k), EntityType.BODY));
            k += 1;
        }
    }
    opBoolean(context, id + "channelCut", {
                "tools" : qUnion(channels),
                "targets" : shell,
                "operationType" : BooleanOperationType.SUBTRACTION
            });

    // INDEX-style cap: one square pad and one central contact stem only.
    // There are no MIDDLE-specific lugs, hooks or thin retention details.
    depthBox(context, id + "cap", ncs, CAP_SIZE, CAP_SIZE,
        -1.40 * millimeter, 1.60 * millimeter);
    const cosine = dot(n, a);
    fCylinder(context, id + "stem", {
                "topCenter" : p + a * 0.80 * millimeter,
                "bottomCenter" : p - a * (ACTUATOR_TOP - CAP_FREE_NORMAL * cosine),
                "radius" : 1.50 * millimeter
            });
    var capTools = [qCreatedBy(id + "cap", EntityType.BODY),
                    qCreatedBy(id + "stem", EntityType.BODY)];
    opBoolean(context, id + "capMerge", {
                "tools" : qUnion(capTools),
                "operationType" : BooleanOperationType.UNION
            });
}

annotation { "Feature Type Name" : "OneGrip simplified finger internals" }
export const oneGripSimplifiedFingerInternals = defineFeature(function(context is Context,
    id is Id, definition is map)
    precondition
    {
    }
    {
        // The verified back-plane contact points lie strictly inside the
        // existing RWID and RZKD pads.  Point ownership is more robust here
        // than asking users to re-enter creating-feature ids.
        const rwid = qContainsPoint(qAllSolidBodies(), backNode(INDEX[2]));
        const rzkd = qContainsPoint(qAllSolidBodies(), backNode(INDEX[3]));

        // Rebuild clean MIDDLE seats/caps first.  No spacer, rail or rear hook.
        for (var i = 0; i < size(MIDDLE); i += 1)
            rebuildMiddleButton(context, id + ("m" ~ i), MIDDLE[i], i);

        // Absorb all INDEX spacer functions into the two retained carriers.
        var sharedTools = [rwid];
        for (var i = 0; i < 3; i += 1)
        {
            addPost(context, id + ("ip" ~ i), INDEX[i], INDEX_REAR);
            sharedTools = append(sharedTools, qCreatedBy(id + ("ip" ~ i), EntityType.BODY));
        }
        addPost(context, id + "ip3", INDEX[3], INDEX_REAR);

        // MIDDLE central contact posts replace all four independent spacers.
        for (var i = 0; i < 3; i += 1)
        {
            addPost(context, id + ("mp" ~ i), MIDDLE[i], BODY_REAR);
            sharedTools = append(sharedTools, qCreatedBy(id + ("mp" ~ i), EntityType.BODY));
        }
        addPost(context, id + "mp3", MIDDLE[3], BODY_REAR);

        // JfD backbone: I3 -> M3 -> dogleg -> M2 -> M1.
        segmentBox(context, id + "jb0", backNode(INDEX[2]), backNode(MIDDLE[2]),
            vector(0.211301290, 0.731289520, 0.648511680), BEAM_W, BEAM_T);
        segmentBox(context, id + "jb1", backNode(MIDDLE[2]), DOGLEG,
            vector(-0.843215940, 0.490299570, -0.220438680), BEAM_W, BEAM_T);
        segmentBox(context, id + "jb2", DOGLEG, backNode(MIDDLE[1]),
            vector(0.995963070, -0.022796690, -0.086820900), BEAM_W, BEAM_T);
        segmentBox(context, id + "jb3", backNode(MIDDLE[1]), backNode(MIDDLE[0]),
            vector(0.847015100, 0.382384410, 0.369252730), BEAM_W, BEAM_T);
        for (var k = 0; k < 4; k += 1)
            sharedTools = append(sharedTools, qCreatedBy(id + ("jb" ~ k), EntityType.BODY));

        opBoolean(context, id + "sharedCarrierAdd", {
                    "tools" : qUnion(sharedTools),
                    "operationType" : BooleanOperationType.UNION
                });

        // JaD backbone: I4 -> M4.
        segmentBox(context, id + "ab0", backNode(INDEX[3]), backNode(MIDDLE[3]),
            vector(0.041113690, 0.761210510, 0.647200300), BEAM_W, BEAM_T);
        opBoolean(context, id + "i4CarrierAdd", {
                    "tools" : qUnion([rzkd,
                                qCreatedBy(id + "ip3", EntityType.BODY),
                                qCreatedBy(id + "mp3", EntityType.BODY),
                                qCreatedBy(id + "ab0", EntityType.BODY)]),
                    "operationType" : BooleanOperationType.UNION
                });

        // Existing INDEX openings, holders, channels, caps and travel remain
        // untouched.  MIDDLE follows their external language; INDEX geometry
        // is not edited merely for visual matching.
    });
