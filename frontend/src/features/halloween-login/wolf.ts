/**
 * Sói trên đỉnh: 60 khung PNG gốc đã chuyển WebP (1,42 MB → 0,47 MB) và nằm
 * trong `public/halloween/wolf-transparent/`. Chuyển thể từ `wolf.js`.
 *
 * Sói xuất hiện khi `<body>` có class `night`, rút đi khi bỏ night có hiệu ứng
 * chạy ngược, và hú khi đèn pin chiếu vào.
 */

import { resources } from './assets';

type Cleanup = () => void;

interface Keyframe {
  x: number;
  y: number;
  opacity: number;
  lean: number;
}

const SVG_NS = 'http://www.w3.org/2000/svg';
const sources = Array.from({ length: 60 }, (_, i) => `images/wolf-transparent/frame-${String(i).padStart(2, '0')}.webp`);

const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export function startWolf(): Cleanup {
  const stageElement = document.querySelector<HTMLElement>('.summit-stage');
  if (!stageElement) return () => {};
  const stage: HTMLElement = stageElement;

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let ready = false;
  let active = false;
  let departing = false;
  let returnTime = 0;
  let frameId = 0;
  let elapsed = 0;
  let previous = 0;
  let lastFrame = -1;
  let routeFrames: Keyframe[] = [];
  let fps = 30;
  let routeGroup: SVGGElement;
  let bodyPose: SVGGElement;
  let frameImage: SVGImageElement;
  let howlActive = false;
  let howlFrame = 59;
  let howlPhase: 'lowering' | 'raising' | 'holding' = 'lowering';
  let holdTime = 0;
  let frameDelta = 0;
  let cancelled = false;

  function paint(seconds: number): void {
    const position = Math.min(routeFrames.length - 1, seconds * fps);
    const index = Math.floor(position);
    const a = routeFrames[index];
    const b = routeFrames[Math.min(index + 1, routeFrames.length - 1)];
    const blend = position - index;
    const value = (key: keyof Keyframe): number => lerp(a[key], b[key], blend);
    const idle = seconds > 5.8 && !reduced.matches ? Math.sin((seconds - 5.8) * 2.1) * 0.005 : 0;
    routeGroup.setAttribute('transform', `translate(${value('x')} ${value('y')}) scale(.86)`);
    routeGroup.setAttribute('opacity', String(value('opacity')));
    bodyPose.setAttribute('transform', `rotate(${value('lean')}) scale(1 ${1 + idle})`);
    let frame: number;
    if (seconds < 3.8) frame = Math.min(38, Math.floor(((Math.max(0, seconds - 0.7) / 3.1) * 39)));
    else if (seconds < 4.4) frame = Math.min(47, 39 + Math.floor(((seconds - 3.8) / 0.6) * 9));
    else frame = Math.min(59, 48 + Math.floor(((seconds - 4.4) / 1.4) * 12));
    const lit = !departing && stage.classList.contains('is-beam-lit');
    if (!departing && seconds >= 5.8 && !reduced.matches && (lit || howlActive)) {
      howlActive = true;
      if (!lit) howlPhase = 'lowering';
      if (howlPhase === 'lowering') {
        howlFrame = Math.max(47, howlFrame - frameDelta * 10);
        if (howlFrame === 47 && lit) howlPhase = 'raising';
      } else if (howlPhase === 'raising') {
        howlFrame = Math.min(59, howlFrame + frameDelta * 10);
        if (howlFrame === 59) {
          howlPhase = 'holding';
          holdTime = 0;
        }
      } else {
        holdTime += frameDelta;
        if (holdTime >= 0.85) howlPhase = 'lowering';
      }
      frame = Math.round(howlFrame);
    }
    if (departing && seconds < 3.8) frame = Math.floor(returnTime * 14) % 18;
    frameImage.setAttribute('transform', departing && seconds < 3.8 ? 'scale(-1 1)' : '');
    if (frame !== lastFrame) {
      frameImage.setAttribute('href', `/halloween/${sources[frame]}`);
      lastFrame = frame;
    }
  }

  function tick(now: number): void {
    if (cancelled || (!active && !departing) || !ready) return;
    frameDelta = Math.min(0.06, Math.max(0, (now - previous) / 1000));
    previous = now;
    if (departing) {
      returnTime += frameDelta;
      elapsed = Math.max(0, elapsed - frameDelta * 1.65);
    } else {
      elapsed += frameDelta;
    }
    paint(elapsed);
    if (departing && elapsed === 0) {
      departing = false;
      return;
    }
    frameId = requestAnimationFrame(tick);
  }

  function sync(): void {
    const night = document.body.classList.contains('night');
    const enabled = night && !document.body.classList.contains('night-exiting');
    if (enabled === active && (night || !departing)) return;
    const wasDeparting = departing;
    active = enabled;
    cancelAnimationFrame(frameId);
    if (!ready) return;
    if (!enabled) {
      departing = night && !reduced.matches && elapsed > 0;
      if (!departing) return;
      elapsed = Math.min(elapsed, 5.8);
      if (howlActive) elapsed = 4.4 + (Math.max(0, howlFrame - 48) / 12) * 1.4;
      howlActive = false;
      returnTime = 0;
      previous = performance.now();
      frameId = requestAnimationFrame(tick);
      return;
    }
    departing = false;
    howlActive = false;
    howlFrame = 59;
    howlPhase = 'lowering';
    holdTime = 0;
    frameDelta = 0;
    elapsed = reduced.matches ? 5.8 : wasDeparting ? elapsed : 0;
    paint(elapsed);
    previous = performance.now();
    if (!reduced.matches) frameId = requestAnimationFrame(tick);
  }

  const observer = new MutationObserver(sync);
  observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
  const onVisibility = (): void => {
    previous = performance.now();
  };
  document.addEventListener('visibilitychange', onVisibility);
  const onReducedChange = (): void => {
    cancelAnimationFrame(frameId);
    if (!ready || !active) return;
    if (reduced.matches) {
      elapsed = 5.8;
      paint(elapsed);
    } else {
      previous = performance.now();
      frameId = requestAnimationFrame(tick);
    }
  };
  reduced.addEventListener('change', onReducedChange);

  resources
    .json<{ frames: Keyframe[]; fps: number }>('images/wolf-frames/keyframes.json')
    .then((data) => {
      if (cancelled) return;
      const svg = document.createElementNS(SVG_NS, 'svg');
      svg.setAttribute('viewBox', '0 0 400 500');
      svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
      svg.setAttribute('aria-hidden', 'true');
      routeGroup = document.createElementNS(SVG_NS, 'g');
      bodyPose = document.createElementNS(SVG_NS, 'g');
      frameImage = document.createElementNS(SVG_NS, 'image');
      frameImage.setAttribute('x', '-62.5');
      frameImage.setAttribute('y', '-84.375');
      frameImage.setAttribute('width', '125');
      frameImage.setAttribute('height', '90.625');
      bodyPose.append(frameImage);
      routeGroup.append(bodyPose);
      svg.append(routeGroup);
      stage.replaceChildren(svg);
      routeFrames = data.frames;
      fps = data.fps;
      ready = true;
      active = false;
      sync();
    })
    .catch((error: unknown) => console.warn('Không tải được sói:', (error as Error)?.message ?? error));

  return () => {
    cancelled = true;
    cancelAnimationFrame(frameId);
    observer.disconnect();
    document.removeEventListener('visibilitychange', onVisibility);
    reduced.removeEventListener('change', onReducedChange);
  };
}
