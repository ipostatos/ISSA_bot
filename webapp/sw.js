// Service worker Mini App — офлайн-режим (Этап 4 «PWA/offline»).
//
// Прогрессивное улучшение: в iOS-клиенте Telegram (WKWebView) service worker
// недоступен — там приложение работает как раньше, по сети. В Android-клиенте
// и обычных браузерах после первого визита страницы и данные доступны офлайн.
//
// Стратегии (важно для корректности после деплоя):
//   • страницы и код (.html/.js/.css/.json) — NETWORK-FIRST с таймаутом:
//     онлайн всегда отдаём свежую версию (никакого «залипшего» кода после
//     деплоя), кэш используется только как фолбэк без сети;
//   • картинки и vendor-библиотеки — STALE-WHILE-REVALIDATE: отдаём из кэша
//     мгновенно, в фоне обновляем (меняются редко);
//   • НЕ кэшируем: /api/* (живой прогресс/синхрон), PDF-книги (десятки МБ,
//     range-запросы pdf.js), внешние тайлы карт и Open-Meteo (живые данные).
"use strict";

var CACHE = "issa-static-v2"; // bump при смене формата кэша — старые удаляются в activate (v2: чистка клиентов со старыми icons.js/i18n.dict.js после релиза камер)

var NET_TIMEOUT_MS = 4000; // на плохой сети не ждём вечно — падаем в кэш

self.addEventListener("install", function () {
  // Без precache-списка: наполняем кэш по мере использования (runtime caching).
  // Так нет риска, что список отстанет от реального набора файлов.
  self.skipWaiting();
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

// Кладём в кэш только полноценные ответы (200) и opaque (no-cors скрипт
// telegram.org) — ошибки и редиректы не запоминаем.
function putIfCacheable(req, res) {
  if (!res || (res.status !== 200 && res.type !== "opaque")) return res;
  var copy = res.clone();
  caches.open(CACHE).then(function (c) { c.put(req, copy); }).catch(function () {});
  return res;
}

function fetchWithTimeout(req) {
  if (typeof AbortController === "undefined") return fetch(req);
  var ctrl = new AbortController();
  var t = setTimeout(function () { ctrl.abort(); }, NET_TIMEOUT_MS);
  return fetch(req, { signal: ctrl.signal }).finally(function () { clearTimeout(t); });
}

// Сеть → кэш. Для навигаций последний фолбэк — закэшированная главная,
// чтобы офлайн-запуск не упирался в белый экран.
function networkFirst(req, isNavigate) {
  return fetchWithTimeout(req)
    .then(function (res) { return putIfCacheable(req, res); })
    .catch(function () {
      return caches.match(req, { ignoreSearch: true }).then(function (hit) {
        if (hit) return hit;
        if (isNavigate) return caches.match("index.html", { ignoreSearch: true });
        return Promise.reject(new Error("offline: " + req.url));
      });
    });
}

// Кэш сразу, обновление в фоне.
function staleWhileRevalidate(req) {
  return caches.match(req, { ignoreSearch: true }).then(function (hit) {
    var refresh = fetch(req)
      .then(function (res) { return putIfCacheable(req, res); })
      .catch(function () { return hit; });
    return hit || refresh;
  });
}

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  if (req.headers.has("range")) return; // pdf.js читает книги кусками — мимо кэша

  var url;
  try { url = new URL(req.url); } catch (err) { return; }

  if (url.origin === self.location.origin) {
    var p = url.pathname;
    if (p.indexOf("/api/") !== -1) return;      // живые данные — только сеть
    if (p.slice(-4) === ".pdf") return;         // книги не кэшируем (объём)
    if (p.slice(-4) === ".mp3") return;         // нейроозвучка: десятки МБ, мимо кэша
    if (p.indexOf("/images/") !== -1 || p.indexOf("/vendor/") !== -1 ||
        p.slice(-4) === ".svg" || p.slice(-4) === ".png" || p.slice(-4) === ".jpg") {
      e.respondWith(staleWhileRevalidate(req));
      return;
    }
    // страницы, скрипты, стили, манифест, данные
    e.respondWith(networkFirst(req, req.mode === "navigate"));
    return;
  }

  // Единственный внешний ресурс, без которого Mini App не стартует.
  if (url.hostname === "telegram.org" && url.pathname.indexOf("telegram-web-app") !== -1) {
    e.respondWith(staleWhileRevalidate(req));
  }
  // Остальное внешнее (тайлы CARTO, Open-Meteo, донат-ссылки) — не трогаем.
});
