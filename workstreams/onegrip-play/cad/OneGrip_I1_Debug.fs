FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/* ============================================================================
   INDEX holder atomic pipeline + rear retainer (OneGrip Play)

   검증된 순서 (버튼마다 독립 Feature, 배열/다중 target 금지):
       BLANK → SEAT → REAR → LIP → [SPLITCLIP] → GROOVE → CLEARNBR → UNION
       그리고 RETAINER (별도 body, 쉘과 union 하지 않음)

   쉘(JaD/JfD)에 대한 negative boolean 은 이 파일에 존재하지 않는다.
   holder 는 blank NEW BODY 로 완성한 뒤 마지막에 ADD UNION 만 한다.
   UNION 은 반드시 qUnion([shell, blank]) — 기존 shell 이 첫 원소여야
   partId(JaD/JfD) identity 가 보존된다.

   blank 는 생성한 Feature 의 id 로 직접 참조한다 (qContainsPoint 오식별 방지).

   [F2 개정 — 2026-08-19 승인]
   국소법선 정렬(OPTION B)은 축 수렴으로 I1-I2 스위치가 1.833mm 관통한다(docs/12).
   F2 는 축을 법선에서 최대 16.46도 완화해 최소 스위치 여유 1.200mm 를 확보한다(docs/13).
   버튼 중심 / Z=+9 / 피치 11 / 캡 8 / 6x6x6 / 3+1 ownership 은 전부 그대로다.

   변경점 3가지:
     1. IDX 의 "n" = F2 승인 축. "n0" = 원래 국소법선(개구부·캡·트림 기준면).
     2. GROOVE 단계 -> FRONT TRIM 으로 전환. blank 를 n0 깊이 2.8mm 평면으로 자른다.
        (외피 돌출 1.0~1.6mm 와 캡 이동공간 침범 0.86~0.89mm 를 동시에 해소)
        enum 식별자 GROOVE 는 기존 feature JSON 호환을 위해 유지한다.
     3. RETAINER 단계 폐기(no-op). 개별 twist-lock plug 는 상호 간섭으로 불가.
        후속: I1/I2/I3 공용 후면 retaining plate.

   front lip = 1.5mm (F2 승인). 트리 변수 #finger_switch_front_lip(0.8) 은 폐기되었으나
   변수 피처 수정에 필요한 /features GET 이 rate limit 상태라 여기서 상수로 둔다.
   rate limit 해제 후 트리 변수를 1.5 로 바꾸고 getVariable 로 되돌릴 것.
   ============================================================================ */

export enum IdxButton
{
    annotation { "Name" : "I1" }
    I1,
    annotation { "Name" : "I2" }
    I2,
    annotation { "Name" : "I3" }
    I3,
    annotation { "Name" : "I4" }
    I4
}

export enum IdxStage
{
    annotation { "Name" : "A blank only" }
    BLANK,
    annotation { "Name" : "B switch seat" }
    SEAT,
    annotation { "Name" : "C rear opening" }
    REAR,
    annotation { "Name" : "D front lip / stem bore" }
    LIP,
    annotation { "Name" : "E split clip (X=0)" }
    SPLITCLIP,
    annotation { "Name" : "E2 clear neighbour seats" }
    CLEARNBR,
    annotation { "Name" : "E3 front trim" }
    GROOVE,
    annotation { "Name" : "F union into shell" }
    UNION,
    annotation { "Name" : "G unused (retired)" }
    RETAINER
}

// 버튼 중심 p (변경 금지) / F2 승인 축 n / 원래 국소법선 n0 (개구부·캡·트림 기준)
const IDX = [
    { "p" : vector(-22.224, -17.494, 9.000),
      // ITS-1105 6.18x6.12 design-envelope refinement: +0.408 deg max.
      "n" : vector(-0.847667872, -0.506166919, -0.158915794),
      "n0" : vector(-0.9291, -0.2385, -0.2828), "dom" : true },
    { "p" : vector(-15.970, -26.208, 9.000),
      "n" : vector(-0.387542111, -0.574231284, -0.721158474),
      "n0" : vector(-0.4724, -0.7368, -0.4838), "dom" : true },
    { "p" : vector(-5.496, -29.325, 9.000),
      "n" : vector(-0.068454195, -0.997609880, 0.009410170),
      "n0" : vector(-0.0383, -0.9556, -0.2921), "dom" : true },
    { "p" : vector(5.496, -29.325, 9.000),
      "n" : vector(0.024161, -0.968017, -0.249718),
      "n0" : vector(0.0383, -0.9556, -0.2921), "dom" : false }
];

