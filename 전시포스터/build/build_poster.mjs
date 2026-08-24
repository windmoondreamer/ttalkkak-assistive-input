import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const BUILD_DIR = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.resolve(BUILD_DIR, "..").replaceAll("\\", "/");
const PPTX_PATH = `${OUT_DIR}/OneGrip_Play_A1_전시포스터.pptx`;
const PREVIEW_PATH = `${OUT_DIR}/OneGrip_Play_A1_전시포스터_preview.png`;
const PRINT_PNG_PATH = `${OUT_DIR}/OneGrip_Play_A1_전시포스터_인쇄용.png`;
const LAYOUT_PATH = `${OUT_DIR}/OneGrip_Play_A1_전시포스터.layout.json`;

const ASSETS = {
  hero: `${OUT_DIR}/build/assets/V4_ISOMETRIC_no_title.png`,
  cutaway: `${OUT_DIR}/build/assets/V4_CUTAWAY_no_title.png`,
  fingers: `${OUT_DIR}/build/assets/01_final_cap_view_no_title.png`,
};

const C = {
  navy: "#172230",
  navy2: "#24384A",
  blue: "#52758B",
  blueLight: "#E8EEF1",
  page: "#F5F3EE",
  white: "#FFFFFF",
  ink: "#202832",
  muted: "#5F6973",
  border: "#CED3D5",
  orange: "#D9824B",
  orangeLight: "#F6E8DD",
  green: "#5D8372",
  greenLight: "#E5EEE9",
  red: "#B96B61",
  gray: "#E7E6E1",
};

const W = 2245;
const H = 3179;
const FONT = "Noto Sans KR";

async function bytes(path) {
  const b = await fs.readFile(path);
  return new Uint8Array(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));
}

function addRect(slide, x, y, w, h, fill, line = C.border, lineWidth = 2, radius = 12) {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: lineWidth },
    borderRadius: radius,
  });
}

function addText(slide, text, x, y, w, h, size, color = C.ink, bold = false, align = "left", vAlign = "top") {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = text;
  box.text.style = {
    fontSize: size,
    bold,
    color,
    typeface: FONT,
    alignment: align,
    verticalAlignment: vAlign,
    autoFit: "shrinkText",
    wrap: "square",
    insets: { top: 3, right: 5, bottom: 3, left: 5 },
  };
  return box;
}

function addSection(slide, x, y, w, h, title, accent = C.navy2, fill = C.white) {
  addRect(slide, x, y, w, h, fill, C.border, 2, 14);
  addRect(slide, x + 26, y + 23, 8, 45, accent, accent, 0, 4);
  addText(slide, title, x + 51, y + 19, w - 78, 52, 34, C.ink, true, "left", "middle");
  slide.shapes.add({
    geometry: "line",
    position: { left: x + 26, top: y + 79, width: w - 52, height: 0 },
    fill: "none",
    line: { style: "solid", fill: C.gray, width: 2 },
  });
}

function addImageFrame(slide, imageBytes, x, y, w, h, alt, crop = undefined, fit = "contain", dark = false) {
  addRect(slide, x, y, w, h, dark ? "#111B2B" : C.white, dark ? "#26374D" : C.border, 2, 12);
  return slide.images.add({
    blob: imageBytes,
    contentType: "image/png",
    alt,
    fit,
    crop,
    position: { left: x + 10, top: y + 10, width: w - 20, height: h - 20 },
    geometry: "roundRect",
    borderRadius: 8,
  });
}

function addFeatureRow(slide, n, title, body, x, y, w, color) {
  addText(slide, n, x, y, 88, 88, 52, color, true, "left", "middle");
  addText(slide, title, x + 92, y, w - 92, 48, 31, C.ink, true, "left", "middle");
  addText(slide, body, x + 92, y + 49, w - 92, 76, 25, C.muted, false, "left", "top");
  slide.shapes.add({
    geometry: "line",
    position: { left: x + 92, top: y + 129, width: w - 92, height: 0 },
    fill: "none",
    line: { style: "solid", fill: C.gray, width: 2 },
  });
}

