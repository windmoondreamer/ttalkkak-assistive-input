FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/* ============================================================================
   OneGrip Play — 하부 20도 경사 어댑터 (모듈형)

   이 Part Studio 에는 상체(JaD/JfD)가 존재하지 않는다. derive 도 하지 않는다.
   따라서 이 스크립트는 구조적으로 상체 형상을 수정할 수 없다.
   상체와의 정합은 lower_adapter/docs/00 의 실측 상수로만 보장한다.

   좌표계 = 그립 Part Studio 프레임 (상수를 그대로 쓰기 위해).
     ONEGRIP_CENTER_AXIS = (0, 27.269160) 을 지나는 +Z
     착좌면 Z = -67.878507,  법선 = +Z (실측 수직도 오차 0.000000 deg)

   경사는 웨지 밑면 하나에만 존재한다.
     UP_LOCAL = 월드 수직을 그립좌표로 표현 = (0, sin20, cos20)
     angle(UP_LOCAL, +Z) = 20.000000 deg   <-- GRIP_AXIS ⟂ TILT_SURFACE

   부품
     CRADLE  각도 무관. 착좌 평면 + 림 + 보스 포켓 + post + 케이블 보어
     WEDGE   각도 의존. 윗면 = 크래들 밑면(수평, 그립좌표), 밑면 = 월드 수평
     RING    각도 무관. 2분할 클램프. 플랜지 립을 유격 0.327mm 로 잡는다
   ============================================================================ */

export enum AdpStage
{
    annotation { "Name" : "A cradle blank" }
    CRADLE_BLANK,
    annotation { "Name" : "B cradle seat" }
    CRADLE_SEAT,
    annotation { "Name" : "C boss pocket" }
    CRADLE_POCKET,
    annotation { "Name" : "D post + cable bore" }
    CRADLE_POST,
    annotation { "Name" : "E cradle holes" }
    CRADLE_HOLES,
    annotation { "Name" : "F wedge blank + base cut" }
    WEDGE,
    annotation { "Name" : "G wedge holes" }
    WEDGE_HOLES,
    annotation { "Name" : "H clamp ring x2" }
    RING
}

// ---------- 상체 실측 인터페이스 (lower_adapter/docs/00). 변경 금지 ----------
const FLANGE_Z     = -67.878507 * millimeter;   // 착좌 평면
const BOSS_Z       = -73.878507 * millimeter;   // 보스 끝면 (착좌면 -6.000)
const SOCKET_TOP   = -52.878507 * millimeter;   // 직진 보어 막힌 끝
const AXIS_Y       =  27.269160 * millimeter;   // 중심축 Y
const POST_W       =  20.272 * millimeter;      // 원본 Pitch post 단면
const POST_D       =  25.272 * millimeter;

// ---------- 설계 파라미터 ----------
const RIM_CLR      =  0.30 * millimeter;
const RIM_WALL     =  4.00 * millimeter;
const RIM_TOP      = -64.028507 * millimeter;   // 림 상단 = 클램프 링 밑면
const CRADLE_BOT   = -78.078507 * millimeter;   // 크래들 밑면 (착좌면 -10.200)
const POCKET_FLOOR = -74.078507 * millimeter;   // 보스 포켓 바닥 (깊이 6.200)
const POCKET_W     =  31.672 * millimeter;      // 보스 31.072 + 2 x 0.30
const POCKET_D     =  36.272 * millimeter;      // 보스 35.672 + 2 x 0.30
const POST_TOP     = -53.878507 * millimeter;   // 보어 물림 20.000, 끝 여유 1.000
const POST_WALL    =  4.00 * millimeter;
const LIP_CAP      =  5.00 * millimeter;        // 링 립 물림(반경방향)
const RING_T       =  4.00 * millimeter;
const EAR_OD       =  9.00 * millimeter;
const SPLIT_Y      =  25.996 * millimeter;      // 링 분할선 (플랜지 도심)

const SCREW_CLR_D  =  3.40 * millimeter;        // M3 관통       PROVISIONAL
const SCREW_PILOT  =  2.50 * millimeter;        // M3 셀프탭 하공 PROVISIONAL
const SPOTFACE_D   =  6.50 * millimeter;
const TAP_CRADLE   =  8.00 * millimeter;
const TAP_EAR      =  6.00 * millimeter;
const TAP_GIMBAL   =  8.00 * millimeter;

