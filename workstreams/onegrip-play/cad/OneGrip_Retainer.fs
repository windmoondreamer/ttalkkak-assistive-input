FeatureScript 2878;
import(path : "onshape/std/geometry.fs", version : "2878.0");

/* ============================================================================
   OneGrip Play — INDEX 후면 retainer (NEGATIVE-MOLD 방식)

   승인 근거: docs/16 §R (평면 cap 폐기) + 이번 실행의 복셀/삽입경로 해석.

   [핵심] retainer 는 별도 NEW PART 다. JaD/JfD 와 union 하지 않는다.
          SUBTRACT target 은 항상 retainer body 하나뿐.
          기존 쉘/홀더는 tool·reference 로만 쓴다.

   [형상] blank − (홀더 4개 + fit clr, 삽입방향으로 sweep)
                − (나사 B 보스 + 여유, 삽입방향으로 sweep)
                + pad 3개  − 배선슬롯 3개

   [삽입방향] w = 세 스위치 축을 감싸는 최소 원뿔의 축.
          세 축 모두와 30.08도 -> pad(3.6) 가 보어(6.4) 에서 빠져나올 수 있다
          (허용 한계 46.0도). 홀더·쉘 sweep 을 미리 빼두었으므로 직선 인출이 성립한다.
   ============================================================================ */

export enum RetStage
{
    annotation { "Name" : "A blank" }
    BLANK,
    annotation { "Name" : "B cut holders (swept)" }
    CUTHOLD,
    annotation { "Name" : "C cut screw B (swept)" }
    CUTSCREW,
    annotation { "Name" : "D pads" }
    PADS,
    annotation { "Name" : "E wiring slots" }
    SLOTS,
    annotation { "Name" : "F cut shell (copy)" }
    SHELLCUT,
    annotation { "Name" : "G insertion relief (screw B boss, swept)" }
    RELIEF,
    annotation { "Name" : "H1 EAR_A prime" }
    EARA,
    annotation { "Name" : "H2 EAR_B prime" }
    EARB,
    annotation { "Name" : "I1 shell boss B" }
    BOSSB,
    annotation { "Name" : "J1 fastening hole A" }
    HOLEA,
    annotation { "Name" : "J2 fastening hole B" }
    HOLEB
}

// F2 확정 축 (docs/15). 변경 금지.
const IDX = [
    { "p" : vector(-22.224, -17.494, 9.000), "n" : vector(-0.851033, -0.500047, -0.160298) },
    { "p" : vector(-15.970, -26.208, 9.000), "n" : vector(-0.393870, -0.571110, -0.720208) },
    { "p" : vector(-5.496, -29.325, 9.000),  "n" : vector(-0.069850, -0.997555, 0.002429) },
    { "p" : vector(5.496, -29.325, 9.000),   "n" : vector(0.024161, -0.968017, -0.249718) }
];

// 삽입/인출 방향 (retainer 가 이 방향으로 들어가 자리잡는다)
const WIN = vector(-0.4734, -0.8350, -0.2805);

const FIT = 0.25 * millimeter;      // #finger_retainer_fit_clearance
const PRELOAD = 0.15 * millimeter;  // #finger_retainer_preload
const PAD_W = 3.6 * millimeter;
const SLOT_W = 2.5 * millimeter;
const SLOT_D = 1.5 * millimeter;

const BLANK_FROM = 12.5 * millimeter;   // 홀더 뒷면
const BLANK_TO = 17.0 * millimeter;     // retainer 뒤끝 (인출 성립 확인된 범위)
const BLANK_LAT = 15.0 * millimeter;
const SW_REAR = 11.3 * millimeter;      // 스위치 뒷면
const HOLD_W = 12.4 * millimeter;
const HOLD_FROM = 2.8 * millimeter;
const HOLD_TO = 12.5 * millimeter;

const SWEEP_STEP = 4 * millimeter;
const SWEEP_N = 12;

