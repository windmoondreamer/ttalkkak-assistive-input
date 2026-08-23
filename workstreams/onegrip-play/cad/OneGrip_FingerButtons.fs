FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/* ============================================================================
   OneGrip Play — 신규 INDEX 손가락 버튼  (V3 / RIGHT HAND / #hand_sign = +1)

   좌표계: X=좌우(분할면 X=0), Y=전후(전면 -Y), Z=그립축.
   DOMINANT = Joystick_2 (X<0) : I1, I2, I3     OPPOSITE = Joystick_1 (X>0) : I4

   [V3 아키텍처 — pre-union holder]
   원본 쉘(JaD/JfD)에 holder 관련 **negative boolean 을 절대 수행하지 않는다.**
       1) holder blank 를 NEW BODY 로 생성
       2) blank 자체만 target 으로 seat / stem bore 제거
       3) 마지막에 blank 를 쉘에 ADD UNION (target 을 qUnion 첫 원소로)
   이렇게 해서 subtractive op 로 JfD 가 split 될 가능성을 구조적으로 제거한다.
   쉘에 대한 유일한 negative op 는 승인된 버튼 개구부(OPENINGS)뿐이다.

   [스위치 기준] 원작자 명시 사양 = 6 x 6 x 6 mm tactile push switch.
   문서에 임포트된 PushBtn.SLDPRT(7.566 x 8.519 x 6.010)는 참조 모델일 뿐
   기계적 envelope 의 source of truth 로 쓰지 않는다.
   body / stem 분할은 실제 구매 부품 확정 전까지 파라미터로 남긴다.
   ============================================================================ */

export enum OneGripStage
{
    annotation { "Name" : "1 Construction" }
    CONSTRUCTION,
    annotation { "Name" : "2 Shell openings" }
    OPENINGS,
    annotation { "Name" : "3 Holders (pre-union)" }
    HOLDERS,
    annotation { "Name" : "4 Button caps" }
    CAPS,
    annotation { "Name" : "5 Rear retainer plates" }
    RETAINER
}

const IDX = [
    { "nm" : "I1", "p" : vector(-22.224, -17.494, 9.000),
      "n" : vector(-0.9291, -0.2385, -0.2828), "dom" : true,  "clip" : false },
    { "nm" : "I2", "p" : vector(-15.970, -26.208, 9.000),
      "n" : vector(-0.4724, -0.7368, -0.4838), "dom" : true,  "clip" : false },
    { "nm" : "I3", "p" : vector(-5.496, -29.325, 9.000),
      "n" : vector(-0.0383, -0.9556, -0.2921), "dom" : true,  "clip" : true },
    { "nm" : "I4", "p" : vector(5.496, -29.325, 9.000),
      "n" : vector(0.0383, -0.9556, -0.2921), "dom" : false, "clip" : true }
];

// 쉘 식별점 — 어떤 피처도 제거하지 않는 두꺼운 재료 구간(Z=-35, 두께 9.77mm)
const DOM_WALL_PT = vector(-4.8872, 0.0000, -35.0000);
const OPP_WALL_PT = vector(4.8859, 0.0000, -35.0000);

const SHELL_WALL = 3 * millimeter;
const HOLDER_WALL = 3 * millimeter;
const FUSE = 0.2 * millimeter;

