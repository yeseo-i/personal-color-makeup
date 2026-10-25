"use strict";

// 사용자 추천 글 저장소. 지금은 localStorage를 쓴다.
// 다른 저장 방식으로 바꿀 때는 이 파일의 함수만 같은 반환 형식으로 다시 구현한다.
//   createPostId() -> 새 글의 고유 id
//   loadUserPosts() -> { ok: true, posts: [...], resaveError? } | { ok: false, posts: [], error }
//   saveUserPosts(posts) -> { ok: true } | { ok: false, error }
//   deleteUserPost(id) -> { ok: true, posts: [...] } | { ok: false, notFound: true, posts: [...] } | { ok: false, error }

const STORAGE_KEY = "personal-color-makeup.recommendations.v1";
const POST_SEASONS = ["spring_warm", "summer_cool", "autumn_warm", "winter_cool"];

function getLocalStorage() {
  // 브라우저 설정에 따라 localStorage에 접근하는 것만으로도 예외가 날 수 있다.
  const storage = window.localStorage;
  if (!storage) throw new Error("localStorage를 사용할 수 없습니다.");
  return storage;
}

function createPostId() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

// id는 검사하지 않는다. 없거나 겹치는 id는 불러올 때 새로 붙인다.
function isValidPost(post) {
  return post !== null && typeof post === "object" &&
    POST_SEASONS.includes(post.season) &&
    typeof post.nickname === "string" &&
    typeof post.product === "string" &&
    typeof post.reason === "string" &&
    typeof post.createdAt === "string";
}

function withUniqueIds(posts) {
  const seen = new Set();
  let changed = false;
  const result = posts.map((post) => {
    let next = post;
    if (typeof post.id !== "string" || post.id === "" || seen.has(post.id)) {
      next = { ...post, id: createPostId() };
      changed = true;
    }
    seen.add(next.id);
    return next;
  });
  return { posts: result, changed };
}

function loadUserPosts() {
  let posts;
  try {
    const raw = getLocalStorage().getItem(STORAGE_KEY);
    if (raw === null) return { ok: true, posts: [] };
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) throw new Error("저장된 값이 목록 형식이 아닙니다.");
    posts = parsed.filter(isValidPost);
  } catch (error) {
    return { ok: false, posts: [], error };
  }

  const fixed = withUniqueIds(posts);
  if (!fixed.changed) return { ok: true, posts: fixed.posts };
  const saved = saveUserPosts(fixed.posts);
  return saved.ok
    ? { ok: true, posts: fixed.posts }
    : { ok: true, posts: fixed.posts, resaveError: saved.error };
}

function saveUserPosts(posts) {
  try {
    getLocalStorage().setItem(STORAGE_KEY, JSON.stringify(posts));
    return { ok: true };
  } catch (error) {
    return { ok: false, error };
  }
}

// 저장소에서 다시 읽은 목록에서 지운다. 저장에 실패하면 아무것도 지우지 않은 것으로 본다.
function deleteUserPost(id) {
  const loaded = loadUserPosts();
  if (!loaded.ok) return { ok: false, error: loaded.error };
  if (!loaded.posts.some((post) => post.id === id)) {
    return { ok: false, notFound: true, posts: loaded.posts };
  }

  const remaining = loaded.posts.filter((post) => post.id !== id);
  const saved = saveUserPosts(remaining);
  if (!saved.ok) return { ok: false, error: saved.error };
  return { ok: true, posts: remaining };
}
