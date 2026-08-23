FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/* ============================================================================
   OneGrip Play — OPTION C : 스톡 짐벌 카트리지 마운트

   구조:
       OneGrip (무수정)
          |  기존 소켓 / Pitch post — 무수정
       스톡 짐벌 (STOCK_GIMBAL_INTERNALS = IMMUTABLE)
          |  기존 M3 2개 (C1/C2) + 캐리어 포켓
       CARRIER_PLATE      <- 아래에서 탈착
          |  스피곳 끼움 + 립 + M3 6개
       DECK_HOUSING (20도 경사 덱 + 둘레 벽 + 스커트)

   스톡 짐벌은 덱을 **관통**해서 주로 아래로 뻗는다. 덱 개구부는 비구조다.

   좌표계 = 그립 Part Studio 프레임.
     착좌 평면 Z = -67.878507, 중심축 (0, 27.269160), 법선 +Z
     GRIP_AXIS ⟂ DECK 는 덱 법선을 그립 +Z 로 두어 **정의상** 성립시킨다.
     20도는 스커트 밑면(지면 평면) 절단 한 곳에만 존재한다. (V1 과 동일한 방식)

   Part Studio 변수 (트리 상단에 먼저 선언되어 있어야 한다):
     #cartridge_insert_depth  6 mm    덱 상면을 착좌면보다 이만큼 위로
     #deck_thickness          6 mm
     #wall_thickness          9 mm
     #carrier_fit           0.2 mm    캐리어 외곽 <-> 하우징 내경 (편측)
     #pocket_clearance      0.3 mm    포켓 <-> 스톡 Base (편측)
     #usb_clearance           6 mm    카트리지 최저점 <-> 지면

   FeatureScript 주의 (lower_adapter/docs/01 §11):
     - 함수 인자 7개 초과 금지,  함수명 `box` 금지
     - body 생성 id 는 feature id 하위여야 한다 (makeId("문자열") 금지)
     - qCreatedBy 는 스케치 wire 도 잡으므로 boolean 에는 qBodyType(SOLID) 로 감싼다
   ============================================================================ */

export enum CartStage
{
    annotation { "Name" : "A carrier plate" }
    CARRIER,
    annotation { "Name" : "B deck housing" }
    HOUSING
}

// ---------- 상체 확정 인터페이스 (변경 금지) ----------
const SEAT_Z     = -67.878507 * millimeter;

// ---------- 스톡 짐벌 실측 (중립 복원, 변경 금지) ----------
const BASE_BOT   = -149.956514 * millimeter;   // 스톡 Base 밑면
const BASE_TOP   = -131.456500 * millimeter;   // 스톡 Base 윗면
const BODY_W     =  100.000 * millimeter;      // Base 본체 (X)
const BODY_D     =  100.000 * millimeter;      // Base 본체 (Y)
const CX         =    0.354442 * millimeter;   // Base 본체 중심
const CY         =   26.689150 * millimeter;
const TAIL_W0    =   28.000 * millimeter;      // 전장 꼬리 폭
const TAIL_CX    =    0.354400 * millimeter;
const JUNC_Y     =  -23.310850 * millimeter;   // 본체 <-> 꼬리 경계
const TAIL_END   =  -66.310800 * millimeter;

// C1 / C2 — 기존 M3 체결점 (Roll_holder / Roll_holder_2 의 ⌀3.0 블라인드)
const C_X        =    0.354430 * millimeter;
const C1_Y       =   60.325240 * millimeter;
const C2_Y       =   -6.946830 * millimeter;
const C_SLOT_W   =    3.400 * millimeter;      // Base 슬롯과 동일
const C_SLOT_L   =   11.400 * millimeter;

// 덱 개구 (9자세 x 덱 두께 구간 합집합 + FDM 1.5/side)
const OP_CX      =   -0.048853 * millimeter;
const OP_CY      =   26.228023 * millimeter;
const OP_W       =   90.789042 * millimeter;
const OP_H       =   87.485128 * millimeter;
const OP_R       =    8.000 * millimeter;

// ---------- 경사 (V1 / EMBEDDED_GIMBAL_V1 과 동일한 확정값) ----------
const UP_LOCAL   = vector(0.0, 0.3420201433256687, 0.9396926207859084);
const GROUND_Z   = -192.035493 * millimeter;   // 지면 평면이 (CX,CY) 에서 갖는 Z

