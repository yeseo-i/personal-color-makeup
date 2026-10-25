"use strict";

// 사용자 추천 글 저장소. 지금은 localStorage를 쓴다.
// 다른 저장 방식으로 바꿀 때는 이 파일의 함수만 같은 반환 형식으로 다시 구현한다.
//   loadUserPosts() -> { ok: true, posts: [...] } | { ok: false, posts: [], error }
//   saveUserPosts(posts) -> { ok: true } | { ok: false, error }

const STORAGE_KEY = "personal-color-makeup.recommendations.v1";
const POST_SEASONS = ["spring_warm", "summer_cool", "autumn_warm", "winter_cool"];

function getLocalStorage() {
  // 브라우저 설정에 따라 localStorage에 접근하는 것만으로도 예외가 날 수 있다.
  const storage = window.localStorage;
  if (!storage) throw new Error("localStorage를 사용할 수 없습니다.");
  return storage;
}

function isValidPost(post) {
  return post !== null && typeof post === "object" &&
    typeof post.id === "string" &&
    POST_SEASONS.includes(post.season) &&
    typeof post.nickname === "string" &&
    typeof post.product === "string" &&
    typeof post.reason === "string" &&
    typeof post.createdAt === "string";
}

function loadUserPosts() {
  try {
    const raw = getLocalStorage().getItem(STORAGE_KEY);
    if (raw === null) return { ok: true, posts: [] };
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) throw new Error("저장된 값이 목록 형식이 아닙니다.");
    return { ok: true, posts: parsed.filter(isValidPost) };
  } catch (error) {
    return { ok: false, posts: [], error };
  }
}

function saveUserPosts(posts) {
  try {
    getLocalStorage().setItem(STORAGE_KEY, JSON.stringify(posts));
    return { ok: true };
  } catch (error) {
    return { ok: false, error };
  }
}