// ===== TECHNICAL DEBT / TODO =====
// 승인된 front lip = 2.3 mm (docs/15). 이것이 형상의 source of truth 다.
// 트리 변수 #finger_switch_front_lip(0.8) 은 사문(死文)이며 절대 기준으로 쓰지 말 것.
// /features GET rate limit 해제 후: 트리 변수를 2.3 으로 바꾸고 getVariable 로 되돌린다.
const LIP_F2 = 2.3 * millimeter;

// 쉘 식별점 — 어떤 피처도 제거하지 않는 두꺼운 재료 구간(Z=-35, 두께 9.77mm)
const DOM_WALL_PT = vector(-4.8872, 0.0000, -35.0000);
const OPP_WALL_PT = vector(4.8859, 0.0000, -35.0000);

const SHELL_WALL = 3 * millimeter;
const HOLDER_WALL = 3 * millimeter;
const FUSE = 0.2 * millimeter;

function btnIndex(b is IdxButton) returns number
{
    if (b == IdxButton.I1) return 0;
    if (b == IdxButton.I2) return 1;
    if (b == IdxButton.I3) return 2;
    return 3;
}

function btnCS(b is map) returns CoordSystem
{
    const zA = normalize(b.n);
    const xA = normalize(cross(vector(0, 0, 1), zA));
    return coordSystem(b.p * millimeter, xA, zA);
}

// 원래 국소법선 기준 좌표계 — 개구부 / 캡 / front trim 이 쓰는 기준면
function btnCS0(b is map) returns CoordSystem
{
    const zA = normalize(b.n0);
    const xA = normalize(cross(vector(0, 0, 1), zA));
    return coordSystem(b.p * millimeter, xA, zA);
}

function depthBox(context is Context, boxId is Id, cs is CoordSystem,
    w is ValueWithUnits, h is ValueWithUnits,
    dFrom is ValueWithUnits, dTo is ValueWithUnits)
{
    fCuboid(context, boxId, {
                "corner1" : vector(-w / 2, -h / 2, -dTo),
                "corner2" : vector(w / 2, h / 2, -dFrom)
            });
    opTransform(context, boxId + "xf", {
                "bodies" : qCreatedBy(boxId, EntityType.BODY),
                "transform" : toWorld(cs)
            });
}

function depthCyl(context is Context, cylId is Id, cs is CoordSystem,
    r is ValueWithUnits, dFrom is ValueWithUnits, dTo is ValueWithUnits)
{
    fCylinder(context, cylId, {
                "topCenter" : vector(0 * millimeter, 0 * millimeter, -dFrom),
                "bottomCenter" : vector(0 * millimeter, 0 * millimeter, -dTo),
                "radius" : r
            });
    opTransform(context, cylId + "xf", {
                "bodies" : qCreatedBy(cylId, EntityType.BODY),
                "transform" : toWorld(cs)
            });
}

