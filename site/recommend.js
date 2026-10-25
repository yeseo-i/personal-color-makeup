"use strict";

const SEASON_LABELS = {
  spring_warm: "봄 웜",
  summer_cool: "여름 쿨",
  autumn_warm: "가을 웜",
  winter_cool: "겨울 쿨",
};

const LIMITS = {
  nickname: 20,
  product: 50,
  reason: 300,
};

const FIELD_LABELS = {
  season: "유형",
  nickname: "닉네임",
  product: "화장품 이름",
  reason: "추천 이유",
};

// 화면 구성을 보여 주기 위한 예시 글. localStorage에 저장하지 않는다.
const EXAMPLE_POSTS = [
  { season: "spring_warm", product: "코랄 계열 립스틱", reason: "예시 글입니다. 밝고 따뜻한 코랄 색을 추천하는 글이 이런 식으로 표시됩니다." },
  { season: "spring_warm", product: "피치 계열 블러셔", reason: "예시 글입니다. 복숭아빛 블러셔를 추천하는 이유를 적는 자리입니다." },
  { season: "summer_cool", product: "로즈 핑크 립스틱", reason: "예시 글입니다. 부드러운 로즈 핑크 색을 추천하는 글이 이런 식으로 표시됩니다." },
  { season: "summer_cool", product: "라벤더 계열 아이섀도", reason: "예시 글입니다. 차분한 라벤더 색 아이섀도를 추천하는 이유를 적는 자리입니다." },
  { season: "autumn_warm", product: "브릭 레드 립스틱", reason: "예시 글입니다. 깊고 따뜻한 벽돌색을 추천하는 글이 이런 식으로 표시됩니다." },
  { season: "autumn_warm", product: "브라운 계열 아이섀도", reason: "예시 글입니다. 차분한 브라운 아이섀도를 추천하는 이유를 적는 자리입니다." },
  { season: "winter_cool", product: "버건디 립스틱", reason: "예시 글입니다. 선명하고 차가운 버건디 색을 추천하는 글이 이런 식으로 표시됩니다." },
  { season: "winter_cool", product: "푸시아 핑크 블러셔", reason: "예시 글입니다. 쨍한 푸시아 핑크 블러셔를 추천하는 이유를 적는 자리입니다." },
].map((post) => ({ ...post, nickname: "예시", isExample: true }));

const state = {
  userPosts: [],
  season: null,
  // 불러오기에 실패하면 저장된 값을 덮어쓰지 않도록 저장도 하지 않는다.
  storageReady: false,
};

const el = {
  storageStatus: document.getElementById("storage-status"),
  form: document.getElementById("post-form"),
  formStatus: document.getElementById("form-status"),
  fields: {
    season: document.getElementById("post-season"),
    nickname: document.getElementById("post-nickname"),
    product: document.getElementById("post-product"),
    reason: document.getElementById("post-reason"),
  },
  message: document.getElementById("message"),
  seasonHeader: document.getElementById("season-header"),
  seasonTitle: document.getElementById("season-title"),
  resultCount: document.getElementById("result-count"),
  listStatus: document.getElementById("list-status"),
  list: document.getElementById("post-list"),
  seasonButtons: document.querySelectorAll(".season-btn"),
};

function showStatus(node, message, kind) {
  node.textContent = message;
  node.className = `status status-${kind}`;
  node.hidden = false;
}

function hideStatus(node) {
  node.hidden = true;
  node.textContent = "";
}

function formatDate(iso) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleDateString("ko-KR");
}

function addText(parent, tag, className, value) {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = value;
  parent.appendChild(node);
  return node;
}

// 사용자가 입력한 값은 모두 textContent로만 넣는다.
function renderPost(post) {
  const li = document.createElement("li");
  li.className = post.isExample ? "post-card is-example" : "post-card";

  const meta = document.createElement("p");
  meta.className = "post-meta";
  if (post.isExample) addText(meta, "span", "badge", "예시");
  addText(meta, "span", "post-author", post.nickname);
  if (!post.isExample) {
    const date = formatDate(post.createdAt);
    if (date) addText(meta, "span", "post-date", date);
  }
  li.appendChild(meta);

  addText(li, "p", "product-name", post.product);
  addText(li, "p", "post-reason", post.reason);

  if (!post.isExample) {
    const actions = document.createElement("div");
    actions.className = "post-actions";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "delete-btn";
    button.textContent = "삭제";
    button.setAttribute("aria-label", `${post.product} 글 삭제`);
    if (state.storageReady) {
      button.addEventListener("click", () => handleDelete(post.id));
    } else {
      button.disabled = true;
      button.title = "저장된 글을 불러오지 못해 삭제할 수 없습니다.";
    }
    actions.appendChild(button);
    li.appendChild(actions);
  }
  return li;
}

function setPressed(season) {
  for (const button of el.seasonButtons) {
    button.setAttribute("aria-pressed", String(button.dataset.season === season));
  }
}

