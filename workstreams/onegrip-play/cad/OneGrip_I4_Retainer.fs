FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/* ============================================================================
   OneGrip Play — I4 separate removable rear retainer

   ISOLATION RULE:
   - I1/I2/I3 shared retainer (RWID), JfD fastening, and their Feature Studio
     are frozen at version INDEX_SHARED_RET_FINAL.
   - This feature creates a separate I4 retainer NEW PART and touches JaD only
     for the new downstream boss and pilot hole.
   - Existing I4 holder / seat / opening / cap are not modified.

   I4 source of truth:
     p    = (+5.496, -29.325, +9.000) mm
     axis = (+0.024161, -0.968017, -0.249718)
     switch rear depth = 11.3 mm, holder rear depth = 12.5 mm

   Adopted architecture:
     split-relieved 6.5 x 10 x 2.8 mm flat plate (u = -1.5 .. +5.0)
     + 3.6 x 3.6 mm axial contact pad
     + one OD 7.0 mm fastening ear
     + JaD-only OD 6.0 mm downstream boss

   Screw dimensions are PROVISIONAL. No M2 SKU is declared final.
   ============================================================================ */

export enum I4RetStage
{
    annotation { "Name" : "A flat plate blank (NEW PART)" }
    BLANK,
    annotation { "Name" : "B contact pad" }
    PAD,
    annotation { "Name" : "C wiring notch" }
    NOTCH,
    annotation { "Name" : "D fastening ear" }
    EAR,
    annotation { "Name" : "E JaD boss" }
    BOSS,
    annotation { "Name" : "F screw clearance + pilot" }
    HOLE
}

export enum I4Preload
{
    annotation { "Name" : "0.10 mm" }
    LOW,
    annotation { "Name" : "0.15 mm nominal" }
    NOMINAL,
    annotation { "Name" : "0.20 mm" }
    HIGH
}

const I4_P = vector(5.496, -29.325, 9.000);
const I4_N = vector(0.024161, -0.968017, -0.249718);

const OPP_WALL_PT = vector(4.8859, 0.0000, -35.0000);

const SW_REAR = 11.3 * millimeter;
const HOLDER_REAR = 12.5 * millimeter;
const PLATE_FROM = 12.7 * millimeter;  // 0.2 mm axial gap from holder rear
const PLATE_TO = 15.5 * millimeter;
const PAD_TO = 13.2 * millimeter;      // 0.5 mm union overlap with plate

const EAR_U = 7.0 * millimeter;
const EAR_OD = 7.0 * millimeter;
const EAR_FROM = 12.7 * millimeter;
const EAR_TO = 16.2 * millimeter;

// All fastening dimensions remain provisional until the actual screw SKU is fixed.
const SCREW_D = 2.0 * millimeter;
const SCREW_CLR = 0.2 * millimeter;
const PILOT_D = 1.7 * millimeter;
// OD 6.0 with pilot 1.7 leaves a 2.15 mm radial wall (structural target >= 2.0).
const BOSS_OD = 6.0 * millimeter;
const BOSS_FROM = 8.0 * millimeter;
const BOSS_TO = 12.5 * millimeter;

function i4CS() returns CoordSystem
{
    const zA = normalize(I4_N);
    const xA = normalize(cross(vector(0, 0, 1), zA));
    return coordSystem(I4_P * millimeter, xA, zA);
}

function offsetCS(cs is CoordSystem, uOff is ValueWithUnits, vOff is ValueWithUnits)
    returns CoordSystem
{
    const vA = cross(cs.zAxis, cs.xAxis);
    return coordSystem(cs.origin + cs.xAxis * uOff + vA * vOff, cs.xAxis, cs.zAxis);
}

function localBox(context is Context, boxId is Id, cs is CoordSystem,
    u0 is ValueWithUnits, u1 is ValueWithUnits,
    v0 is ValueWithUnits, v1 is ValueWithUnits,
    dFrom is ValueWithUnits, dTo is ValueWithUnits)
{
    fCuboid(context, boxId, {
                "corner1" : vector(u0, v0, -dTo),
                "corner2" : vector(u1, v1, -dFrom)
            });
    opTransform(context, boxId + "xf", {
                "bodies" : qCreatedBy(boxId, EntityType.BODY),
                "transform" : toWorld(cs)
            });
}

function depthCyl(context is Context, cylId is Id, cs is CoordSystem,
    radius is ValueWithUnits, dFrom is ValueWithUnits, dTo is ValueWithUnits)
{
    fCylinder(context, cylId, {
                "topCenter" : vector(0 * millimeter, 0 * millimeter, -dFrom),
                "bottomCenter" : vector(0 * millimeter, 0 * millimeter, -dTo),
                "radius" : radius
            });
    opTransform(context, cylId + "xf", {
                "bodies" : qCreatedBy(cylId, EntityType.BODY),
                "transform" : toWorld(cs)
            });
}