function addUsageCard(slide, x, y, w, h, title, subtitle, kind, color) {
  addRect(slide, x, y, w, h, "#FAFAF7", C.border, 2, 10);
  addRect(slide, x + 22, y + 25, 84, 84, C.white, color, 2, 10);
  const line = { style: "solid", fill: color, width: 4 };
  const none = "none";
  if (kind === "pc") {
    slide.shapes.add({ geometry: "roundRect", position: { left: x + 40, top: y + 43, width: 48, height: 33 }, fill: none, line, borderRadius: 4 });
    slide.shapes.add({ geometry: "line", position: { left: x + 64, top: y + 76, width: 0, height: 13 }, fill: none, line });
    slide.shapes.add({ geometry: "line", position: { left: x + 51, top: y + 89, width: 26, height: 0 }, fill: none, line });
  } else if (kind === "switch") {
    slide.shapes.add({ geometry: "roundRect", position: { left: x + 36, top: y + 42, width: 56, height: 48 }, fill: none, line, borderRadius: 8 });
    slide.shapes.add({ geometry: "rect", position: { left: x + 51, top: y + 46, width: 26, height: 40 }, fill: none, line: { ...line, width: 3 } });
    slide.shapes.add({ geometry: "ellipse", position: { left: x + 41, top: y + 53, width: 6, height: 6 }, fill: color, line: { style: "solid", fill: color, width: 0 } });
    slide.shapes.add({ geometry: "ellipse", position: { left: x + 82, top: y + 72, width: 6, height: 6 }, fill: color, line: { style: "solid", fill: color, width: 0 } });
  } else if (kind === "web") {
    slide.shapes.add({ geometry: "ellipse", position: { left: x + 41, top: y + 43, width: 46, height: 46 }, fill: none, line });
    slide.shapes.add({ geometry: "line", position: { left: x + 64, top: y + 45, width: 0, height: 42 }, fill: none, line: { ...line, width: 3 } });
    slide.shapes.add({ geometry: "line", position: { left: x + 43, top: y + 66, width: 42, height: 0 }, fill: none, line: { ...line, width: 3 } });
  } else {
    slide.shapes.add({ geometry: "roundRect", position: { left: x + 38, top: y + 44, width: 52, height: 42 }, fill: none, line, borderRadius: 6 });
    slide.shapes.add({ geometry: "triangle", position: { left: x + 58, top: y + 54, width: 20, height: 22 }, fill: color, line: { style: "solid", fill: color, width: 0 } });
  }
  addText(slide, title, x + 124, y + 25, w - 144, 44, 26, C.ink, true, "left", "middle");
  addText(slide, subtitle, x + 124, y + 72, w - 144, 61, 21, C.muted, false, "left", "top");
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const [heroBytes, cutawayBytes, fingersBytes] = await Promise.all([
    bytes(ASSETS.hero), bytes(ASSETS.cutaway), bytes(ASSETS.fingers),
  ]);

  const deck = Presentation.create({ slideSize: { width: W, height: H } });
  const slide = deck.slides.add();
  slide.background.fill = C.page;

  // Header
  addRect(slide, 42, 42, 2161, 272, C.navy, C.navy, 0, 18);
  addRect(slide, 90, 77, 10, 150, C.orange, C.orange, 0, 4);
  addText(slide, "ONEGRIP PLAY", 124, 66, 1126, 104, 90, C.white, true, "left", "middle");
  addText(slide, "한 손 게임·미디어 통합 컨트롤러", 124, 166, 1470, 65, 40, "#E9EDF0", true, "left", "middle");
  addText(slide, "이동·시점·주요 액션을 한 손 안에서 분리해 동시에 조작", 124, 232, 1530, 42, 25, "#BFC9D1", false, "left", "middle");
  addText(slide, "ONE-HAND ACCESSIBLE INPUT", 1660, 88, 465, 48, 23, "#BEC8D0", true, "right", "middle");
  addText(slide, "GAME  ·  WEB  ·  MEDIA", 1660, 144, 465, 46, 27, C.orange, true, "right", "middle");
  slide.shapes.add({ geometry: "line", position: { left: 1668, top: 210, width: 450, height: 0 }, fill: "none", line: { style: "solid", fill: "#42515F", width: 2 } });
  addText(slide, "제7회 국립재활원 보조기기 해커톤", 1660, 222, 465, 40, 22, C.white, false, "right", "middle");

  // Overview
  addSection(slide, 60, 365, 795, 568, "대상 사용자와 아이디어 개요", C.orange);
  addRect(slide, 94, 458, 726, 126, C.orangeLight, C.orangeLight, 0, 8);
  addText(slide, "주 대상", 114, 474, 116, 31, 23, C.orange, true, "left", "middle");
  addText(slide,
    "편마비·상지 절단·기능 제한 또는 하반신 마비 등으로 침상·리클라이닝 자세에서 한 손 입력이 필요한 사용자",
    230, 463, 568, 104, 24, C.ink, true, "left", "middle");
  addText(slide,
    "양손 게임패드를 사용하기 어렵거나 침상·리클라이닝 자세로 활동하는 사용자는 이동·시점·버튼 입력을 동시에 수행하기 어렵고, 디지털 여가 활동의 선택지가 제한됩니다.",
    94, 600, 726, 104, 26, C.ink, false);
  addText(slide,
    "OneGrip Play는 사용 가능한 한 손의 손목·엄지·검지·중지 움직임을 분리해 양손 입력을 한 손 안에서 재구성합니다.",
    94, 716, 726, 82, 26, C.ink, true);
  addRect(slide, 94, 816, 726, 84, C.blueLight, C.blueLight, 0, 8);
  addText(slide, "활용 목표", 114, 832, 116, 30, 22, C.blue, true, "left", "middle");
  addText(slide, "PC 게임(LoL 등) · Nintendo Switch · 웹 서핑 · 유튜브·OTT", 230, 825, 568, 56, 23, C.navy2, true, "left", "middle");

  // Operating logic
  addSection(slide, 890, 365, 1295, 568, "한 손 안에서 세 가지 역할을 분리");
  const rows = [
    { y: 474, a: "손목·팔", b: "하단 2축 짐벌", c: "이동(PC 게임·Switch)\n메뉴 탐색(웹·미디어)", color: C.orange, light: C.orangeLight },
    { y: 613, a: "엄지", b: "소형 조이스틱", c: "시점(PC 게임·Switch)\n포인터·스크롤(웹·미디어)", color: C.blue, light: C.blueLight },
    { y: 752, a: "검지·중지", b: "8개 손가락 버튼", c: "주요 액션(PC 게임·Switch)\n클릭·재생(웹·미디어)", color: C.green, light: C.greenLight },
  ];
  // arrows first
  for (const r of rows) {
    slide.shapes.add({ geometry: "rightArrow", position: { left: 1235, top: r.y + 34, width: 92, height: 38 }, fill: r.color, line: { style: "solid", fill: r.color, width: 0 } });
    slide.shapes.add({ geometry: "rightArrow", position: { left: 1654, top: r.y + 34, width: 92, height: 38 }, fill: r.color, line: { style: "solid", fill: r.color, width: 0 } });
  }
  for (const r of rows) {
    addRect(slide, 940, r.y, 275, 104, C.white, r.color, 3, 12);
    addText(slide, r.a, 960, r.y + 18, 235, 68, 30, C.ink, true, "center", "middle");
    addRect(slide, 1345, r.y, 289, 104, "#F8FAFD", r.color, 3, 12);
    addText(slide, r.b, 1365, r.y + 18, 249, 68, 29, C.ink, true, "center", "middle");
    addRect(slide, 1765, r.y, 355, 104, r.light, r.color, 3, 12);
    addText(slide, r.c, 1785, r.y + 12, 315, 80, 24, C.ink, true, "center", "middle");
  }
  addText(slide, "PC 게임·Switch에서는 이동·시점·액션을, 웹·미디어에서는 메뉴 탐색·포인터·클릭/재생을 나눠 조작합니다.", 952, 875, 1150, 40, 24, C.muted, false, "center", "middle");

  // Hero and device structure
  addSection(slide, 60, 995, 1260, 1035, "제품 구조");
  addImageFrame(slide, heroBytes, 92, 1068, 1196, 780, "OneGrip Play 20-degree ergonomic housing and grip", { left: 0.03, top: 0, right: 0.03, bottom: 0.02 }, "contain", false);
  addRect(slide, 92, 1865, 1196, 118, C.navy2, C.navy2, 0, 8);
  addText(slide, "20° 팔받침 하우징  ·  ±15° 손목 기울임  ·  엄지 조이스틱  ·  손가락 버튼", 118, 1881, 1144, 82, 29, "#F4F5F3", true, "center", "middle");

  // Core features
  addSection(slide, 1350, 995, 835, 1035, "핵심 기능", C.orange);
  addFeatureRow(slide, "01", "이동과 포인터 조작을 분리", "손목·팔은 이동·메뉴 탐색을, 엄지는 시점·포인터·스크롤을 담당해 두 축계를 독립적으로 사용합니다.", 1394, 1085, 740, C.orange);
  addFeatureRow(slide, "02", "손가락 위치를 유지한 8버튼", "검지·중지가 그립을 놓지 않고 주요 액션과 클릭·재생 제어를 직접 입력하도록 배치했습니다.", 1394, 1305, 740, C.blue);
  addFeatureRow(slide, "03", "팔을 받치는 20° 인체공학 하우징", "손목만 버티지 않도록 팔 지지면을 넓히고, 하부 짐벌을 하우징 내부에 수용했습니다.", 1394, 1525, 740, C.green);
  addFeatureRow(slide, "04", "출력·조립·수리를 고려한 모듈화", "버튼 캐리어를 분리하고 하우징을 2분할해 FDM 출력과 내부 조립 순서를 함께 설계했습니다.", 1394, 1745, 740, C.red);

  // Implementation results
  addSection(slide, 60, 2080, 2125, 835, "구현 및 검증 결과", C.navy2);
  addImageFrame(slide, fingersBytes, 92, 2160, 600, 430, "Eight finger button exterior layout", { left: 0.21, top: 0, right: 0.21, bottom: 0.12 }, "cover", true);
  addText(slide, "손가락 입력부", 100, 2600, 585, 42, 29, C.ink, true, "center", "middle");
  addText(slide, "8개 버튼 간 비의도 간섭 0 mm³\n정격 행정 0.35 mm · 최소 벽 1.20 mm", 100, 2646, 585, 75, 23, C.muted, false, "center", "middle");

  addImageFrame(slide, cutawayBytes, 720, 2160, 600, 430, "Gimbal housing cutaway", { left: 0.02, top: 0, right: 0.02, bottom: 0.02 }, "contain", false);
  addText(slide, "하부 짐벌·하우징", 728, 2600, 585, 42, 29, C.ink, true, "center", "middle");
  addText(slide, "±15° 전 자세 간섭 0\n최초 접촉 15.88° · 검증 게이트 23/23 PASS", 728, 2646, 585, 75, 23, C.muted, false, "center", "middle");

  addRect(slide, 1350, 2160, 790, 560, "#FAFAF7", C.border, 2, 12);
  addText(slide, "활용 장면", 1382, 2183, 250, 42, 30, C.navy2, true, "left", "middle");
  addText(slide, "하나의 그립으로 게임과 일상 미디어 조작까지", 1625, 2186, 480, 36, 21, C.muted, false, "right", "middle");
  addUsageCard(slide, 1382, 2250, 348, 190, "PC 게임", "LoL 등 이동·시점·주요 액션", "pc", C.orange);
  addUsageCard(slide, 1750, 2250, 348, 190, "Nintendo Switch", "한 손 조작용 게임 입력", "switch", C.red);
  addUsageCard(slide, 1382, 2460, 348, 190, "웹 서핑", "포인터 이동·클릭·스크롤", "web", C.blue);
  addUsageCard(slide, 1750, 2460, 348, 190, "유튜브·OTT", "탐색·재생·볼륨 제어", "media", C.green);

  // Bottom message and team footer
  addRect(slide, 60, 2945, 2125, 92, C.blueLight, C.blueLight, 0, 12);
  addText(slide, "한 손 사용자의 게임 접근성을 높이되, 손가락을 새로 외우기보다 손의 자연스러운 역할 분담을 활용합니다.", 95, 2960, 2055, 62, 27, C.navy2, true, "center", "middle");
  addText(slide, "동국대학교 전자전기공학부  |  김민섭 · 윤홍민 · 장재원 · 김예진", 65, 3070, 1510, 50, 25, C.ink, true, "left", "middle");
  addText(slide, "ONEGRIP PLAY", 1675, 3070, 500, 50, 28, C.navy2, true, "right", "middle");

  slide.speakerNotes.textFrame.setText(
    "[Sources]\n" +
    `- ${OUT_DIR}/../README.md\n` +
    `- ${OUT_DIR}/../cad/source_snapshot/team_claude_latest/README.md\n` +
    `- ${OUT_DIR}/../cad/onegrip-index-middle-cassette-v2/README.md\n` +
    `- ${OUT_DIR}/../cad/onegrip-full-module-v3/README.md\n` +
    `- ${ASSETS.hero}\n- ${ASSETS.cutaway}\n- ${ASSETS.fingers}\n`
  );

  const preview = await deck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(PREVIEW_PATH, new Uint8Array(await preview.arrayBuffer()));
  const printPng = await deck.export({ slide, format: "png", scale: 3 });
  await fs.writeFile(PRINT_PNG_PATH, new Uint8Array(await printPng.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(LAYOUT_PATH, await layout.text(), "utf8");
  const pptx = await PresentationFile.exportPptx(deck);
  await pptx.save(PPTX_PATH);

  const inspection = await deck.inspect({ kind: "slide,textbox,shape,image", maxChars: 12000 });
  await fs.writeFile(`${OUT_DIR}/OneGrip_Play_A1_전시포스터.inspect.ndjson`, inspection.ndjson, "utf8");
  console.log(JSON.stringify({ pptx: PPTX_PATH, preview: PREVIEW_PATH, printPng: PRINT_PNG_PATH, layout: LAYOUT_PATH }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
