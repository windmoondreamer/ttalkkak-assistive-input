FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/*
 * ITS-1105 INDEX downstream implementation.
 *
 * - Centers and external opening/cap datums are frozen.
 * - F2 axes are the <=0.408 degree design-envelope refinement.
 * - Fixed roots are rigid and receive four local hard-clearance channels.
 * - Distal terminals may be formed once before assembly.
 * - Rear spacers are four independent service parts; RWID/RZKD pads do not move.
 * - Existing cap is always first in the boss UNION; existing shell is only a
 *   SUBTRACTION target for the local channel and stop relief.
 */

export enum ITSIndexButton
{
    annotation { "Name" : "I1" } I1,
    annotation { "Name" : "I2" } I2,
    annotation { "Name" : "I3" } I3,
    annotation { "Name" : "I4" } I4
}

export enum ITSIndexStage
{
    annotation { "Name" : "A local fixed-root channel" } CHANNEL,
    annotation { "Name" : "B independent rear spacer" } SPACER,
    annotation { "Name" : "C cap boss and local stop relief" } CAP
}

const BTN = [
    { "p" : vector(-22.224, -17.494, 9.000),
      "n" : vector(-0.847667872, -0.506166919, -0.158915794),
      "n0" : vector(-0.9291, -0.2385, -0.2828),
      "roll90" : false, "dom" : true, "spacer" : 2.4403 },
    { "p" : vector(-15.970, -26.208, 9.000),
      "n" : vector(-0.387542111, -0.574231284, -0.721158474),
      "n0" : vector(-0.4724, -0.7368, -0.4838),
      "roll90" : false, "dom" : true, "spacer" : 2.4403 },
    { "p" : vector(-5.496, -29.325, 9.000),
      "n" : vector(-0.068454195, -0.997609880, 0.009410170),
      "n0" : vector(-0.0383, -0.9556, -0.2921),
      "roll90" : true, "dom" : true, "spacer" : 2.4403 },
    { "p" : vector(5.496, -29.325, 9.000),
      "n" : vector(0.024161, -0.968017, -0.249718),
      "n0" : vector(0.0383, -0.9556, -0.2921),
      "roll90" : true, "dom" : false, "spacer" : 2.4400 }
];

const DOM_WALL_PT = vector(-4.8872, 0.0000, -35.0000);
const OPP_WALL_PT = vector(4.8859, 0.0000, -35.0000);

const BODY_X = 6.18 * millimeter;
const BODY_REAR = 8.86 * millimeter;
const ROOT_DEPTH = 1.80 * millimeter;
const ROOT_OUTER = 7.90 * millimeter;
const ROOT_PITCH = 4.50 * millimeter;
const METAL_U = 0.30 * millimeter;
const METAL_V = 0.70 * millimeter;
const CHANNEL_CLEARANCE = 0.08 * millimeter;
const CHANNEL_START = 8.76 * millimeter;
const CHANNEL_TO = 12.70 * millimeter;
const KNEE_OVERLAP = 0.20 * millimeter;

const CAP_UNDERSIDE = 2.60 * millimeter;
const CURRENT_STOP = 2.80 * millimeter;
const DESIRED_FREE = 0.05 * millimeter;
const MAX_TRAVEL = 0.35 * millimeter;
const ACTUATOR_TOP = 2.86 * millimeter;
const CAP_RELIEF_W = 7.80 * millimeter;

function btnIndex(button is ITSIndexButton) returns number
{
    if (button == ITSIndexButton.I1) return 0;
    if (button == ITSIndexButton.I2) return 1;
    if (button == ITSIndexButton.I3) return 2;
    return 3;
}

function axisCS(b is map) returns CoordSystem
{
    const zA = normalize(b.n);
    const xA = normalize(cross(vector(0, 0, 1), zA));
    return coordSystem(b.p * millimeter, xA, zA);
}

function normalCS(b is map) returns CoordSystem
{
    const zA = normalize(b.n0);
    const xA = normalize(cross(vector(0, 0, 1), zA));
    return coordSystem(b.p * millimeter, xA, zA);
}