function preloadValue(p is I4Preload) returns ValueWithUnits
{
    if (p == I4Preload.LOW)
        return 0.10 * millimeter;
    if (p == I4Preload.HIGH)
        return 0.20 * millimeter;
    return 0.15 * millimeter;
}

annotation { "Feature Type Name" : "OneGrip I4 separate retainer" }
export const oneGripI4Retainer = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Stage" }
        definition.stage is I4RetStage;
        annotation { "Name" : "Retainer blank feature id" }
        definition.bodyId is string;
        annotation { "Name" : "Provisional preload" }
        definition.preload is I4Preload;
    }
    {
        const cs = i4CS();

        if (definition.stage == I4RetStage.BLANK)
        {
            // Shared-freeze correction: RWID fastening reaches X=+3.1744 mm.
            // u=-5 produced an actual RWID/I4 intersection.  Trimming only the unused
            // split-side plate edge to u=-1.5 gives min X=+3.5908 mm and leaves the
            // centered pad, notch, ear, holder, seat, opening and cap unchanged.
            localBox(context, id + "plate", cs,
                -1.5 * millimeter, 5 * millimeter,
                -5 * millimeter, 5 * millimeter,
                PLATE_FROM, PLATE_TO);
            return;
        }

        const body = qCreatedBy(makeId(definition.bodyId), EntityType.BODY);

        if (definition.stage == I4RetStage.PAD)
        {
            const pre = preloadValue(definition.preload);
            localBox(context, id + "pad", cs,
                -1.8 * millimeter, 1.8 * millimeter,
                -1.8 * millimeter, 1.8 * millimeter,
                SW_REAR - pre, PAD_TO);
            opBoolean(context, id + "padadd", {
                        "tools" : qUnion([body, qCreatedBy(id + "pad", EntityType.BODY)]),
                        "operationType" : BooleanOperationType.UNION
                    });
        }
        else if (definition.stage == I4RetStage.NOTCH)
        {
            // Edge-open -v wiring notch. It remains 0.4 mm away from the 3.6 mm pad.
            localBox(context, id + "notch", cs,
                -1.25 * millimeter, 1.25 * millimeter,
                -5.2 * millimeter, -2.2 * millimeter,
                PLATE_FROM - 0.2 * millimeter, PLATE_TO + 0.2 * millimeter);
            opBoolean(context, id + "notchcut", {
                        "tools" : qCreatedBy(id + "notch", EntityType.BODY),
                        "targets" : body,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == I4RetStage.EAR)
        {
            const ecs = offsetCS(cs, EAR_U, 0 * millimeter);
            depthCyl(context, id + "ear", ecs, EAR_OD / 2, EAR_FROM, EAR_TO);
            opBoolean(context, id + "earadd", {
                        "tools" : qUnion([body, qCreatedBy(id + "ear", EntityType.BODY)]),
                        "operationType" : BooleanOperationType.UNION
                    });
        }
        else if (definition.stage == I4RetStage.BOSS)
        {
            // JaD-only positive feature. Existing JaD target is first to preserve partId.
            const ecs = offsetCS(cs, EAR_U, 0 * millimeter);
            depthCyl(context, id + "boss", ecs, BOSS_OD / 2, BOSS_FROM, BOSS_TO);
            const shell = qContainsPoint(qAllSolidBodies(), OPP_WALL_PT * millimeter);
            opBoolean(context, id + "bossadd", {
                        "tools" : qUnion([shell, qCreatedBy(id + "boss", EntityType.BODY)]),
                        "operationType" : BooleanOperationType.UNION
                    });
        }
        else if (definition.stage == I4RetStage.HOLE)
        {
            const ecs = offsetCS(cs, EAR_U, 0 * millimeter);

            // Retainer clearance hole: provisional 2.0 + 2 x 0.2 = 2.4 mm.
            depthCyl(context, id + "clr", ecs, (SCREW_D + 2 * SCREW_CLR) / 2,
                EAR_FROM - 0.5 * millimeter, EAR_TO + 0.5 * millimeter);
            opBoolean(context, id + "clrcut", {
                        "tools" : qCreatedBy(id + "clr", EntityType.BODY),
                        "targets" : body,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });

            // JaD boss/holder pilot only. Original Screw_holes are untouched.
            depthCyl(context, id + "pilot", ecs, PILOT_D / 2,
                BOSS_FROM - 0.5 * millimeter, BOSS_TO + 0.2 * millimeter);
            const shell = qContainsPoint(qAllSolidBodies(), OPP_WALL_PT * millimeter);
            opBoolean(context, id + "pilotcut", {
                        "tools" : qCreatedBy(id + "pilot", EntityType.BODY),
                        "targets" : shell,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
    });