// ---------- 경사 ----------
const UP_LOCAL = vector(0.0, 0.3420201433256687, 0.9396926207859084);  // 월드 수직
const BASE_PT  = vector(0.0, 15.674677141259831, -99.73408684464229) * millimeter;
const BIG      = 200 * millimeter;

// ---------- 볼트 / 이어 / 스포트페이스 ----------
const BOLTS_CW = [
    vector(26.0000, 8.0000) * millimeter,
    vector(-26.0000, 8.0000) * millimeter,
    vector(26.0000, 46.0000) * millimeter,
    vector(-26.0000, 46.0000) * millimeter
];
const SPOT_FACE_Z = [
    -91.940733 * millimeter,
    -91.940733 * millimeter,
    -105.771602 * millimeter,
    -105.771602 * millimeter
];
const GIMBAL_PTS = [
    vector(28.000000, 36.347915, -107.258530) * millimeter,
    vector(28.000000, -4.998561, -92.209644) * millimeter,
    vector(-28.000000, 36.347915, -107.258530) * millimeter,
    vector(-28.000000, -4.998561, -92.209644) * millimeter
];
const EAR_PTS = [
    vector(40.7415, 49.5181) * millimeter,
    vector(0.0000, 67.4275) * millimeter,
    vector(-40.7423, 49.5186) * millimeter,
    vector(-40.6130, 2.5481) * millimeter,
    vector(-0.0000, -15.0077) * millimeter,
    vector(40.6130, 2.5481) * millimeter
];

// 플랜지 윤곽 72점 — Z=-66.5 (prismatic 구간) 실측.
// lower_adapter/scripts/gen_adapter_constants.py 생성. 임의 수정 금지.
const FLANGE_PTS = [
    vector(38.6460, 25.9960) * millimeter, vector(38.6859, 29.3806) * millimeter, vector(38.6508, 32.8112) * millimeter,
    vector(38.4270, 36.2925) * millimeter, vector(38.0417, 39.8420) * millimeter, vector(37.4076, 43.4394) * millimeter,
    vector(36.4114, 47.0181) * millimeter, vector(34.9396, 50.4610) * millimeter, vector(32.8888, 53.5930) * millimeter,
    vector(30.2185, 56.2145) * millimeter, vector(27.0301, 58.2093) * millimeter, vector(23.5715, 59.6596) * millimeter,
    vector(20.0214, 60.6741) * millimeter, vector(16.4950, 61.3697) * millimeter, vector(13.0432, 61.8319) * millimeter,
    vector(9.6828, 62.1326) * millimeter, vector(6.3942, 62.2595) * millimeter, vector(3.1811, 62.3557) * millimeter,
    vector(0.0000, 62.4275) * millimeter, vector(-3.1793, 62.3356) * millimeter, vector(-6.3895, 62.2324) * millimeter,
    vector(-9.6793, 62.1196) * millimeter, vector(-13.0360, 61.8123) * millimeter, vector(-16.5006, 61.3816) * millimeter,
    vector(-20.0289, 60.6870) * millimeter, vector(-23.5686, 59.6555) * millimeter, vector(-27.0354, 58.2156) * millimeter,
    vector(-30.2152, 56.2112) * millimeter, vector(-32.8904, 53.5943) * millimeter, vector(-34.9382, 50.4600) * millimeter,
    vector(-36.4122, 47.0186) * millimeter, vector(-37.4146, 43.4427) * millimeter, vector(-38.0159, 39.8327) * millimeter,
    vector(-38.3902, 36.2826) * millimeter, vector(-38.6379, 32.8089) * millimeter, vector(-38.7046, 29.3822) * millimeter,
    vector(-38.6853, 25.9960) * millimeter, vector(-38.6728, 22.6126) * millimeter, vector(-38.5512, 19.1984) * millimeter,
    vector(-38.2689, 15.7419) * millimeter, vector(-37.8742, 12.2109) * millimeter, vector(-37.2406, 8.6304) * millimeter,
    vector(-36.2828, 5.0481) * millimeter, vector(-34.9197, 1.5449) * millimeter, vector(-32.9987, -1.6932) * millimeter,
    vector(-30.4468, -4.4508) * millimeter, vector(-27.2964, -6.5346) * millimeter, vector(-23.7739, -7.9567) * millimeter,
    vector(-20.1307, -8.8715) * millimeter, vector(-16.5118, -9.4137) * millimeter, vector(-13.0013, -9.7247) * millimeter,
    vector(-9.6132, -9.8809) * millimeter, vector(-6.3451, -9.9890) * millimeter, vector(-3.1494, -10.0022) * millimeter,
    vector(-0.0000, -10.0077) * millimeter, vector(3.1492, -9.9996) * millimeter, vector(6.3441, -9.9833) * millimeter,
    vector(9.6165, -9.8934) * millimeter, vector(13.0013, -9.7248) * millimeter, vector(16.5142, -9.4189) * millimeter,
    vector(20.1337, -8.8766) * millimeter, vector(23.7748, -7.9580) * millimeter, vector(27.2953, -6.5333) * millimeter,
    vector(30.4451, -4.4491) * millimeter, vector(32.9989, -1.6934) * millimeter, vector(34.9173, 1.5466) * millimeter,
    vector(36.2829, 5.0481) * millimeter, vector(37.2329, 8.6340) * millimeter, vector(37.8697, 12.2126) * millimeter,
    vector(38.2694, 15.7418) * millimeter, vector(38.5495, 19.1987) * millimeter, vector(38.6335, 22.6160) * millimeter
];