// 배선 슬롯 방향: I1 -v / I2 +v / I3 -v  (docs/16 §R6)
const SLOT_SIGN = [-1, 1, -1];

/* ===== FASTENING (docs/23) — 나사 규격은 전부 PROVISIONAL =====
   실제 SKU 미확정. M2 급 소형 나사를 가정한 잠정값이며 확정 시 갱신한다.
   기존 쉘 Screw_holes 규격을 복사한 것이 아니다.                                */
const SCREW_D   = 2.0 * millimeter;   // #finger_retainer_screw_diameter   PROVISIONAL
const SCREW_CLR = 0.2 * millimeter;   // #finger_retainer_screw_clearance  -> 관통공 2.4
const PILOT_D   = 1.7 * millimeter;   // 셀프탭 하공                        PROVISIONAL
const BOSS_OD   = 5.0 * millimeter;   // #finger_retainer_boss_od          PROVISIONAL
const HEAD_D    = 3.8 * millimeter;   // #finger_retainer_head_diameter    PROVISIONAL
const HEAD_H    = 1.6 * millimeter;   // #finger_retainer_head_height      PROVISIONAL
const EAR_OD    = 7.0 * millimeter;   // 반경 3.5 — 실측 여유 안 (A: s<=+1.75, B: s<=-0.5)
                                      // 관통공 2.4 기준 벽 두께 (7.0-2.4)/2 = 2.3mm

// 앵커 (docs/22 승인). 나사축 = w. 체결하면 retainer 가 +w 로 당겨져 pad 가 스위치를 누른다.
const EAR_A = vector(-14.11, -4.03, 11.24);
const EAR_B = vector(-4.52, -15.38, 1.97);
// 앵커 기준 w 축 국소 구간 (실측):
//   A : retainer [0,+1.8]  틈 [+1.8,+2.8]  쉘 [+2.8,+9.0]   -> 쉘 6.2mm, 보스 불필요
//   B : retainer [-3.4,0]  틈 [0,+5.1]     쉘 [+5.1,+8.5]   -> 쉘 3.4mm, 보스 필요
// 쉘 침범 없는 최대 s (반경 2.5 기준, 실측): A +1.75 / B +0.25
const EAR_A_FROM = -2.5 * millimeter;  const EAR_A_TO = 1.5 * millimeter;
// EAR_B 는 -w 로 더 돌출시켜야 드라이버가 접근한다 (주변 retainer 가 s=-3.7 까지 있음)
const EAR_B_FROM = -6.0 * millimeter;  const EAR_B_TO = -0.5 * millimeter;
const BOSS_B_FROM = 0.5 * millimeter;  const BOSS_B_TO = 5.2 * millimeter;

function axCS(org is Vector) returns CoordSystem
{
    const zA = normalize(WIN) * -1;             // 깊이(+) 가 +w 가 되도록
    const xA = normalize(cross(vector(0, 0, 1), zA));
    return coordSystem(org, xA, zA);
}

// 쉘 식별점 (홀더 파이프라인과 동일). 어떤 피처도 제거하지 않는 두꺼운 구간
const DOM_WALL_PT = vector(-4.8872, 0.0000, -35.0000);
const OPP_WALL_PT = vector(4.8859, 0.0000, -35.0000);

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

// 주어진 body 를 WIN 방향으로 sweep (평행이동 복사 후 union). 볼록체라 정확한 sweep 이 된다.
function sweepAlongW(context is Context, baseId is Id, sid is Id)
{
    var xf = [];
    var nm = [];
    for (var k = 1; k <= SWEEP_N; k += 1)
    {
        xf = append(xf, transform(normalize(WIN) * (k * SWEEP_STEP)));
        nm = append(nm, "s" ~ k);
    }
    opPattern(context, sid + "pat", {
                "entities" : qCreatedBy(baseId, EntityType.BODY),
                "transforms" : xf,
                "instanceNames" : nm
            });
    opBoolean(context, sid + "uni", {
                "tools" : qUnion([qCreatedBy(baseId, EntityType.BODY),
                            qCreatedBy(sid + "pat", EntityType.BODY)]),
                "operationType" : BooleanOperationType.UNION
            });
}

