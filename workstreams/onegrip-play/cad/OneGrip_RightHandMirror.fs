FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

annotation { "Feature Type Name" : "OneGrip RIGHT HAND mirror" }
export const oneGripRightHandMirror = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
    }
    {
        const allSolids = qBodyType(qEverything(EntityType.BODY), BodyType.SOLID);
        opTransform(context, id + "mirror", {
                    "bodies" : allSolids,
                    "transform" : mirrorAcross(YZ_PLANE)
                });
    });