// ---------- 하드웨어 ----------
const M3_CLR     =    3.400 * millimeter;
const M3_CB      =    6.600 * millimeter;      // 소켓 헤드 ⌀5.5 + 여유
const CB_D       =    3.500 * millimeter;      // 카운터보어 깊이
const INSERT_D   =    4.000 * millimeter;      // M3 열간 인서트
const INSERT_L   =    8.000 * millimeter;

// ---------- 구조 ----------
const POCK_D     =    3.000 * millimeter;      // 포켓 깊이 (Base 측면 포착량)
const CAR_FLR    =    6.000 * millimeter;      // 포켓 바닥 아래 살
const LIP_W      =    8.000 * millimeter;      // 립 반경방향 폭
const LIP_T      =   10.000 * millimeter;      // 립 두께(Z) — 인서트 수용
const LIP_CLR    =    1.000 * millimeter;      // 립 내경 <-> Base 옆면 (편측)
const WIN_MARGIN =   20.000 * millimeter;      // 창 옆 남길 살 (덱~립 구간)
const SKIRT_MRG  =   24.000 * millimeter;      // 스커트 코너 다리 폭
const SKIRT_GAP  =    4.000 * millimeter;      // 캐리어 밑면 아래 남길 살
const WIN_TOP    =   12.000 * millimeter;      // 덱 밑면에서 창까지
const WIN_BOT    =    7.000 * millimeter;      // 립 위에서 창까지
const BIG        =  400 * millimeter;

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

/** 모서리 반경 r 의 둥근 사각 기둥. box 2개 + 코너 원기둥 4개의 합집합. */
function mkRound(context is Context, id is Id, c is Vector, wd is Vector,
                 r is ValueWithUnits, z0 is ValueWithUnits, z1 is ValueWithUnits)
{
    mkBox(context, id + "a", c, vector(wd[0] - 2 * r, wd[1]), z0, z1);
    const acc = qBodyType(qCreatedBy(id + "a", EntityType.BODY), BodyType.SOLID);
    mkBox(context, id + "b", c, vector(wd[0], wd[1] - 2 * r), z0, z1);
    opBoolean(context, id + "bj", {
                "tools" : qUnion([acc, qBodyType(qCreatedBy(id + "b", EntityType.BODY), BodyType.SOLID)]),
                "operationType" : BooleanOperationType.UNION
            });
    for (var s = 0; s < 4; s += 1)
    {
        var sx = 1;
        var sy = 1;
        if (s == 1 || s == 2)
        {
            sx = -1;
        }
        if (s >= 2)
        {
            sy = -1;
        }
        const cid = id + ("c" ~ s);
        fCylinder(context, cid, {
                    "topCenter" : vector(c[0] + sx * (wd[0] / 2 - r), c[1] + sy * (wd[1] / 2 - r), z1),
                    "bottomCenter" : vector(c[0] + sx * (wd[0] / 2 - r), c[1] + sy * (wd[1] / 2 - r), z0),
                    "radius" : r
                });
        opBoolean(context, cid + "j", {
                    "tools" : qUnion([acc, qBodyType(qCreatedBy(cid, EntityType.BODY), BodyType.SOLID)]),
                    "operationType" : BooleanOperationType.UNION
                });
    }
}

