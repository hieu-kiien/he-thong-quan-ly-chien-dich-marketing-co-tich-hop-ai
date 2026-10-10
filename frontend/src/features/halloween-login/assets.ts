/**
 * Tải tài nguyên cảnh Halloween.
 *
 * Bản gốc là trang HTML tĩnh, script nạp ảnh SVG/dữ liệu JSON bằng fetch qua
 * biến toàn cục `pageResources`. Bản này tách ra một module để React dùng lại,
 * mọi đường dẫn trỏ vào `public/halloween/` (vẫn phục vụ tĩnh như cũ).
 */

const BASE = '/halloween/';

export function assetUrl(path: string): string {
  return BASE + path.replace(/^\/+/, '');
}

async function loadText(path: string): Promise<string> {
  const response = await fetch(assetUrl(path));
  if (!response.ok) throw new Error(`Không tải được tài nguyên: ${path}`);
  return response.text();
}

async function loadJson<T>(path: string): Promise<T> {
  return JSON.parse(await loadText(path)) as T;
}

/** Nạp font + mặt nạ ánh sáng, giống phần khởi tạo của resources.js gốc. */
export async function prepareAssets(): Promise<void> {
  const style = document.documentElement.style;
  style.setProperty('--sky-mask', `url("${assetUrl('images/sky-mask.svg')}")`);
  style.setProperty('--beam-mask', `url("${assetUrl('images/beam-mask.svg')}")`);
  const font = new FontFace(
    'Grenze Gotisch',
    `url("${assetUrl('fonts/GrenzeGotisch.ttf')}")`,
    { weight: '100 900', style: 'normal', display: 'swap' },
  );
  document.fonts.add(font);
  await font.load().catch((error: unknown) => {
    console.warn('Không tải được font hoặc mặt nạ:', (error as Error)?.message ?? error);
  });
}

/** Thay các phần tử `[data-svg]` bằng SVG nội tuyến. */
export async function inlineSvgPlaceholders(root: ParentNode): Promise<void> {
  const placeholders = Array.from(root.querySelectorAll<HTMLElement>('[data-svg]'));
  const sources = new Map<string, Promise<string>>();
  await Promise.all(
    placeholders.map(async (placeholder) => {
      const path = placeholder.dataset.svg;
      if (!path) return;
      if (!sources.has(path)) sources.set(path, loadText(path));
      const source = await sources.get(path)!;
      const artwork = new DOMParser().parseFromString(source, 'image/svg+xml');
      placeholder.replaceWith(document.importNode(artwork.documentElement, true));
    }),
  );
}

export const resources = {
  text: loadText,
  json: loadJson,
};
