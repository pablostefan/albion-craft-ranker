"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

const STORAGE_KEY = "albion-craft-favorites";

/* ── External store for cross-component sync ── */

let listeners: Array<() => void> = [];
function emitChange() {
  for (const listener of listeners) listener();
}
function subscribe(listener: () => void) {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}
function getSnapshot(): string {
  return localStorage.getItem(STORAGE_KEY) ?? "[]";
}
function getServerSnapshot(): string {
  return "[]";
}

function setStored(ids: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  emitChange();
}

/* ── Hook ── */

export function useFavorites() {
  const raw = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const favorites = new Set<string>(JSON.parse(raw) as string[]);

  const isFavorite = useCallback(
    (id: string) => favorites.has(id),
    [raw],               // eslint-disable-line react-hooks/exhaustive-deps
  );

  const toggleFavorite = useCallback((id: string) => {
    const current: string[] = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    const next = current.includes(id)
      ? current.filter((x) => x !== id)
      : [...current, id];
    setStored(next);
  }, []);

  const clearFavorites = useCallback(() => {
    setStored([]);
  }, []);

  return { favorites, isFavorite, toggleFavorite, clearFavorites } as const;
}