annotation { "Feature Type Name" : "INDEX holder atomic" }
export const idxHolderAtomic = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Button" }
        definition.button is IdxButton;
        annotation { "Name" : "Stage" }
        definition.stage is IdxStage;
        annotation { "Name" : "Blank feature id" }
        definition.blankId is string;
    }
    {
        const pockW = getVariable(context, "finger_switch_pocket_width");
        const totH = getVariable(context, "finger_switch_total_height");
        const lip = LIP_F2;   // F2 승인 1.5mm (트리 변수 #finger_switch_front_lip 폐기)
        const bore = getVariable(context, "finger_switch_stem_bore");
        const retClr = getVariable(context, "finger_retainer_clearance");

        const b = IDX[btnIndex(definition.button)];
        const cs = btnCS(b);

        const swFront = SHELL_WALL + lip;          // 5.3  (3.0 + 2.3)
        const swRear = swFront + totH;             // 11.3
        const seatTo = swRear + retClr;            // 11.5
        const blankFrom = SHELL_WALL - FUSE;       // 2.8  (= front trim 평면 깊이)
        // [수정안] 개별 twist-lock plug 폐기로 retT(2.5) 예비 불필요.
        // 후단을 줄여 I4 <-> 나사 B 3D 여유를 회복한다 (docs/14 HOLD-3).
        const blankTo = seatTo + 1 * millimeter;   // 12.5
        const holderW = pockW + 2 * HOLDER_WALL;   // 12.4

        if (definition.stage == IdxStage.BLANK)
        {
            depthBox(context, id + "blank", cs, holderW, holderW, blankFrom, blankTo);
            return;
        }

        if (definition.stage == IdxStage.RETAINER)
        {
            // === 폐기 (F2) ===
            // 개별 twist-lock plug 4개는 깊이 10~15mm 구간에서 축이 3.2~4.4mm 로 수렴해
            // 서로 0.000mm 간섭한다(docs/12). 기하학적으로 불가능하므로 형상을 만들지 않는다.
            // 기존 plug body(Part 17~20)는 이 no-op 로 사라진다.
            // 후속: I1/I2/I3 공용 후면 retaining plate (docs/13 §10.3).
            return;
        }

        // 이후 모든 단계는 blank 를 만든 Feature 의 id 로 직접 참조한다.
        const blank = qCreatedBy(makeId(definition.blankId), EntityType.BODY);

        if (definition.stage == IdxStage.SEAT)
        {
            depthBox(context, id + "seat", cs, pockW, pockW, swFront, seatTo);
            opBoolean(context, id + "seatcut", {
                        "tools" : qCreatedBy(id + "seat", EntityType.BODY),
                        "targets" : blank,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == IdxStage.REAR)
        {
            depthBox(context, id + "rear", cs, pockW, pockW, seatTo, blankTo + 2 * millimeter);
            opBoolean(context, id + "rearcut", {
                        "tools" : qCreatedBy(id + "rear", EntityType.BODY),
                        "targets" : blank,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == IdxStage.LIP)
        {
            depthBox(context, id + "bore", cs, bore, bore, 1 * millimeter, swFront);
            opBoolean(context, id + "borecut", {
                        "tools" : qCreatedBy(id + "bore", EntityType.BODY),
                        "targets" : blank,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == IdxStage.SPLITCLIP)
        {
            const lo = b.dom ? 0 * millimeter : -60 * millimeter;
            const hi = b.dom ? 60 * millimeter : 0 * millimeter;
            fCuboid(context, id + "clip", {
                        "corner1" : vector(lo, -80 * millimeter, -80 * millimeter),
                        "corner2" : vector(hi, 80 * millimeter, 80 * millimeter)
                    });
            opBoolean(context, id + "clipcut", {
                        "tools" : qCreatedBy(id + "clip", EntityType.BODY),
                        "targets" : blank,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == IdxStage.GROOVE)
        {
            // === FRONT TRIM (F2) ===
            // blank 앞면을 '축에 수직한 평면'이 아니라 '원래 법선 n0 깊이 2.8mm 평면'으로 자른다.
            // 축이 기울면 축수직 앞면이 (a) 외피를 1.0~1.6mm 뚫고 나오고
            // (b) 캡 이동공간을 0.86~0.89mm 침범한다. 이 한 단계가 둘 다 없앤다.
            // target 은 이 blank 하나뿐. 쉘은 절대 target 이 아니다.
            depthBox(context, id + "trim", btnCS0(b), 60 * millimeter, 60 * millimeter,
                -60 * millimeter, blankFrom);
            opBoolean(context, id + "trimcut", {
                        "tools" : qCreatedBy(id + "trim", EntityType.BODY),
                        "targets" : blank,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == IdxStage.CLEARNBR)
        {
            // 이웃 버튼의 seat / groove 기둥을 이 blank 에서 미리 비운다.
            // union 순서상 나중에 합쳐지는 blank 의 solid 재료가
            // 먼저 만든 이웃 seat 를 메우는 것을 방지한다.
            // [F2] 폭은 반드시 pocket 폭(6.4)이다. groove 가 없어졌고,
            // 7.4 를 쓰면 이웃 포켓 표면을 0.5mm 넘어 파서 0.80mm 칸막이가 0.30mm 가 된다.
            // 시작 깊이는 blankFrom 앞이어야 한다 (swFront 부터면 보어 구간이 남는다).
            const grvW = pockW;
            for (var k = 0; k < size(IDX); k += 1)
            {
                if (k == btnIndex(definition.button))
                    continue;
                const ocs = btnCS(IDX[k]);
                depthBox(context, id + ("s" ~ k), ocs, grvW, grvW,
                    blankFrom - 1 * millimeter, blankTo + 2 * millimeter);
                try silent
                {
                    opBoolean(context, id + ("clear" ~ k), {
                                "tools" : qCreatedBy(id + ("s" ~ k), EntityType.BODY),
                                "targets" : blank,
                                "operationType" : BooleanOperationType.SUBTRACTION
                            });
                }
            }
        }
        else if (definition.stage == IdxStage.UNION)
        {
            const shell = qContainsPoint(qAllSolidBodies(),
                (b.dom ? DOM_WALL_PT : OPP_WALL_PT) * millimeter);
            opBoolean(context, id + "add", {
                        "tools" : qUnion([shell, blank]),
                        "operationType" : BooleanOperationType.UNION
                    });
        }
    });