// ============================================================================
//  유틸
// ============================================================================

/** 폐다각형을 바깥(+) / 안(-) 으로 오프셋 한다. 정점 법선 평균 방식. */
function offsetLoop(pts is array, d is ValueWithUnits) returns array
{
    const n = size(pts);
    var c = pts[0] * 0;
    for (var p in pts)
    {
        c = c + p;
    }
    c = c / n;
    var out = [];
    for (var i = 0; i < n; i += 1)
    {
        const a = pts[(i + n - 1) % n];
        const b = pts[i];
        const e = pts[(i + 1) % n];
        const t1 = normalize(b - a);
        const t2 = normalize(e - b);
        var m = normalize(vector(t1[1], -t1[0]) + vector(t2[1], -t2[0]));
        if (dot(m, normalize(b - c)) < 0)
        {
            m = -m;
        }
        out = append(out, b + m * d);
    }
    return out;
}

/** XY 폐곡선을 z0 -> z1 로 압출한 새 body. */
function prism(context is Context, id is Id, pts is array,
               z0 is ValueWithUnits, z1 is ValueWithUnits)
{
    const sk = newSketchOnPlane(context, id + "sk",
            { "sketchPlane" : plane(vector(0 * millimeter, 0 * millimeter, z0), vector(0, 0, 1), vector(1, 0, 0)) });
    skPolyline(sk, "loop", { "points" : append(pts, pts[0]) });
    skSolve(sk);
    opExtrude(context, id + "ex", {
                "entities" : qSketchRegion(id + "sk", false),
                "direction" : vector(0, 0, 1),
                "endBound" : BoundingType.BLIND,
                "endDepth" : z1 - z0
            });
}

/** 중심 c=(x,y), 크기 wd=(폭,깊이) 의 사각 기둥.
    주의 1: FeatureScript 는 함수 인자 8개를 거부한다 (7개까지) -> 벡터로 묶었다.
    주의 2: 함수명 `box` 는 std 와 충돌해 컴파일이 조용히 실패한다 -> mkBox. */
function mkBox(context is Context, id is Id, c is Vector, wd is Vector,
             z0 is ValueWithUnits, z1 is ValueWithUnits)
{
    fCuboid(context, id, {
                "corner1" : vector(c[0] - wd[0] / 2, c[1] - wd[1] / 2, z0),
                "corner2" : vector(c[0] + wd[0] / 2, c[1] + wd[1] / 2, z1)
            });
}

/** +Z 축 원기둥. */
function cyl(context is Context, id is Id, p is Vector, dia is ValueWithUnits,
             z0 is ValueWithUnits, z1 is ValueWithUnits)
{
    fCylinder(context, id, {
                "topCenter" : vector(p[0], p[1], z1),
                "bottomCenter" : vector(p[0], p[1], z0),
                "radius" : dia / 2
            });
}

function cut(context is Context, id is Id, target is Query, toolId is Id)
{
    opBoolean(context, id, {
                "tools" : qBodyType(qCreatedBy(toolId, EntityType.BODY), BodyType.SOLID),
                "targets" : target,
                "operationType" : BooleanOperationType.SUBTRACTION
            });
}


// ============================================================================
//  피처
// ============================================================================

