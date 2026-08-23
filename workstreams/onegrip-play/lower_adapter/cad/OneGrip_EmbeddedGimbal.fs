FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/* ============================================================================
   OneGrip Play — 매립형(embedded) 20도 짐벌

   구조:  OneGrip -> 소켓/post -> 소형 HUB -> 축2 베어링 -> RING -> 축1 베어링
          -> 20도 경사 HOUSING (고정)
   큰 웨지는 없다. 짐벌이 경사 하우징 "내부 체적" 을 쓴다.

   좌표계 = 그립 Part Studio 프레임.
     착좌 평면 Z = -67.878507,  중심축 (0, 27.269160), 법선 +Z
     경사(20도)는 하우징 밑면 절단 한 곳에만 존재한다 (V1 과 동일한 방식)

   파라미터는 Part Studio 변수로 뺀다 (트리 상단에 먼저 선언되어 있어야 한다):
     #pivot_depth    15 mm   (15 / 16 / 17 평가 가능)
     #gimbal_travel  10 deg  (10 / 12 / 15 평가 가능)
     #seat_recess     6 mm   착좌면을 경사 외피보다 이만큼 아래로
     #axis1_radius   29 mm   하우징 베어링 반경 (u). r 27~33 "선반" 중앙
     #axis2_radius   32 mm   링 베어링 반경 (v)
     #yoke_wall     2.5 mm   베어링 시트 살

   FeatureScript 주의 (docs/01 §11):
     - 함수 인자 7개 초과 금지,  함수명 `box` 금지
     - body 생성 id 는 feature id 하위여야 한다
     - qCreatedBy 는 스케치 wire 도 잡으므로 boolean 에는 qBodyType(SOLID) 로 감싼다
   ============================================================================ */

export enum EmbStage
{
    annotation { "Name" : "A hub" }
    HUB,
    annotation { "Name" : "B gimbal ring" }
    RING,
    annotation { "Name" : "C housing" }
    HOUSING,
    annotation { "Name" : "D bearing carriers (removable)" }
    CARRIER
}

// ---------- 상체 확정 인터페이스 (변경 금지) ----------
const FLANGE_Z   = -67.878507 * millimeter;
const AXIS_Y     =  27.269160 * millimeter;
const POST_TOP   = -53.878507 * millimeter;
const POCKET_W   =  31.672 * millimeter;    // 보스 31.072 + 2 x 0.30
const POCKET_D   =  36.272 * millimeter;
const POCKET_DEP =   6.200 * millimeter;
const POST_W     =  20.272 * millimeter;
const POST_D     =  25.272 * millimeter;
const POST_WALL  =   4.000 * millimeter;
const FLANGE_R   =  44.022 * millimeter;    // 중심축 기준 최대 반경

// ---------- 하드웨어 ----------
const BR_BORE    =  16.150 * millimeter;    // 625ZZ OD 16 + 끼움 0.15
const BR_W       =   5.000 * millimeter;
const SHAFT_CLR  =   5.400 * millimeter;    // M5 관통
const SHAFT_TAP  =   4.200 * millimeter;    // M5 셀프탭 하공
const M3_TAP     =   2.500 * millimeter;
const M3_CLR     =   3.400 * millimeter;

// ---------- 구조 ----------
const HUB_WALL   =   4.000 * millimeter;
const HUB_FLOOR  =   3.500 * millimeter;
const RING_BAND  =  12.000 * millimeter;    // 링 밴드 높이
const HOUSE_HALF =  58.000 * millimeter;    // 하우징 plan 반폭
const HOUSE_FLR  =   3.500 * millimeter;
const CLR        =   1.500 * millimeter;
const BIG        = 300 * millimeter;

// ---------- 경사 (V1 과 동일한 확정값) ----------
const UP_LOCAL   = vector(0.0, 0.3420201433256687, 0.9396926207859084);
const STACK_H    = 41.000 * millimeter;     // 기준면 -> 착좌 평면 (월드 수직)

