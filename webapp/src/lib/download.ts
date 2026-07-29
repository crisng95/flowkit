// Trigger a browser download of a same-origin file with a chosen filename.
// (Media is served by the agent at /media/… so it's same-origin and `download` is honoured;
// a cross-origin href would silently open the file in a tab instead of saving it.)
export function downloadFile(url: string, filename: string) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// Filesystem-safe slug for a generated filename.
export const slugName = (s: string, fallback = "shot") =>
  (s || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[\\/:*?"<>|\r\n\t]+/g, "")
    .replace(/-{2,}/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60) || fallback;

export const pad3 = (n: number) => String(n + 1).padStart(3, "0");