function rolledAxes(b is map) returns map
{
    const zA = normalize(b.n);
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

annotation { "Feature Type Name" : "ITS-1105 INDEX downstream" }
export const its1105Index = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Button" }
        definition.button is ITSIndexButton;
        annotation { "Name" : "Stage" }
        definition.stage is ITSIndexStage;
    }
    {
        const index = btnIndex(definition.button);
        const b = BTN[index];
        const axes = rolledAxes(b);
        const p = b.p * millimeter;
        const shell = qContainsPoint(qAllSolidBodies(),
            (b.dom ? DOM_WALL_PT : OPP_WALL_PT) * millimeter);

        if (definition.stage == ITSIndexStage.CHANNEL)
        {
            var tools = [];
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
                        - axes.z * CHANNEL_START;
                    const root1 = p + axes.u * (su * kneeU) + axes.v * (sv * ROOT_PITCH / 2)
                        - axes.z * (BODY_REAR + ROOT_DEPTH);
                    const rear = p + axes.u * (su * kneeU) + axes.v * (sv * ROOT_PITCH / 2)
                        - axes.z * CHANNEL_TO;
                    // The slanted rigid root and straight rear path must overlap at
                    // the knee.  A zero-length butt joint leaves a tessellated wedge
                    // contact even when both cross-sections have 0.08 mm clearance.
                    const rootDirection = normalize(root1 - root0);
                    const rootEnd = root1 + rootDirection * KNEE_OVERLAP;
                    const rearStart = root1 + axes.z * KNEE_OVERLAP;
                    segmentBox(context, id + ("root" ~ k), root0, rootEnd, axes.v, widthV, widthT);
                    tools = append(tools, qCreatedBy(id + ("root" ~ k), EntityType.BODY));
                    k += 1;
                    segmentBox(context, id + ("rear" ~ k), rearStart, rear, axes.v, widthV, widthT);
                    tools = append(tools, qCreatedBy(id + ("rear" ~ k), EntityType.BODY));
                    k += 1;
                }
            }
            opBoolean(context, id + "channelCut", {
                        "tools" : qUnion(tools),
                        "targets" : shell,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == ITSIndexStage.SPACER)
        {
            const zA = normalize(b.n);
            fCylinder(context, id + "spacer", {
                        "topCenter" : p - zA * BODY_REAR,
                        "bottomCenter" : p - zA * (BODY_REAR + b.spacer * millimeter),
                        "radius" : 1.80 * millimeter
                    });
        }
        else if (definition.stage == ITSIndexStage.CAP)
        {
            const zA = normalize(b.n);
            const n0 = normalize(b.n0);
            const cosine = dot(zA, n0);
            const freeGap = ACTUATOR_TOP * cosine - CAP_UNDERSIDE;
            const bossLength = freeGap - DESIRED_FREE;
            const capPoint = p - zA * (CAP_UNDERSIDE / cosine);
            fCylinder(context, id + "boss", {
                        "topCenter" : capPoint,
                        "bottomCenter" : capPoint - n0 * bossLength,
                        "radius" : 1.50 * millimeter
                    });
            const cap = qContainsPoint(qAllSolidBodies(), p);
            opBoolean(context, id + "capAdd", {
                        "tools" : qUnion([cap, qCreatedBy(id + "boss", EntityType.BODY)]),
                        "operationType" : BooleanOperationType.UNION
                    });

            const stopRelief = DESIRED_FREE + MAX_TRAVEL * cosine
                - (CURRENT_STOP - CAP_UNDERSIDE);
            depthBox(context, id + "stop", normalCS(b), CAP_RELIEF_W, CAP_RELIEF_W,
                CURRENT_STOP, CURRENT_STOP + stopRelief);
            opBoolean(context, id + "stopCut", {
                        "tools" : qCreatedBy(id + "stop", EntityType.BODY),
                        "targets" : shell,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
    });