// ============================================================================
//  유틸
// ============================================================================

/** 중심 c=(x,y), 크기 wd=(폭,깊이) 의 사각 기둥 (Z 방향). */
function mkBox(context is Context, id is Id, c is Vector, wd is Vector,
               z0 is ValueWithUnits, z1 is ValueWithUnits)
{
    fCuboid(context, id, {
                "corner1" : vector(c[0] - wd[0] / 2, c[1] - wd[1] / 2, z0),
                "corner2" : vector(c[0] + wd[0] / 2, c[1] + wd[1] / 2, z1)
            });
}

/** 임의 두 점 사이 원기둥. */
function cylAB(context is Context, id is Id, pa is Vector, pb is Vector, dia is ValueWithUnits)
{
    fCylinder(context, id, { "topCenter" : pb, "bottomCenter" : pa, "radius" : dia / 2 });
}

/** +Z 축 원기둥 (중심축 위). */
function cylZ(context is Context, id is Id, dia is ValueWithUnits,
              z0 is ValueWithUnits, z1 is ValueWithUnits)
{
    fCylinder(context, id, {
                "topCenter" : vector(0 * millimeter, AXIS_Y, z1),
                "bottomCenter" : vector(0 * millimeter, AXIS_Y, z0),
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

function join(context is Context, id is Id, a is Query, toolId is Id)
{
    opBoolean(context, id, {
                "tools" : qUnion([a, qBodyType(qCreatedBy(toolId, EntityType.BODY), BodyType.SOLID)]),
                "operationType" : BooleanOperationType.UNION
            });
}

// ============================================================================
//  피처
// ============================================================================

annotation { "Feature Type Name" : "OneGrip embedded gimbal" }
export const oneGripEmbeddedGimbal = defineFeature(function(context is Context, id is Id,
        definition is map)
    precondition
    {
        annotation { "Name" : "Stage" }
        definition.stage is EmbStage;
        annotation { "Name" : "Housing feature id" }
        definition.housingId is string;
    }
    {
        const st = definition.stage;
        const p = getVariable(context, "pivot_depth");
        const th = getVariable(context, "gimbal_travel");
        const recess = getVariable(context, "seat_recess");
        const a1 = getVariable(context, "axis1_radius");
        const a2 = getVariable(context, "axis2_radius");
        const yw = getVariable(context, "yoke_wall");

        const PIVOT_Z = FLANGE_Z - p;
        const hBoss = BR_BORE / 2 + yw;                    // 보스 상하 반경
        const bossOD = 2 * hBoss;
        const sinT = sin(th);
        const cosT = cos(th);

        // 파생 치수
        const hubHalfU = POCKET_W / 2 + HUB_WALL;
        const hubHalfV = POCKET_D / 2 + HUB_WALL;
        const hubBot = FLANGE_Z - POCKET_DEP - HUB_FLOOR;
        const armEndV = a2 - BR_W / 2 - 0.3 * millimeter;   // 축2 베어링 안쪽면
        const ringOutU = a1 - BR_W / 2 - 0.5 * millimeter;  // 링 u 외곽 = 베어링 안쪽면
        const ringOutV = a2 + BR_W / 2 + yw;
        // 링 내경(u)은 "허브가 축2로 기울었을 때 아래쪽 바깥 모서리가 나가는 위치" 로 잡는다.
        // 정지 기준(hubHalfU + CLR)으로 잡으면 +-10deg 에서 허브 모서리가 링 탭 보스를 친다.
        const ringInU = hubHalfU * cosT + (p - (POCKET_DEP + HUB_FLOOR)) * sinT + CLR;
        const ringInV = armEndV;
        const wellR = FLANGE_R * cosT + (p + 8 * millimeter) * sinT + CLR;
        const wellD = FLANGE_R * sinT + 3 * millimeter;
        const ringSweep = (a2 + 5 * millimeter + hBoss) * sinT;
        const cavBot = PIVOT_Z - hBoss - ringSweep - CLR;
        const surfZ = FLANGE_Z + recess;

        // ---------------- A. HUB ----------------
        if (st == EmbStage.HUB)
        {
            mkBox(context, id + "hub", vector(0 * millimeter, AXIS_Y),
                vector(2 * hubHalfU, 2 * hubHalfV), hubBot, FLANGE_Z);
            const hub = qBodyType(qCreatedBy(id + "hub", EntityType.BODY), BodyType.SOLID);

            // 팔 본체는 베어링 앞 3 mm 에서 끝내고, 그 앞은 지름 8 보스만 남긴다.
            // (14x14 각 팔이 링 숄더 구멍 D13.65 를 통과하지 못해 중립에서 간섭했다)
            // 팔 상단은 반드시 허브 바닥까지 올려 붙인다.
            // (p 가 커지면 PIVOT_Z+7 이 허브 바닥보다 아래로 내려가 body 가 분리된다)
            mkBox(context, id + "arm", vector(0 * millimeter, AXIS_Y),
                vector(14 * millimeter, 2 * (armEndV - 3 * millimeter)),
                PIVOT_Z - 7 * millimeter, hubBot + 0.5 * millimeter);
            join(context, id + "armj", hub, id + "arm");
            for (var s = 0; s < 2; s += 1)
            {
                var sg = 1;
                if (s == 1)
                {
                    sg = -1;
                }
                const nid = id + ("nose" ~ s);
                cylAB(context, nid,
                    vector(0 * millimeter, AXIS_Y + sg * (armEndV - 4 * millimeter), PIVOT_Z),
                    vector(0 * millimeter, AXIS_Y + sg * (a2 - BR_W / 2), PIVOT_Z),
                    8 * millimeter);
                join(context, nid + "j", hub, nid);
            }

            mkBox(context, id + "pk", vector(0 * millimeter, AXIS_Y),
                vector(POCKET_W, POCKET_D), FLANGE_Z - POCKET_DEP, FLANGE_Z + 1 * millimeter);
            cut(context, id + "pkc", hub, id + "pk");

            mkBox(context, id + "post", vector(0 * millimeter, AXIS_Y),
                vector(POST_W, POST_D), FLANGE_Z - POCKET_DEP, POST_TOP);
            join(context, id + "postj", hub, id + "post");

            mkBox(context, id + "cab", vector(0 * millimeter, AXIS_Y),
                vector(POST_W - 2 * POST_WALL, POST_D - 2 * POST_WALL),
                hubBot - 1 * millimeter, POST_TOP + 1 * millimeter);
            cut(context, id + "cabc", hub, id + "cab");

            for (var s = 0; s < 2; s += 1)
            {
                var sg = 1;
                if (s == 1)
                {
                    sg = -1;
                }
                const tid = id + ("tap" ~ s);
                cylAB(context, tid,
                    vector(0 * millimeter, AXIS_Y + sg * (armEndV - 11 * millimeter), PIVOT_Z),
                    vector(0 * millimeter, AXIS_Y + sg * (armEndV + 1 * millimeter), PIVOT_Z),
                    SHAFT_TAP);
                cut(context, tid + "c", hub, tid);

                const sid = id + ("set" ~ s);
                cylAB(context, sid,
                    vector(sg * (hubHalfU + 1 * millimeter), AXIS_Y, FLANGE_Z - POCKET_DEP / 2),
                    vector(sg * (POCKET_W / 2 - 0.5 * millimeter), AXIS_Y, FLANGE_Z - POCKET_DEP / 2),
                    M3_TAP);
                cut(context, sid + "c", hub, sid);
            }
            return;
        }

        // ---------------- B. RING ----------------
        if (st == EmbStage.RING)
        {
            mkBox(context, id + "ring", vector(0 * millimeter, AXIS_Y),
                vector(2 * ringOutU, 2 * ringOutV),
                PIVOT_Z - RING_BAND / 2, PIVOT_Z + RING_BAND / 2);
            const ring = qBodyType(qCreatedBy(id + "ring", EntityType.BODY), BodyType.SOLID);
            mkBox(context, id + "rin", vector(0 * millimeter, AXIS_Y),
                vector(2 * ringInU, 2 * ringInV),
                PIVOT_Z - RING_BAND, PIVOT_Z + RING_BAND);
            cut(context, id + "rinc", ring, id + "rin");

            for (var s = 0; s < 2; s += 1)
            {
                var sg = 1;
                if (s == 1)
                {
                    sg = -1;
                }
                // 축2 베어링 보스 (v 방향)
                const bid = id + ("b2" ~ s);
                cylAB(context, bid,
                    vector(0 * millimeter, AXIS_Y + sg * (a2 - BR_W / 2 - 2 * millimeter), PIVOT_Z),
                    vector(0 * millimeter, AXIS_Y + sg * ringOutV, PIVOT_Z), bossOD);
                join(context, bid + "j", ring, bid);
                // 축1 탭 보스 (u 방향)
                const cid = id + ("b1" ~ s);
                cylAB(context, cid,
                    vector(sg * ringInU, AXIS_Y, PIVOT_Z),
                    vector(sg * ringOutU, AXIS_Y, PIVOT_Z), 12 * millimeter);
                join(context, cid + "j", ring, cid);
            }
            for (var s = 0; s < 2; s += 1)
            {
                var sg = 1;
                if (s == 1)
                {
                    sg = -1;
                }
                const hid = id + ("bore" ~ s);
                cylAB(context, hid,
                    vector(0 * millimeter, AXIS_Y + sg * (a2 - BR_W / 2), PIVOT_Z),
                    vector(0 * millimeter, AXIS_Y + sg * (ringOutV + 1 * millimeter), PIVOT_Z),
                    BR_BORE);
                cut(context, hid + "c", ring, hid);
                const sid = id + ("shd" ~ s);
                cylAB(context, sid,
                    vector(0 * millimeter, AXIS_Y + sg * (a2 - BR_W / 2 - 3 * millimeter), PIVOT_Z),
                    vector(0 * millimeter, AXIS_Y + sg * (a2 - BR_W / 2), PIVOT_Z),
                    BR_BORE - 2.5 * millimeter);
                cut(context, sid + "c", ring, sid);
                const tid = id + ("t1" ~ s);
                cylAB(context, tid,
                    vector(sg * (ringOutU - 10 * millimeter), AXIS_Y, PIVOT_Z),
                    vector(sg * (ringOutU + 1 * millimeter), AXIS_Y, PIVOT_Z), SHAFT_TAP);
                cut(context, tid + "c", ring, tid);
            }
            return;
        }

        // ---------------- C. HOUSING ----------------
        if (st == EmbStage.HOUSING)
        {
            mkBox(context, id + "house", vector(0 * millimeter, AXIS_Y),
                vector(2 * HOUSE_HALF, 2 * HOUSE_HALF), FLANGE_Z - BIG / 2, surfZ);
            const hs = qBodyType(qCreatedBy(id + "house", EntityType.BODY), BodyType.SOLID);

            // 월드 수평 밑면
            const bp = vector(0 * millimeter, AXIS_Y, FLANGE_Z) - UP_LOCAL * STACK_H;
            const sk = newSketchOnPlane(context, id + "bsk",
                    { "sketchPlane" : plane(bp, UP_LOCAL, vector(1, 0, 0)) });
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
            cut(context, id + "bcut", hs, id + "bex");

            // well (그립 스윕 공간)
            cylZ(context, id + "well", 2 * wellR, FLANGE_Z - wellD, surfZ + 1 * millimeter);
            cut(context, id + "wellc", hs, id + "well");
            // 링 공동
            cylZ(context, id + "cav", 2 * (ringOutV + ringSweep + CLR),
                cavBot, FLANGE_Z - wellD + 0.01 * millimeter);
            cut(context, id + "cavc", hs, id + "cav");

            // 축1 베어링은 "분리형 캐리어" 로 뺀다.
            // 기둥을 통짜로 만들면 링을 well 로 내려 넣을 수 없다 (u 22~36 에서 간섭).
            // 하우징에는 캐리어 착좌 탭 구멍 4개와 측면 조립 개구부만 만든다.
            for (var s = 0; s < 2; s += 1)
            {
                var sg = 1;
                if (s == 1)
                {
                    sg = -1;
                }
                // 측면 조립 개구부 (캐리어를 옆으로 밀어 넣는다)
                const oid = id + ("op" ~ s);
                mkBox(context, oid, vector(sg * (a1 + 18 * millimeter), AXIS_Y),
                    vector(40 * millimeter, 24 * millimeter),
                    cavBot, PIVOT_Z + hBoss + 1 * millimeter);
                cut(context, oid + "c", hs, oid);
                // 캐리어 고정 탭 (바닥에서 위로)
                for (var k = 0; k < 2; k += 1)
                {
                    var kg = 1;
                    if (k == 1)
                    {
                        kg = -1;
                    }
                    const tid = id + ("ct" ~ s ~ k);
                    cylAB(context, tid,
                        vector(sg * (a1 + 2.25 * millimeter), AXIS_Y + kg * 7 * millimeter,
                            cavBot - 9 * millimeter),
                        vector(sg * (a1 + 2.25 * millimeter), AXIS_Y + kg * 7 * millimeter,
                            cavBot + 1 * millimeter), M3_TAP);
                    cut(context, tid + "c", hs, tid);
                }
            }
            return;
        }

        // ---------------- D. 분리형 베어링 캐리어 2개 ----------------
        if (st == EmbStage.CARRIER)
        {
            for (var s = 0; s < 2; s += 1)
            {
                var sg = 1;
                if (s == 1)
                {
                    sg = -1;
                }
                // 안쪽면 = 링 u 팔 바깥 + 0.5. (a1-7 로 두면 링과 중립에서 겹친다)
                const carIn = ringOutU + 0.5 * millimeter;
                const carOut = a1 + 7 * millimeter;
                const cid = id + ("car" ~ s);
                mkBox(context, cid, vector(sg * (carIn + carOut) / 2, AXIS_Y),
                    vector(carOut - carIn, 22 * millimeter), cavBot, PIVOT_Z + hBoss);
                const car = qBodyType(qCreatedBy(cid, EntityType.BODY), BodyType.SOLID);
                // 베어링 시트 (바깥에서 압입, 안쪽 숄더)
                const bid = id + ("cb" ~ s);
                cylAB(context, bid,
                    vector(sg * (a1 - BR_W / 2), AXIS_Y, PIVOT_Z),
                    vector(sg * (a1 + 8 * millimeter), AXIS_Y, PIVOT_Z), BR_BORE);
                cut(context, bid + "c", car, bid);
                const sid = id + ("cs" ~ s);
                cylAB(context, sid,
                    vector(sg * (a1 - BR_W / 2 - 3 * millimeter), AXIS_Y, PIVOT_Z),
                    vector(sg * (a1 - BR_W / 2), AXIS_Y, PIVOT_Z), BR_BORE - 2.5 * millimeter);
                cut(context, sid + "c", car, sid);
                // 하우징 바닥 고정 나사 관통공 2개
                for (var k = 0; k < 2; k += 1)
                {
                    var kg = 1;
                    if (k == 1)
                    {
                        kg = -1;
                    }
                    const hid = id + ("ch" ~ s ~ k);
                    cylAB(context, hid,
                        vector(sg * (carIn + carOut) / 2, AXIS_Y + kg * 7 * millimeter, cavBot - 1 * millimeter),
                        vector(sg * (carIn + carOut) / 2, AXIS_Y + kg * 7 * millimeter,
                            PIVOT_Z + hBoss + 1 * millimeter), M3_CLR);
                    cut(context, hid + "c", car, hid);
                }
            }
        }
    });