annotation { "Feature Type Name" : "OneGrip INDEX retainer" }
export const oneGripIndexRetainer = defineFeature(function(context is Context, id is Id, definition is map)
    precondition
    {
        annotation { "Name" : "Stage" }
        definition.stage is RetStage;
        annotation { "Name" : "Retainer feature id" }
        definition.bodyId is string;
    }
    {
        if (definition.stage == RetStage.BLANK)
        {
            for (var i = 0; i < 3; i += 1)
                depthBox(context, id + ("b" ~ i), btnCS(IDX[i]), BLANK_LAT, BLANK_LAT,
                    BLANK_FROM, BLANK_TO);
            opBoolean(context, id + "join", {
                        "tools" : qUnion([qCreatedBy(id + "b0", EntityType.BODY),
                                    qCreatedBy(id + "b1", EntityType.BODY),
                                    qCreatedBy(id + "b2", EntityType.BODY)]),
                        "operationType" : BooleanOperationType.UNION
                    });
            return;
        }

        const body = qCreatedBy(makeId(definition.bodyId), EntityType.BODY);

        if (definition.stage == RetStage.CUTHOLD)
        {
            for (var i = 0; i < size(IDX); i += 1)
            {
                const sid = id + ("h" ~ i);
                depthBox(context, sid + "box", btnCS(IDX[i]),
                    HOLD_W + 2 * FIT, HOLD_W + 2 * FIT, HOLD_FROM - FIT, HOLD_TO + FIT);
                sweepAlongW(context, sid + "box", sid);
                opBoolean(context, sid + "cut", {
                            "tools" : qCreatedBy(sid, EntityType.BODY),
                            "targets" : body,
                            "operationType" : BooleanOperationType.SUBTRACTION
                        });
            }
        }
        else if (definition.stage == RetStage.CUTSCREW)
        {
            fCylinder(context, id + "sc", {
                        "topCenter" : vector(-20 * millimeter, -14.45 * millimeter, 23.07 * millimeter),
                        "bottomCenter" : vector(11 * millimeter, -14.45 * millimeter, 23.07 * millimeter),
                        "radius" : 4.5 * millimeter
                    });
            // [수정] sweep 하지 않는다. 나사 B 보스는 fit 여유만 확보하면 되고,
            // 이를 삽입방향으로 sweep 하면 과대 절삭이 되어 retainer 가 3조각으로 갈라진다.
            opBoolean(context, id + "sccut", {
                        "tools" : qCreatedBy(id + "sc", EntityType.BODY),
                        "targets" : body,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == RetStage.PADS)
        {
            var tools = [body];
            for (var i = 0; i < 3; i += 1)
            {
                depthBox(context, id + ("p" ~ i), btnCS(IDX[i]), PAD_W, PAD_W,
                    SW_REAR - PRELOAD, BLANK_FROM + 1 * millimeter);
                tools = append(tools, qCreatedBy(id + ("p" ~ i), EntityType.BODY));
            }
            opBoolean(context, id + "padadd", {
                        "tools" : qUnion(tools),
                        "operationType" : BooleanOperationType.UNION
                    });
        }
        else if (definition.stage == RetStage.RELIEF)
        {
            // === LOCAL SCREW-B SWEPT RELIEF (docs/19 승인) ===
            // service disengagement 정의: d_required 1.57 + margin 0.50 = d_service 2.07 mm.
            // 그 구간의 유일한 장애물은 나사 B 보스(전체 차단의 100%, 2.1%/42mm3)이고,
            // 주 shell wall 은 이 구간에 관여하지 않는다.
            // 보스 원통(r 3.5 + fit)을 w 로 3.00 mm 만 sweep 해 retainer 에서만 뺀다.
            //   [개정 docs/21] sweep 3.00 -> 2.07 mm.
            //   요구 인출량이 곧 d_service 2.07 이므로 이것이 필요·충분값이고,
            //   3.00 의 초과분이 web 을 0.52mm 깎고 있었다.
            //   예측: 제거 65.7mm3, 단일 body, web 2.12mm, travel 2.42mm.
            //   이산화(0.5/0.25/0.10/연속)는 결과에 영향이 없음이 입증되었다(docs/21).
            //   sweep 2.50 은 body 가 2분할되므로 금지.
            // SUBTRACT target 은 retainer body 하나뿐. 쉘/홀더/나사는 tool·reference 로만 쓴다.
            fCylinder(context, id + "bs", {
                        "topCenter" : vector(-22 * millimeter, -14.45 * millimeter, 23.07 * millimeter),
                        "bottomCenter" : vector(1 * millimeter, -14.45 * millimeter, 23.07 * millimeter),
                        "radius" : (3.5 * millimeter) + FIT
                    });
            var xf = [];
            var nm = [];
            for (var k = 1; k <= 6; k += 1)
            {
                xf = append(xf, transform(normalize(WIN) * (k * 0.345 * millimeter)));
                nm = append(nm, "r" ~ k);
            }
            opPattern(context, id + "bspat", {
                        "entities" : qCreatedBy(id + "bs", EntityType.BODY),
                        "transforms" : xf,
                        "instanceNames" : nm
                    });
            opBoolean(context, id + "bscut", {
                        "tools" : qUnion([qCreatedBy(id + "bs", EntityType.BODY),
                                    qCreatedBy(id + "bspat", EntityType.BODY)]),
                        "targets" : body,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == RetStage.EARA || definition.stage == RetStage.EARB)
        {
            const isA = (definition.stage == RetStage.EARA);
            const org = (isA ? EAR_A : EAR_B) * millimeter;
            const s0 = isA ? EAR_A_FROM : EAR_B_FROM;
            const s1 = isA ? EAR_A_TO : EAR_B_TO;
            depthCyl(context, id + "ear", axCS(org), EAR_OD / 2, s0, s1);
            opBoolean(context, id + "earadd", {
                        "tools" : qUnion([body, qCreatedBy(id + "ear", EntityType.BODY)]),
                        "operationType" : BooleanOperationType.UNION
                    });
        }
        else if (definition.stage == RetStage.BOSSB)
        {
            // 쉘(JfD) 에 ADD UNION. target 을 첫 원소로 두어 partId 를 보존한다.
            depthCyl(context, id + "bb", axCS(EAR_B * millimeter), BOSS_OD / 2,
                BOSS_B_FROM, BOSS_B_TO);
            const shell = qContainsPoint(qAllSolidBodies(), DOM_WALL_PT * millimeter);
            opBoolean(context, id + "bbadd", {
                        "tools" : qUnion([shell, qCreatedBy(id + "bb", EntityType.BODY)]),
                        "operationType" : BooleanOperationType.UNION
                    });
        }
        else if (definition.stage == RetStage.HOLEA || definition.stage == RetStage.HOLEB)
        {
            const isA = (definition.stage == RetStage.HOLEA);
            const org = (isA ? EAR_A : EAR_B) * millimeter;
            const s0 = isA ? EAR_A_FROM : EAR_B_FROM;
            // 관통공 (retainer 쪽) — ear 전체를 관통
            depthCyl(context, id + "clr", axCS(org), (SCREW_D + 2 * SCREW_CLR) / 2,
                s0 - 0.5 * millimeter, (isA ? EAR_A_TO : EAR_B_TO) + 0.5 * millimeter);
            // [개정] 카운터보어는 파지 않는다. ⌀3.8 자리를 파면 ear 벽이 0.6mm 로 얇아져
            // structural neck 이 0.19mm 까지 떨어졌다(docs/23). 나사 머리는 ear 의 -w 면에
            // 그대로 앉는다 (그쪽은 열린 공간이라 간섭 없음).
            opBoolean(context, id + "holecut", {
                        "tools" : qCreatedBy(id + "clr", EntityType.BODY),
                        "targets" : body,
                        "operationType" : BooleanOperationType.SUBTRACTION
                    });
        }
        else if (definition.stage == RetStage.SHELLCUT)
        {
            // 쉘을 '복사본' 으로 빼낸다. 원본 JaD/JfD 는 opPattern 복사만 하므로 손상되지 않는다.
            for (var k = 0; k < 2; k += 1)
            {
                const pt = (k == 0 ? DOM_WALL_PT : OPP_WALL_PT) * millimeter;
                const sid = id + ("sh" ~ k);
                // 원위치 복사는 Onshape 가 거부하므로 멀리 복사한 뒤 되돌린다.
                const away = vector(500, 0, 0) * millimeter;
                opPattern(context, sid + "cp", {
                            "entities" : qContainsPoint(qAllSolidBodies(), pt),
                            "transforms" : [transform(away)],
                            "instanceNames" : ["c"]
                        });
                opTransform(context, sid + "back", {
                            "bodies" : qCreatedBy(sid + "cp", EntityType.BODY),
                            "transform" : transform(-away)
                        });
                // [개정 docs/23] 쉘 복사본을 삽입방향 w 로 짧게 sweep 해서 뺀다.
                // 0 clearance 로 빼면 retainer 표면이 쉘과 정확히 접해 미끄러지지 못하고
                // service travel 이 1.83mm 로 떨어졌다. w 로 0.3mm 만 sweep 하면
                // 인출 방향으로 실제 여유가 생긴다 (0.15mm inset 만으로 travel 2.55 회복 확인).
                var sxf = [];
                var snm = [];
                // service travel 전 구간(2.07mm)을 덮어야 인출이 성립한다.
                for (var m = 1; m <= 6; m += 1)
                {
                    sxf = append(sxf, transform(normalize(WIN) * (m * 0.345 * millimeter)));
                    snm = append(snm, "sw" ~ m);
                }
                opPattern(context, sid + "spat", {
                            "entities" : qCreatedBy(sid + "cp", EntityType.BODY),
                            "transforms" : sxf,
                            "instanceNames" : snm
                        });
                opBoolean(context, sid + "cut", {
                            "tools" : qUnion([qCreatedBy(sid + "cp", EntityType.BODY),
                                        qCreatedBy(sid + "spat", EntityType.BODY)]),
                            "targets" : body,
                            "operationType" : BooleanOperationType.SUBTRACTION
                        });
            }
        }
        else if (definition.stage == RetStage.SLOTS)
        {
            for (var i = 0; i < 3; i += 1)
            {
                const cs = btnCS(IDX[i]);
                const vA = cross(cs.zAxis, cs.xAxis);
                // [수정] 오프셋 5.0 / 높이 10.0 이면 v=0 까지 뻗어 pad(3.6, +-1.8) 를 파고든다.
                // 오프셋 6.0 / 높이 8.0 -> v 구간 [2,10] 으로 pad 에서 0.2mm 이격된다.
                const org = IDX[i].p * millimeter + vA * (SLOT_SIGN[i] * 6.0 * millimeter);
                const scs = coordSystem(org, cs.xAxis, cs.zAxis);
                depthBox(context, id + ("s" ~ i), scs, SLOT_W, 8 * millimeter,
                    BLANK_FROM, BLANK_FROM + SLOT_D);
                opBoolean(context, id + ("sc" ~ i), {
                            "tools" : qCreatedBy(id + ("s" ~ i), EntityType.BODY),
                            "targets" : body,
                            "operationType" : BooleanOperationType.SUBTRACTION
                        });
            }
        }
    });
