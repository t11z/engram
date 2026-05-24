import { goto } from "$app/navigation";

export type View = "list" | "search" | "trash";

const VIEWS: View[] = ["list", "search", "trash"];

export interface NavState {
  view: View;
  note: string | null;
  q: string;
  tag: string | null;
}

export function parse(url: URL): NavState {
  const raw = url.searchParams.get("view");
  const view = VIEWS.includes(raw as View) ? (raw as View) : "list";
  return {
    view,
    note: url.searchParams.get("note"),
    q: url.searchParams.get("q") ?? "",
    tag: url.searchParams.get("tag"),
  };
}

export function navTo(patch: Record<string, string | null>): void {
  const params = new URLSearchParams(window.location.search);
  for (const [key, value] of Object.entries(patch)) {
    if (value === null || value === "") params.delete(key);
    else params.set(key, value);
  }
  const query = params.toString();
  void goto(query ? `/?${query}` : "/", { keepFocus: true, noScroll: true });
}
