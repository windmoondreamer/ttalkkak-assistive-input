FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/*
 * OneGrip Play — original THUMB MODULE rigid reseating, housing-first lower-15 revision.
 *
 * HARD GATES
 * - This feature translates the original in-place Backplate and eight original
 *   button caps as one rigid set.  It does not recreate, scale, rotate, or edit
 *   any member of the module.
 * - The Small_joystick_attachment body is intentionally excluded here because
 *   it is modelled at a Part Studio staging position and is located by assembly
 *   mates.  The HW504 joystick and eight PushBtn bodies are assembly instances;
 *   their global relocation belongs to the Backplate <-> JfD root-mate stage.
 * - JaD, JfD, screw geometry, INDEX, and MIDDLE geometry are not queried.
 * - Stage D relocates the 36 original opening side faces by the same transform.
 *   opMoveFace heals the old location and preserves the original Backplate /
 *   cap / opening relationship without a replacement pedestal or tool body.
 * - Current target is 15 mm below the validated Stage-D position.  Y is
 *   corrected to follow the lower shell curvature.  INDEX/MIDDLE internal
 *   collision work is explicitly deferred to the next design stage.
 */

export enum ThumbReseatStage
{
    annotation { "Name" : "B housing-first total translation (0,+12.25,-21)" }
    TRANSFORM,
    annotation { "Name" : "C probe original opening faces (no geometry write)" }
    PROBE_OPENINGS,
    annotation { "Name" : "D move original opening faces as one rigid set" }
    MOVE_OPENINGS
}

const NOMINAL_TRANSLATION = vector(0, 12.25, -21.0) * millimeter;

function originalInPlaceThumbModule() returns Query
{
    // Backplate final source body.
    const backplate = qCreatedBy(makeId("FR1RGAmsfokIVzQ_4"), EntityType.BODY);

    // Eight original button caps are created in three NEW-body operations:
    // 3 + 3 + 2 bodies.  Downstream cap detail features preserve these bodies.
    const caps = qUnion([
        qCreatedBy(makeId("FN60hLJrErylbKr_5"), EntityType.BODY),
        qCreatedBy(makeId("F5f2Bqv3P4yttCY_8"), EntityType.BODY),
        qCreatedBy(makeId("FhTqxuAvjIWGQgW_11"), EntityType.BODY)
    ]);

    return qBodyType(qUnion([backplate, caps]), BodyType.SOLID);
}

function originalThumbOpeningFaces() returns Query
{
    // The original Buttons sketch is removed from both shell halves in this
    // single feature.  It contains all eight button openings and the joystick
    // opening, so its created faces are the only permitted shell-side seed.
    return qCreatedBy(makeId("F9tZ4ezI7riogDz_2"), EntityType.FACE);
}

annotation { "Feature Type Name" : "OneGrip THUMB module reseat" }
export const oneGripThumbModuleReseat = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Stage" }
        definition.stage is ThumbReseatStage;
    }
    {
        if (definition.stage == ThumbReseatStage.TRANSFORM)
        {
            const module = originalInPlaceThumbModule();
            const members = evaluateQuery(context, module);
            if (size(members) != 9)
                throw regenError("THUMB RESEAT HOLD: expected Backplate + 8 caps = 9 solid bodies.");

            opTransform(context, id + "rigidTranslation", {
                        "bodies" : module,
                        "transform" : transform(NOMINAL_TRANSLATION)
                    });
            return;
        }

        const openingFaces = originalThumbOpeningFaces();
        const faceCount = size(evaluateQuery(context, openingFaces));
        if (faceCount == 0)
            throw regenError("THUMB RESEAT HOLD: original opening face query is empty.");

        if (definition.stage == ThumbReseatStage.PROBE_OPENINGS)
        {
            println("THUMB_RESEAT_ORIGINAL_OPENING_FACE_COUNT=" ~ faceCount);
            debug(context, openingFaces);
            return;
        }

        opMoveFace(context, id + "moveOriginalOpenings", {
                    "moveFaces" : openingFaces,
                    "transform" : transform(NOMINAL_TRANSLATION),
                    "reFillet" : false,
                    "mergeFaces" : true
                });
    });