function btnCS(b is map) returns CoordSystem
{
    const zA = normalize(b.n);
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

// 분할면 X=0 을 넘는 부분을 잘라낸다 (반대 쉘 침범 방지)
function clipAtSplit(context is Context, baseId is Id, bodyId is Id, dom is boolean)
{
    const lo = dom ? 0 * millimeter : -60 * millimeter;
    const hi = dom ? 60 * millimeter : 0 * millimeter;
    fCuboid(context, baseId, {
                "corner1" : vector(lo, -80 * millimeter, -80 * millimeter),
                "corner2" : vector(hi, 80 * millimeter, 80 * millimeter)
            });
    opBoolean(context, baseId + "cut", {
                "tools" : qCreatedBy(baseId, EntityType.BODY),
                "targets" : qCreatedBy(bodyId, EntityType.BODY),
                "operationType" : BooleanOperationType.SUBTRACTION
            });
}

annotation { "Feature Type Name" : "OneGrip INDEX buttons" }
export const oneGripIndexButtons = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Stage" }
        definition.stage is OneGripStage;
    }
    {
        const capW = getVariable(context, "finger_button_cap_width");
        const clr = getVariable(context, "finger_button_clearance");
        const capH = getVariable(context, "finger_button_cap_height");
        const pockW = getVariable(context, "finger_switch_pocket_width");
        const totH = getVariable(context, "finger_switch_total_height");
        const lip = getVariable(context, "finger_switch_front_lip");
        const bore = getVariable(context, "finger_switch_stem_bore");
        const retClr = getVariable(context, "finger_retainer_clearance");
        const retT = getVariable(context, "finger_retainer_thickness");

        const domShell = qContainsPoint(qAllSolidBodies(), DOM_WALL_PT * millimeter);
        const oppShell = qContainsPoint(qAllSolidBodies(), OPP_WALL_PT * millimeter);

        // ---- 깊이 기준 (전부 파라미터 종속) ----
        const swFront = SHELL_WALL + lip;          // 스위치 앞면
        const swRear = swFront + totH;             // 스위치 뒷면
        const seatTo = swRear + retClr;            // seat 끝
        const blankFrom = SHELL_WALL - FUSE;       // 벽과 융합시키기 위한 겹침
        const blankTo = seatTo + retT;             // retainer 자리까지
        const holderW = pockW + 2 * HOLDER_WALL;

        if (definition.stage == OneGripStage.CONSTRUCTION)
        {
            for (var i = 0; i < size(IDX); i += 1)
            {
                const cs = btnCS(IDX[i]);
                opPlane(context, id + IDX[i].nm + "pl", {
                            "plane" : plane(cs.origin, cs.zAxis, cs.xAxis),
                            "width" : 14 * millimeter,
                            "height" : 14 * millimeter
                        });
            }
        }
        else if (definition.stage == OneGripStage.OPENINGS)
        {
            // 쉘에 대한 유일한 negative op (승인된 버튼 개구부)
            for (var i = 0; i < size(IDX); i += 1)
            {
                const b = IDX[i];
                const sid = id + b.nm;
                depthBox(context, sid + "box", btnCS(b), capW, capW,
                    -3 * millimeter, 12 * millimeter);
                opBoolean(context, sid + "cut", {
                            "tools" : qCreatedBy(sid + "box", EntityType.BODY),
                            "targets" : b.dom ? domShell : oppShell,
                            "operationType" : BooleanOperationType.SUBTRACTION
                        });
            }
        }
        else if (definition.stage == OneGripStage.HOLDERS)
        {
            // --- 1) blank 를 NEW BODY 로 생성 (쉘과 무관) ---
            for (var i = 0; i < size(IDX); i += 1)
            {
                const b = IDX[i];
                const sid = id + b.nm;
                depthBox(context, sid + "blank", btnCS(b), holderW, holderW,
                    blankFrom, blankTo);
                if (b.clip)
                    clipAtSplit(context, sid + "blankclip", sid + "blank", b.dom);
            }

            // --- 2) seat + stem bore 를 blank 에만 제거 ---
            //     (쉘은 target 이 아니다. 이웃 blank 도 함께 대상으로 넣어
            //      한 blank 가 다른 blank 의 seat 를 메우지 않게 한다)
            var domBlanks = [];
            var oppBlanks = [];
            var domTools = [];
            var oppTools = [];
            for (var i = 0; i < size(IDX); i += 1)
            {
                const b = IDX[i];
                const sid = id + b.nm;
                const cs = btnCS(b);
                depthBox(context, sid + "seat", cs, pockW, pockW, swFront, seatTo);
                depthBox(context, sid + "bore", cs, bore, bore, 1 * millimeter, swFront);
                if (b.dom)
                {
                    domBlanks = append(domBlanks, qCreatedBy(sid + "blank", EntityType.BODY));
                    domTools = append(domTools, qCreatedBy(sid + "seat", EntityType.BODY));
                    domTools = append(domTools, qCreatedBy(sid + "bore", EntityType.BODY));
                }
                else
                {
                    oppBlanks = append(oppBlanks, qCreatedBy(sid + "blank", EntityType.BODY));
                    oppTools = append(oppTools, qCreatedBy(sid + "seat", EntityType.BODY));
                    oppTools = append(oppTools, qCreatedBy(sid + "bore", EntityType.BODY));
                }
            }
            // 쉘별로 분리해서 제거 (서로 만나지 않는 tool/target 조합을 만들지 않는다)
            opBoolean(context, id + "hollowDom", {
                        "tools" : qUnion(domTools),
                        "targets" : qUnion(domBlanks),
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
            opBoolean(context, id + "hollowOpp", {
                        "tools" : qUnion(oppTools),
                        "targets" : qUnion(oppBlanks),
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });

            // --- 3) 마지막에 쉘과 ADD UNION (target 을 첫 원소로 -> partId 보존) ---
            opBoolean(context, id + "domAdd", {
                        "tools" : qUnion(concatenateArrays([[domShell], domBlanks])),
                        "operationType" : BooleanOperationType.UNION
                    });
            opBoolean(context, id + "oppAdd", {
                        "tools" : qUnion(concatenateArrays([[oppShell], oppBlanks])),
                        "operationType" : BooleanOperationType.UNION
                    });
        }
        else if (definition.stage == OneGripStage.CAPS)
        {
            for (var i = 0; i < size(IDX); i += 1)
            {
                const cw = capW - 2 * clr;
                const inner = SHELL_WALL - FUSE - clr;
                depthBox(context, id + IDX[i].nm + "cap", btnCS(IDX[i]), cw, cw,
                    inner - capH, inner);
            }
        }
        else if (definition.stage == OneGripStage.RETAINER)
        {
            // 스위치 뒷면을 축방향으로 누르는 제거 가능한 판 (버튼별 별도 body).
            // 위치는 전부 파라미터 종속이므로 실제 스위치 확정 시 자동 갱신된다.
            for (var i = 0; i < size(IDX); i += 1)
            {
                depthBox(context, id + IDX[i].nm + "ret", btnCS(IDX[i]),
                    pockW - 2 * retClr, pockW - 2 * retClr, seatTo, seatTo + retT);
            }
        }
    });