function render() {
  setPressed(state.season);
  hideStatus(el.listStatus);
  el.list.replaceChildren();

  if (!state.season) {
    el.seasonHeader.hidden = true;
    el.message.hidden = false;
    return;
  }

  // 사용자 글을 최신순으로 먼저, 예시 글을 뒤에 둔다.
  const userPosts = state.userPosts
    .filter((post) => post.season === state.season)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const examples = EXAMPLE_POSTS.filter((post) => post.season === state.season);

  el.seasonHeader.hidden = false;
  el.seasonTitle.textContent = SEASON_LABELS[state.season];
  el.resultCount.textContent = `작성한 글 ${userPosts.length}개 · 예시 ${examples.length}개`;
  el.message.hidden = true;

  const fragment = document.createDocumentFragment();
  for (const post of [...userPosts, ...examples]) fragment.appendChild(renderPost(post));
  el.list.appendChild(fragment);
}

function updateCounter(name) {
  const input = el.fields[name];
  const counter = document.getElementById(input.dataset.counter);
  const remaining = LIMITS[name] - input.value.length;
  counter.textContent = `${remaining}자 남음 (최대 ${LIMITS[name]}자)`;
}

function readForm() {
  const values = {};
  for (const name of Object.keys(el.fields)) values[name] = el.fields[name].value.trim();
  return values;
}

function validate(values) {
  const empty = Object.keys(el.fields).filter((name) => values[name] === "");
  const tooLong = Object.keys(LIMITS).filter((name) => values[name].length > LIMITS[name]);
  for (const name of Object.keys(el.fields)) {
    el.fields[name].setAttribute("aria-invalid", String(empty.includes(name) || tooLong.includes(name)));
  }

  const problems = [];
  if (empty.length > 0) {
    problems.push(`비어 있는 칸이 있습니다: ${empty.map((name) => FIELD_LABELS[name]).join(", ")}`);
  }
  if (tooLong.length > 0) {
    problems.push(`글자 수를 넘었습니다: ${tooLong.map((name) => `${FIELD_LABELS[name]}(최대 ${LIMITS[name]}자)`).join(", ")}`);
  }
  return { problems, firstInvalid: [...empty, ...tooLong][0] };
}

function handleSubmit(event) {
  event.preventDefault();
  const values = readForm();
  const { problems, firstInvalid } = validate(values);
  if (problems.length > 0) {
    showStatus(el.formStatus, problems.join(" / "), "error");
    el.fields[firstInvalid].focus();
    return;
  }

  const post = { id: createPostId(), ...values, createdAt: new Date().toISOString() };
  const nextPosts = [...state.userPosts, post];
  const result = state.storageReady ? saveUserPosts(nextPosts) : { ok: false };
  state.userPosts = nextPosts;

  if (result.ok) {
    showStatus(el.formStatus, "등록했습니다.", "ok");
  } else {
    if (result.error) console.error(result.error);
    showStatus(el.formStatus,
      "글을 화면에는 추가했지만 브라우저에 저장하지 못했습니다. 새로고침하면 사라집니다.", "error");
  }

  el.fields.nickname.value = values.nickname;
  el.fields.product.value = "";
  el.fields.reason.value = "";
  for (const name of Object.keys(LIMITS)) updateCounter(name);

  state.season = post.season;
  render();
}

function handleDelete(id) {
  if (!state.storageReady) return;
  if (!window.confirm("이 글을 삭제할까요?")) return;

  const result = deleteUserPost(id);
  if (result.ok) {
    state.userPosts = result.posts;
    render();
    showStatus(el.listStatus, "삭제했습니다.", "ok");
  } else if (result.notFound) {
    state.userPosts = result.posts;
    render();
    showStatus(el.listStatus, "이미 삭제되었거나 찾을 수 없는 글입니다. 목록을 다시 불러왔습니다.", "error");
  } else {
    console.error(result.error);
    showStatus(el.listStatus, "삭제하지 못했습니다. 브라우저에 저장하는 중 문제가 생겨 글을 그대로 두었습니다.", "error");
  }
}

function bindControls() {
  for (const button of el.seasonButtons) {
    button.addEventListener("click", () => {
      state.season = button.dataset.season;
      render();
    });
  }
  for (const name of Object.keys(LIMITS)) {
    el.fields[name].maxLength = LIMITS[name];
    el.fields[name].addEventListener("input", () => updateCounter(name));
    updateCounter(name);
  }
  for (const input of Object.values(el.fields)) {
    input.addEventListener("input", () => input.removeAttribute("aria-invalid"));
  }
  el.form.addEventListener("input", () => hideStatus(el.formStatus));
  el.form.addEventListener("submit", handleSubmit);
}

function init() {
  bindControls();
  const result = loadUserPosts();
  state.storageReady = result.ok;
  if (result.ok) {
    state.userPosts = result.posts;
    if (result.resaveError) {
      console.error(result.resaveError);
      showStatus(el.storageStatus,
        "기존 글에 구분용 id를 붙였지만 브라우저에 저장하지 못했습니다. 새로고침하면 다시 시도합니다.", "error");
    }
  } else {
    console.error(result.error);
    showStatus(el.storageStatus,
      "저장된 글을 불러오지 못했습니다. 예시 글만 표시합니다. 새로 쓰는 글은 저장되지 않습니다.", "error");
  }
  render();
}

init();