/** Y 방향 슬롯 (폭 w, 전체 길이 l) 기둥. */
function mkSlot(context is Context, id is Id, c is Vector, w is ValueWithUnits,
                l is ValueWithUnits, z0 is ValueWithUnits, z1 is ValueWithUnits)
{
    mkBox(context, id + "a", c, vector(w, l - w), z0, z1);
    const acc = qBodyType(qCreatedBy(id + "a", EntityType.BODY), BodyType.SOLID);
    for (var s = 0; s < 2; s += 1)
    {
        var sy = 1;
        if (s == 1)
        {
            sy = -1;
        }
        const cid = id + ("e" ~ s);
        fCylinder(context, cid, {
                    "topCenter" : vector(c[0], c[1] + sy * (l - w) / 2, z1),
                    "bottomCenter" : vector(c[0], c[1] + sy * (l - w) / 2, z0),
                    "radius" : w / 2
                });
        opBoolean(context, cid + "j", {
                    "tools" : qUnion([acc, qBodyType(qCreatedBy(cid, EntityType.BODY), BodyType.SOLID)]),
                    "operationType" : BooleanOperationType.UNION
                });
    }
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

/** 캐리어 <-> 하우징 나사 배치 (중심 (CX,CY) 기준 오프셋, mm).

    립 밴드는 반경 51~59 이고 코너는 R6 라운드다. 코너에 놓으면 인서트 ⌀4 가
    라운드를 물어 살이 0.34 mm 만 남는다 -> **전부 평면부에 놓는다.**
    -Y 립은 전장 꼬리 슬롯(X ±15.3)이 지나가므로 그 구간은 비운다.        */
const SCREWS = [
        vector( 55.0, 45.0), vector(-55.0, 45.0),
        vector( 55.0,  0.0), vector(-55.0,  0.0),
        vector( 55.0, -45.0), vector(-55.0, -45.0),
        vector( 30.0, 55.0), vector(-30.0, 55.0)
    ];

function screwXY(i is number) returns Vector
{
    return vector(CX + SCREWS[i][0] * millimeter, CY + SCREWS[i][1] * millimeter);
}

// ============================================================================
//  피처
// ============================================================================

annotation { "Feature Type Name" : "OneGrip stock cartridge mount" }
export const oneGripCartridge = defineFeature(function(context is Context, id is Id,
        definition is map)
    precondition
    {
        annotation { "Name" : "Stage" }
        definition.stage is CartStage;
    }
    {
        const st = definition.stage;
        const insertDepth = getVariable(context, "cartridge_insert_depth");
        const deckT = getVariable(context, "deck_thickness");
        const wallT = getVariable(context, "wall_thickness");
        const fit = getVariable(context, "carrier_fit");
        const pClr = getVariable(context, "pocket_clearance");

        // 파생 치수
        const DECK_Z = SEAT_Z + insertDepth;          // 덱 상면 (= 경사 외피)
        const DECK_B = DECK_Z - deckT;                // 덱 밑면
        const CAR_TOP = BASE_BOT + POCK_D;            // 캐리어 상면 = 립 착좌면
        const CAR_BOT = BASE_BOT - CAR_FLR;
        const POCK_X = BODY_W + 2 * pClr;
        const POCK_Y = BODY_D + 2 * pClr;
        const TAIL_W = TAIL_W0 + 2 * pClr;
        const LIP_IN = BODY_W + 2 * LIP_CLR;          // 102 — Base 가 통과한다
        const HOUSE_IN = LIP_IN + 2 * LIP_W;          // 118
        const CAR_OUT = HOUSE_IN - 2 * fit;           // 117.6
        const HOUSE_OUT = HOUSE_IN + 2 * wallT;       // 136
        const LIP_TOP = CAR_TOP + LIP_T;

        // ---------------- A. CARRIER_PLATE ----------------
        if (st == CartStage.CARRIER)
        {
            mkRound(context, id + "plate", vector(CX, CY), vector(CAR_OUT, CAR_OUT),
                6 * millimeter, CAR_BOT, CAR_TOP);
            const car = qBodyType(qCreatedBy(id + "plate" + "a", EntityType.BODY), BodyType.SOLID);

            // 1) Base 본체 포켓 (위치 결정 + 전단 + 회전 구속)
            mkBox(context, id + "pock", vector(CX, CY), vector(POCK_X, POCK_Y),
                BASE_BOT, CAR_TOP + 1 * millimeter);
            cut(context, id + "pockc", car, id + "pock");

            // 2) 전장 꼬리 슬롯 — -Y 로 완전 관통.
            //    스톡 CAD 는 전장 포켓을 모델링하지 않았고 (Arduino 가 Base 솔리드와
            //    81% 겹쳐 있다), USB 는 Base 밑면 아래 2.850 mm 로 튀어나온다.
            //    -> 꼬리 전체를 보수적으로 비운다. 이 슬롯이 180도 오조립도 막는다.
            mkBox(context, id + "tail", vector(TAIL_CX, (JUNC_Y - BIG) / 2),
                vector(TAIL_W, BIG), BASE_BOT, CAR_TOP + 1 * millimeter);
            cut(context, id + "tailc", car, id + "tail");

            // 3) 꼬리 아래 살도 제거 — 전장/USB 는 Y <= -45.851 에서 밑면 아래로 나온다.
            //    캐리어는 Y >= JUNC_Y 만 남긴다 (플랜지 -Y 끝이 이미 Y = CY - CAR_OUT/2).
            mkBox(context, id + "tailu", vector(TAIL_CX, (JUNC_Y - BIG) / 2),
                vector(TAIL_W, BIG), CAR_BOT - 1 * millimeter, BASE_BOT + 0.001 * millimeter);
            cut(context, id + "tailuc", car, id + "tailu");

            // 4) C1 / C2 — Base 슬롯과 동일한 Y 슬롯 (Base 가 Roll_holder 에 대해
            //    Y 로 ±float 하므로 원형 구멍은 포켓과 싸운다)
            for (var s = 0; s < 2; s += 1)
            {
                var cy = C1_Y;
                if (s == 1)
                {
                    cy = C2_Y;
                }
                const sid = id + ("cs" ~ s);
                mkSlot(context, sid, vector(C_X, cy), M3_CLR, C_SLOT_L,
                    CAR_BOT - 1 * millimeter, BASE_BOT + 1 * millimeter);
                cut(context, sid + "c", car, sid + "a");
                const bid = id + ("cb" ~ s);
                mkSlot(context, bid, vector(C_X, cy), M3_CB, C_SLOT_L + M3_CB - M3_CLR,
                    CAR_BOT - 1 * millimeter, CAR_BOT + CB_D);
                cut(context, bid + "c", car, bid + "a");
            }

            // 5) 캐리어 <-> 하우징 나사 6개 (아래에서 위로, 하우징 립의 인서트로)
            for (var s = 0; s < size(SCREWS); s += 1)
            {
                const p = screwXY(s);
                const hid = id + ("hs" ~ s);
                fCylinder(context, hid, {
                            "topCenter" : vector(p[0], p[1], CAR_TOP + 1 * millimeter),
                            "bottomCenter" : vector(p[0], p[1], CAR_BOT - 1 * millimeter),
                            "radius" : M3_CLR / 2
                        });
                cut(context, hid + "c", car, hid);
                const gid = id + ("hb" ~ s);
                fCylinder(context, gid, {
                            "topCenter" : vector(p[0], p[1], CAR_BOT + CB_D),
                            "bottomCenter" : vector(p[0], p[1], CAR_BOT - 1 * millimeter),
                            "radius" : M3_CB / 2
                        });
                cut(context, gid + "c", car, gid);
            }
            return;
        }

        // ---------------- B. DECK_HOUSING ----------------
        if (st == CartStage.HOUSING)
        {
            // 1) 외곽 셸: 덱 상면 -> 지면 아래까지
            mkRound(context, id + "sh", vector(CX, CY), vector(HOUSE_OUT, HOUSE_OUT),
                10 * millimeter, GROUND_Z - 40 * millimeter, DECK_Z);
            const hs = qBodyType(qCreatedBy(id + "sh" + "a", EntityType.BODY), BodyType.SOLID);

            // 2) 내부 프리즘 제거 -> 덱 + 둘레 벽. 밑면은 열려 있다.
            mkRound(context, id + "in", vector(CX, CY), vector(HOUSE_IN, HOUSE_IN),
                6 * millimeter, GROUND_Z - 50 * millimeter, DECK_B);
            cut(context, id + "inc", hs, id + "in" + "a");

            // 3) 덱 모션 개구부 (비구조). 9자세 x 덱 두께 구간 합집합 + FDM 1.5/side
            mkRound(context, id + "op", vector(OP_CX, OP_CY), vector(OP_W, OP_H),
                OP_R, DECK_B - 1 * millimeter, DECK_Z + 1 * millimeter);
            cut(context, id + "opc", hs, id + "op" + "a");

            // 4) 캐리어 착좌 립 (안쪽으로 LIP_W). 인서트를 담을 두께를 준다.
            mkRound(context, id + "lp", vector(CX, CY), vector(HOUSE_IN, HOUSE_IN),
                6 * millimeter, CAR_TOP, LIP_TOP);
            mkRound(context, id + "lpi", vector(CX, CY), vector(LIP_IN, LIP_IN),
                4 * millimeter, CAR_TOP - 1 * millimeter, LIP_TOP + 1 * millimeter);
            cut(context, id + "lpc", qBodyType(qCreatedBy(id + "lp" + "a", EntityType.BODY),
                    BodyType.SOLID), id + "lpi" + "a");
            join(context, id + "lpj", hs, id + "lp" + "a");

            // 5) 전장 꼬리 관통 슬롯 (-Y 벽 + 립). 꼬리는 하우징 밖으로 나온다.
            //    아래로도 **지면까지** 열어야 한다. BASE_BOT 에서 끊으면 카트리지를
            //    아래로 뽑을 때 꼬리가 t=2mm 만에 -Y 벽 살에 박힌다 (실측 확인).
            mkBox(context, id + "tsl", vector(TAIL_CX, (JUNC_Y - BIG) / 2),
                vector(TAIL_W + 2 * millimeter, BIG),
                GROUND_Z - 50 * millimeter, BASE_TOP + 2 * millimeter);
            cut(context, id + "tslc", hs, id + "tsl");

            // 6) 경량화 창 4면 (덱 밑면 ~ 립 위). 벽은 프레임으로 남는다.
            const winZ0 = LIP_TOP + WIN_BOT;
            const winZ1 = DECK_B - WIN_TOP;
            const winL = HOUSE_OUT - 2 * WIN_MARGIN;
            mkRound(context, id + "wx", vector(CX, CY), vector(BIG, winL),
                10 * millimeter, winZ0, winZ1);
            cut(context, id + "wxc", hs, id + "wx" + "a");
            mkRound(context, id + "wy", vector(CX, CY), vector(winL, BIG),
                10 * millimeter, winZ0, winZ1);
            cut(context, id + "wyc", hs, id + "wy" + "a");

            // 6b) 스커트 경량화 — 립 아래 벽은 20도 절단 때문에 +Y 쪽이 매우 길다.
            //     캐리어 밑면 아래로 SKIRT_GAP 만 남기고 창을 내어 코너 다리 4개만 남긴다.
            //     (캐리어 등록용 안내면은 립~캐리어 밑면 구간에 그대로 보존된다)
            const skZ = CAR_BOT - SKIRT_GAP;
            const skL = HOUSE_OUT - 2 * SKIRT_MRG;
            mkRound(context, id + "sx", vector(CX, CY), vector(BIG, skL),
                10 * millimeter, GROUND_Z - 60 * millimeter, skZ);
            cut(context, id + "sxc", hs, id + "sx" + "a");
            mkRound(context, id + "sy", vector(CX, CY), vector(skL, BIG),
                10 * millimeter, GROUND_Z - 60 * millimeter, skZ);
            cut(context, id + "syc", hs, id + "sy" + "a");

            // 7) M3 인서트 구멍 6개 (립 밑면에서 위로)
            for (var s = 0; s < size(SCREWS); s += 1)
            {
                const p = screwXY(s);
                const iid = id + ("ins" ~ s);
                fCylinder(context, iid, {
                            "topCenter" : vector(p[0], p[1], CAR_TOP + INSERT_L),
                            "bottomCenter" : vector(p[0], p[1], CAR_TOP - 1 * millimeter),
                            "radius" : INSERT_D / 2
                        });
                cut(context, iid + "c", hs, iid);
            }

            // 8) 지면 평면 (20도) 으로 밑면 절단 — 각도는 여기 한 곳에만 존재한다
            const bp = vector(CX, CY, GROUND_Z);
            const sk = newSketchOnPlane(context, id + "gsk",
                    { "sketchPlane" : plane(bp, UP_LOCAL, vector(1, 0, 0)) });
            skRectangle(sk, "r", {
                        "firstCorner" : vector(-BIG, -BIG),
                        "secondCorner" : vector(BIG, BIG)
                    });
            skSolve(sk);
            opExtrude(context, id + "gex", {
                        "entities" : qSketchRegion(id + "gsk", false),
                        "direction" : -UP_LOCAL,
                        "endBound" : BoundingType.BLIND,
                        "endDepth" : BIG
                    });
            cut(context, id + "gcut", hs, id + "gex");
            return;
        }
    });