annotation { "Feature Type Name" : "OneGrip lower adapter" }
export const oneGripLowerAdapter = defineFeature(function(context is Context, id is Id,
        definition is map)
    precondition
    {
        annotation { "Name" : "Stage" }
        definition.stage is AdpStage;
        annotation { "Name" : "Cradle feature id" }
        definition.cradleId is string;
        annotation { "Name" : "Wedge feature id" }
        definition.wedgeId is string;
    }
    {
        const st = definition.stage;
        const rimIn = offsetLoop(FLANGE_PTS, RIM_CLR);
        const rimOut = offsetLoop(FLANGE_PTS, RIM_CLR + RIM_WALL);

        // ---------------- A. 크래들 blank (림 외곽 + 클램프 이어 6개) ----------------
        if (st == AdpStage.CRADLE_BLANK)
        {
            prism(context, id + "cradle", rimOut, CRADLE_BOT, RIM_TOP);
            var toolsA = [qBodyType(qCreatedBy(id + "cradle", EntityType.BODY), BodyType.SOLID)];
            for (var i = 0; i < size(EAR_PTS); i += 1)
            {
                cyl(context, id + ("ear" ~ i), EAR_PTS[i], EAR_OD, CRADLE_BOT, RIM_TOP);
                toolsA = append(toolsA, qBodyType(qCreatedBy(id + ("ear" ~ i), EntityType.BODY), BodyType.SOLID));
            }
            opBoolean(context, id + "u", {
                        "tools" : qUnion(toolsA),
                        "operationType" : BooleanOperationType.UNION
                    });
            return;
        }

        // ---------------- H. 클램프 링 2분할 (자기 완결) ----------------
        if (st == AdpStage.RING)
        {
            const lipIn = offsetLoop(FLANGE_PTS, -LIP_CAP);
            for (var h = 0; h < 2; h += 1)
            {
                var sgn = 1;
                if (h == 1)
                {
                    sgn = -1;
                }
                const rid = id + ("ring" ~ h);
                prism(context, rid, rimOut, RIM_TOP, RIM_TOP + RING_T);
                var toolsR = [qBodyType(qCreatedBy(rid, EntityType.BODY), BodyType.SOLID)];
                for (var i = 0; i < size(EAR_PTS); i += 1)
                {
                    const eid = id + ("r" ~ h ~ "e" ~ i);
                    cyl(context, eid, EAR_PTS[i], EAR_OD, RIM_TOP, RIM_TOP + RING_T);
                    toolsR = append(toolsR, qBodyType(qCreatedBy(eid, EntityType.BODY), BodyType.SOLID));
                }
                opBoolean(context, id + ("ru" ~ h), {
                            "tools" : qUnion(toolsR),
                            "operationType" : BooleanOperationType.UNION
                        });
                const ring = qBodyType(qCreatedBy(rid, EntityType.BODY), BodyType.SOLID);

                prism(context, id + ("rin" ~ h), lipIn,
                    RIM_TOP - 1 * millimeter, RIM_TOP + RING_T + 1 * millimeter);
                cut(context, id + ("rinc" ~ h), ring, id + ("rin" ~ h));

                mkBox(context, id + ("rhalf" ~ h),
                    vector(0 * millimeter, SPLIT_Y + sgn * BIG / 2), vector(2 * BIG, BIG),
                    RIM_TOP - 1 * millimeter, RIM_TOP + RING_T + 1 * millimeter);
                cut(context, id + ("rhalfc" ~ h), ring, id + ("rhalf" ~ h));

                for (var i = 0; i < size(EAR_PTS); i += 1)
                {
                    const hid = id + ("rh" ~ h ~ "_" ~ i);
                    cyl(context, hid, EAR_PTS[i], SCREW_CLR_D,
                        RIM_TOP - 1 * millimeter, RIM_TOP + RING_T + 1 * millimeter);
                    cut(context, hid + "c", ring, hid);
                }
            }
            return;
        }

        // ---------------- F. 웨지 blank + 월드 수평 기준면 절단 ----------------
        if (st == AdpStage.WEDGE)
        {
            prism(context, id + "wedge", rimOut, CRADLE_BOT - BIG, CRADLE_BOT);
            const sk = newSketchOnPlane(context, id + "bsk",
                    { "sketchPlane" : plane(BASE_PT, UP_LOCAL, vector(1, 0, 0)) });
            skRectangle(sk, "r", {
                        "firstCorner" : vector(-BIG, -BIG),
                        "secondCorner" : vector(BIG, BIG)
                    });
            skSolve(sk);
            opExtrude(context, id + "bex", {
                        "entities" : qSketchRegion(id + "bsk", false),
                        "direction" : -UP_LOCAL,
                        "endBound" : BoundingType.BLIND,
                        "endDepth" : BIG
                    });
            cut(context, id + "bcut",
                qBodyType(qCreatedBy(id + "wedge", EntityType.BODY), BodyType.SOLID),
                id + "bex");
            return;
        }

        // 이후 단계는 앞 단계가 만든 body 를 featureId 로 되찾는다.
        const cradle = qBodyType(qCreatedBy(makeId(definition.cradleId), EntityType.BODY),
                BodyType.SOLID);
        const wedge = qBodyType(qCreatedBy(makeId(definition.wedgeId), EntityType.BODY),
                BodyType.SOLID);

        // ---------------- B. 착좌면 ----------------
        if (st == AdpStage.CRADLE_SEAT)
        {
            prism(context, id + "seat", rimIn, FLANGE_Z, RIM_TOP + 5 * millimeter);
            cut(context, id + "seatcut", cradle, id + "seat");
        }

        // ---------------- C. 보스 포켓 ----------------
        else if (st == AdpStage.CRADLE_POCKET)
        {
            mkBox(context, id + "pk", vector(0 * millimeter, AXIS_Y), vector(POCKET_W, POCKET_D),
                POCKET_FLOOR, FLANGE_Z + 1 * millimeter);
            cut(context, id + "pkcut", cradle, id + "pk");
        }

        // ---------------- D. post + 케이블 보어 ----------------
        else if (st == AdpStage.CRADLE_POST)
        {
            mkBox(context, id + "post", vector(0 * millimeter, AXIS_Y), vector(POST_W, POST_D),
                POCKET_FLOOR, POST_TOP);
            opBoolean(context, id + "postu", {
                        "tools" : qUnion([cradle, qBodyType(qCreatedBy(id + "post", EntityType.BODY), BodyType.SOLID)]),
                        "operationType" : BooleanOperationType.UNION
                    });
            mkBox(context, id + "cab", vector(0 * millimeter, AXIS_Y),
                vector(POST_W - 2 * POST_WALL, POST_D - 2 * POST_WALL),
                CRADLE_BOT - 1 * millimeter, POST_TOP + 1 * millimeter);
            cut(context, id + "cabcut", cradle, id + "cab");
        }

        // ---------------- E. 크래들 나사 하공 ----------------
        else if (st == AdpStage.CRADLE_HOLES)
        {
            for (var i = 0; i < size(BOLTS_CW); i += 1)
            {
                const hid = id + ("cb" ~ i);
                cyl(context, hid, BOLTS_CW[i], SCREW_PILOT,
                    CRADLE_BOT - 1 * millimeter, CRADLE_BOT + TAP_CRADLE);
                cut(context, hid + "c", cradle, hid);
            }
            for (var i = 0; i < size(EAR_PTS); i += 1)
            {
                const hid = id + ("eb" ~ i);
                cyl(context, hid, EAR_PTS[i], SCREW_PILOT,
                    RIM_TOP - TAP_EAR, RIM_TOP + 1 * millimeter);
                cut(context, hid + "c", cradle, hid);
            }
        }

        // ---------------- G. 웨지 구멍 ----------------
        else if (st == AdpStage.WEDGE_HOLES)
        {
            for (var i = 0; i < size(BOLTS_CW); i += 1)
            {
                const hid = id + ("wb" ~ i);
                cyl(context, hid, BOLTS_CW[i], SCREW_CLR_D,
                    CRADLE_BOT - BIG, CRADLE_BOT + 1 * millimeter);
                cut(context, hid + "c", wedge, hid);
                const sid = id + ("ws" ~ i);
                cyl(context, sid, BOLTS_CW[i], SPOTFACE_D, CRADLE_BOT - BIG, SPOT_FACE_Z[i]);
                cut(context, sid + "c", wedge, sid);
            }
            mkBox(context, id + "wcab", vector(0 * millimeter, AXIS_Y),
                vector(POST_W - 2 * POST_WALL, POST_D - 2 * POST_WALL),
                CRADLE_BOT - BIG, CRADLE_BOT + 1 * millimeter);
            cut(context, id + "wcabc", wedge, id + "wcab");
            for (var i = 0; i < size(GIMBAL_PTS); i += 1)
            {
                const gid = id + ("g" ~ i);
                fCylinder(context, gid, {
                            "topCenter" : GIMBAL_PTS[i] + UP_LOCAL * TAP_GIMBAL,
                            "bottomCenter" : GIMBAL_PTS[i] - UP_LOCAL * (1 * millimeter),
                            "radius" : SCREW_PILOT / 2
                        });
                cut(context, gid + "c", wedge, gid);
            }
        }
    });
