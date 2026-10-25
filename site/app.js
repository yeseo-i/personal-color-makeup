"use strict";

const DATA_URL = "../data/products.json";
const PLACEHOLDER_IMAGE = "placeholder.svg";

// clean_products.py가 빈 값 대신 넣는 문자열
const NO_BRAND = "브랜드 정보 없음";
const NO_SHADE_NAME = "이름 없음";

const SEASON_LABELS = {
  spring_warm: "봄 웜",
  summer_cool: "여름 쿨",
  autumn_warm: "가을 웜",
  winter_cool: "겨울 쿨",
};

const TYPE_LABELS = {
  lipstick: "립스틱",
  blush: "블러셔",
  eyeshadow: "아이섀도",
};

const HEX_PATTERN = /^#[0-9A-Fa-f]{6}$/;

const SEASON_ORDER = ["spring_warm", "summer_cool", "autumn_warm", "winter_cool"];
const CARD_SWATCHES = 5;

const state = {
  shades: [],
  season: null,
  type: "all",
};

const el = {
  message: document.getElementById("message"),
  seasonHeader: document.getElementById("season-header"),
  seasonTitle: document.getElementById("season-title"),
  resultCount: document.getElementById("result-count"),
  overview: document.getElementById("season-overview"),
  list: document.getElementById("shade-list"),
  seasonButtons: document.querySelectorAll(".season-btn"),
  typeButtons: document.querySelectorAll(".type-btn"),
};

function text(value, fallback) {
  if (typeof value !== "string") return fallback;
  const trimmed = value.trim();
  return trimmed === "" ? fallback : trimmed;
}

// 제품 목록을 셰이드 단위로 펼친다. 데이터 값은 바꾸지 않는다.
function flatten(products) {
  const shades = [];
  for (const product of products) {
    for (const shade of product.shades || []) {
      shades.push({ product, shade });
    }
  }
  return shades;
}

function useFallbackImage(img) {
  img.onerror = null;
  img.src = PLACEHOLDER_IMAGE;
  img.alt = "제품 이미지를 불러오지 못함";
}

function addField(parent, tag, className, value, fallback) {
  const node = document.createElement(tag);
  node.className = className;
  const shown = text(value, fallback);
  node.textContent = shown;
  if (shown === fallback) node.classList.add("placeholder-text");
  parent.appendChild(node);
  return node;
}

function renderCard({ product, shade }) {
  const li = document.createElement("li");
  li.className = "shade-card";

  const productName = text(product.name, "제품명 없음");
  const img = document.createElement("img");
  img.loading = "lazy";
  img.decoding = "async";
  img.width = 200;
  img.height = 200;
  img.alt = productName;
  img.onerror = () => useFallbackImage(img);
  img.src = text(product.image_link, PLACEHOLDER_IMAGE);
  li.appendChild(img);

  const body = document.createElement("div");
  body.className = "shade-body";
  addField(body, "p", "product-name", product.name, "제품명 없음");
  const brand = addField(body, "p", "brand", product.brand, NO_BRAND);
  const typeLabel = TYPE_LABELS[product.product_type];
  if (typeLabel) brand.textContent += ` · ${typeLabel}`;

  const row = document.createElement("div");
  row.className = "shade-row";
  const chip = document.createElement("span");
  chip.className = "chip";
  const hex = HEX_PATTERN.test(shade.hex_value) ? shade.hex_value : null;
  if (hex) chip.style.backgroundColor = hex;
  chip.setAttribute("aria-hidden", "true");
  row.appendChild(chip);

  const names = document.createElement("div");
  addField(names, "p", "shade-name", shade.colour_name, NO_SHADE_NAME);
  addField(names, "p", "hex", hex, "색상값 없음");
  row.appendChild(names);
  body.appendChild(row);

  li.appendChild(body);
  return li;
}

// 계절의 대표 색을 고정된 방식으로 고른다. 실제 셰이드 hex의 중복을 빼고
// 명도(lab_l), hex 순으로 정렬한 뒤 같은 간격 위치에서 count개를 뽑는다.
function sampleSeasonHexes(season, count) {
  const lightnessByHex = new Map();
  for (const { shade } of state.shades) {
    if (shade.season !== season || !HEX_PATTERN.test(shade.hex_value)) continue;
    const hex = shade.hex_value.toUpperCase();
    if (!lightnessByHex.has(hex)) lightnessByHex.set(hex, shade.lab_l);
  }
  const sorted = [...lightnessByHex].sort((a, b) =>
    a[1] - b[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  if (sorted.length === 0) return [];

  const picks = [];
  for (let i = 0; i < count; i++) {
    picks.push(sorted[Math.floor(((i + 1) * (sorted.length - 1)) / (count + 1))][0]);
  }
  return [...new Set(picks)];
}

function makeSwatches(hexes) {
  const wrap = document.createElement("span");
  wrap.className = "swatches";
  wrap.setAttribute("aria-hidden", "true");
  for (const hex of hexes) {
    const dot = document.createElement("span");
    dot.className = "dot";
    dot.style.backgroundColor = hex;
    wrap.appendChild(dot);
  }
  return wrap;
}

function selectSeason(season) {
  state.season = season;
  render();
}

function buildOverview() {
  const fragment = document.createDocumentFragment();
  for (const season of SEASON_ORDER) {
    const count = state.shades.filter(({ shade }) => shade.season === season).length;
    const li = document.createElement("li");
    const card = document.createElement("button");
    card.type = "button";
    card.className = "season-card";
    const name = document.createElement("span");
    name.className = "season-card-name";
    name.textContent = SEASON_LABELS[season];
    const countText = document.createElement("span");
    countText.className = "season-card-count";
    countText.textContent = `셰이드 ${count.toLocaleString("ko-KR")}개`;
    card.append(name, countText, makeSwatches(sampleSeasonHexes(season, CARD_SWATCHES)));
    card.addEventListener("click", () => selectSeason(season));
    li.appendChild(card);
    fragment.appendChild(li);
  }
  el.overview.replaceChildren(fragment);
}

function setPressed(buttons, attr, value) {
  for (const button of buttons) {
    button.setAttribute("aria-pressed", String(button.dataset[attr] === value));
  }
}

function render() {
  setPressed(el.seasonButtons, "season", state.season);
  setPressed(el.typeButtons, "type", state.type);
  el.list.replaceChildren();

  if (!state.season) {
    el.seasonHeader.hidden = true;
    el.message.hidden = false;
    el.overview.hidden = false;
    return;
  }
  el.overview.hidden = true;

  const matches = state.shades.filter(({ product, shade }) =>
    shade.season === state.season &&
    (state.type === "all" || product.product_type === state.type));

  el.seasonHeader.hidden = false;
  el.seasonTitle.textContent = SEASON_LABELS[state.season];
  const typeText = state.type === "all" ? "전체 제품군" : TYPE_LABELS[state.type];
  el.resultCount.textContent = `${typeText} · 셰이드 ${matches.length.toLocaleString("ko-KR")}개`;

  if (matches.length === 0) {
    el.message.textContent = "조건에 맞는 셰이드가 없습니다.";
    el.message.hidden = false;
    return;
  }
  el.message.hidden = true;

  const fragment = document.createDocumentFragment();
  for (const item of matches) fragment.appendChild(renderCard(item));
  el.list.appendChild(fragment);
}

function bindControls() {
  for (const button of el.seasonButtons) {
    button.addEventListener("click", () => selectSeason(button.dataset.season));
  }
  for (const button of el.typeButtons) {
    button.addEventListener("click", () => {
      state.type = button.dataset.type;
      render();
    });
  }
}

async function init() {
  bindControls();
  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.shades = flatten(await response.json());
    buildOverview();
    render();
  } catch (error) {
    console.error(error);
    el.message.textContent =
      "데이터를 불러오지 못했습니다. 저장소 루트에서 로컬 서버를 실행한 뒤 /site/ 주소로 열어 주세요.";
    for (const button of [...el.seasonButtons, ...el.typeButtons]) button.disabled = true;
  }
}

init();
