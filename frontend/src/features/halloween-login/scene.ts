/**
 * Cảnh chính: trời (mặt trời/mặt trăng, dơi, phù thuỷ), cú mèo canh ô email,
 * đèn pin soi mật khẩu ban đêm và dây leo SVG mọc theo trạng thái đêm.
 *
 * Chuyển thể từ `script.js` của bản HTML tĩnh. Toàn bộ trạng thái ngày/đêm vẫn
 * đặt class `night` / `night-exiting` / `flashlight-on` trên `<body>` để CSS
 * gốc (đã chuyển selector về `.night …`) và các module sói/nhện giữ nguyên.
 */

import { inlineSvgPlaceholders, prepareAssets, resources } from './assets';

type Cleanup = () => void;

interface LeafState {
  node: Element;
  strength: number;
  target: number;
  phase: number;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(value, max));
}

export function startScene(): Cleanup {
  const cleanups: Cleanup[] = [];
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');

  const passwordInput = document.getElementById('password') as HTMLInputElement;
  const confirmPasswordInput = document.getElementById('confirmPassword') as HTMLInputElement | null;
  const toggleButton = document.getElementById('show-password') as HTMLButtonElement;
  const statusMessage = document.getElementById('status');
  const beam = document.getElementById('flash-beam') as HTMLElement;
  const passwordOverlay = document.getElementById('password-reveal') as HTMLElement;
  const passwordChars = document.getElementById('reveal-text') as HTMLElement;
  const flashlight = document.getElementById('flashlight') as HTMLElement;
  const owl = document.getElementById('email-owl') as HTMLElement;
  const themeButton = document.getElementById('theme-toggle') as HTMLButtonElement;

  if (!passwordInput || !toggleButton || !beam || !passwordOverlay || !passwordChars || !flashlight || !owl || !themeButton) {
    console.warn('Thiếu mốc cảnh Halloween, bỏ qua hiệu ứng.');
    return () => {};
  }

  const texts = {
    night: 'Bật đêm Halloween',
    day: 'Trở về ban ngày',
    lightOn: 'Chiếu đèn pin để xem mật khẩu',
    lightOff: 'Tắt đèn pin',
    show: 'Hiện mật khẩu',
    hide: 'Ẩn mật khẩu',
  };

  let nightMode = false;
  try {
    nightMode = sessionStorage.getItem('mf_halloween_night') === '1';
  } catch {
    nightMode = false;
  }
  let revealEnabled = false;
  let cursor = { x: 0, y: 0 };
  let beamAngle = Math.PI;

  let leafStates: LeafState[] = [];
  let leafAnimation = 0;
  let leafPrevious = 0;

  function animateLitLeaves(): void {
    if (leafAnimation || reduced.matches) return;
    leafPrevious = performance.now();
    const tick = (now: number): void => {
      const dt = Math.min((now - leafPrevious) / 1000, 0.06);
      leafPrevious = now;
      let moving = false;
      leafStates.forEach((leaf, index) => {
        const easing = 1 - Math.exp(-dt / (leaf.target > leaf.strength ? 0.22 : 0.45));
        leaf.strength += (leaf.target - leaf.strength) * easing;
        leaf.phase += dt * (2.6 + (index % 4) * 0.23);
        const angle = (Math.sin(leaf.phase) * 7 + Math.sin(leaf.phase * 1.7) * 1.4) * leaf.strength;
        if (leaf.strength > 0.002 || leaf.target > 0) {
          leaf.node.setAttribute('style', `transform: rotate(${angle.toFixed(3)}deg)`);
          moving = true;
        } else {
          leaf.strength = 0;
          leaf.node.removeAttribute('style');
        }
      });
      leafAnimation = moving ? requestAnimationFrame(tick) : 0;
    };
    leafAnimation = requestAnimationFrame(tick);
  }

  function updateOwlGaze(dx: number, dy: number, lit: boolean): void {
    const distance = Math.max(1, Math.hypot(dx, dy));
    const x = lit ? dx / distance : 0;
    const y = lit ? dy / distance : 0;
    const newlyLit = lit && !owl.classList.contains('is-lit');
    owl.classList.toggle('is-lit', lit);
    if (newlyLit) owl.classList.add('just-lit');
    if (!lit) owl.classList.remove('just-lit');
    owl.style.setProperty('--owl-gaze-x', `${x * 70}px`);
    owl.style.setProperty('--owl-gaze-y', `${y * 45}px`);
    owl.style.setProperty('--owl-head-x', `${x * 22}px`);
    owl.style.setProperty('--owl-head-y', `${y * 12}px`);
    owl.style.setProperty('--owl-tilt', `${x * 5}deg`);
  }

  function renderPassword(): void {
    const isFocused = document.activeElement === passwordInput;
    const rawCaret = passwordInput.selectionStart;
    const caretPos = typeof rawCaret === 'number' ? rawCaret : passwordInput.value.length;
    const chars = Array.from(passwordInput.value, (letter, idx) => {
      const character = document.createElement('span');
      character.className = isFocused && idx === caretPos ? 'reveal-char has-caret-before' : 'reveal-char';
      const masked = document.createElement('span');
      masked.className = 'masked-char';
      masked.textContent = '•';
      const plain = document.createElement('span');
      plain.className = 'plain-char';
      plain.textContent = letter;
      character.append(masked, plain);
      return character;
    });
    if (isFocused && caretPos >= passwordInput.value.length) {
      const endCaret = document.createElement('span');
      endCaret.className = 'reveal-caret-end';
      endCaret.setAttribute('aria-hidden', 'true');
      chars.push(endCaret);
    }
    passwordChars.replaceChildren(...chars);
  }

  function getLightLevel(x: number, y: number, originX: number, originY: number, unitX: number, unitY: number, beamLength: number, beamHeight: number): number {
    const offsetX = x - originX;
    const offsetY = y - originY;
    const along = offsetX * unitX + offsetY * unitY;
    const sideways = Math.abs(-offsetX * unitY + offsetY * unitX);
    const halfBeam = beamHeight * (0.01 + 0.49 * Math.max(0, along) / beamLength);
    const edgeFade = clamp((halfBeam - sideways + 4) / 16, 0, 1);
    const tail = clamp((along / beamLength - 0.55) / 0.41, 0, 1);
    const endFade = 1 - tail * tail * (3 - 2 * tail);
    return along >= 0 ? edgeFade * endFade : 0;
  }

  function updateFlashlight(): void {
    if (!nightMode || !revealEnabled) return;

    const eyeRect = toggleButton.getBoundingClientRect();
    const fieldRect = passwordInput.getBoundingClientRect();
    const eyeX = eyeRect.left + eyeRect.width / 2;
    const eyeY = eyeRect.top + eyeRect.height / 2;
    const pointerDistance = Math.hypot(cursor.x - eyeX, cursor.y - eyeY);
    if (pointerDistance > 24) {
      beamAngle = Math.atan2(cursor.y - eyeY, cursor.x - eyeX);
    }
    const angleDeg = (beamAngle * 180) / Math.PI;
    const unitX = Math.cos(beamAngle);
    const unitY = Math.sin(beamAngle);
    const originX = eyeX + unitX * 13;
    const originY = eyeY + unitY * 13;
    const beamLength = clamp(pointerDistance * 1.65, 160, 1600);
    const beamHeight = beamLength * 0.38;

    beam.style.left = `${originX}px`;
    beam.style.top = `${originY - beamHeight / 2}px`;
    beam.style.width = `${beamLength}px`;
    beam.style.height = `${beamHeight}px`;
    beam.style.transform = `rotate(${angleDeg}deg)`;
    flashlight.style.left = `${eyeX - 17}px`;
    flashlight.style.top = `${eyeY - 17}px`;
    flashlight.style.transform = `rotate(${angleDeg}deg)`;

    passwordOverlay.style.left = `${fieldRect.left}px`;
    passwordOverlay.style.top = `${fieldRect.top}px`;
    passwordOverlay.style.width = `${Math.max(0, fieldRect.width - 45)}px`;
    passwordOverlay.style.height = `${fieldRect.height}px`;
    passwordChars.style.transform = `translateX(${-passwordInput.scrollLeft}px)`;

    for (const character of Array.from(passwordChars.children)) {
      if (!character.classList.contains('reveal-char')) continue;
      const bounds = character.getBoundingClientRect();
      const light = getLightLevel(
        bounds.left + bounds.width / 2,
        fieldRect.top + fieldRect.height / 2,
        originX,
        originY,
        unitX,
        unitY,
        beamLength,
        beamHeight,
      );
      (character as HTMLElement).style.setProperty('--lit', String(light));
    }
    const owlBounds = owl.getBoundingClientRect();
    const owlX = owlBounds.left + owlBounds.width / 2;
    const owlY = owlBounds.top + owlBounds.height / 2;
    const owlLight = getLightLevel(owlX, owlY, originX, originY, unitX, unitY, beamLength, beamHeight);
    owl.style.opacity = String(owlLight);
    updateOwlGaze(originX - owlX, originY - (owlBounds.top + owlBounds.height * 0.36), owlLight > 0.08);
    document.querySelectorAll('.pumpkin-reaction').forEach((pumpkin) => {
      const face = pumpkin.querySelector('.pumpkin-face-normal')?.getBoundingClientRect();
      if (!face) return;
      const level = getLightLevel(
        face.left + face.width / 2,
        face.top + face.height / 2,
        originX,
        originY,
        unitX,
        unitY,
        beamLength,
        beamHeight,
      );
      const threshold = pumpkin.classList.contains('is-beam-lit') ? 0.06 : 0.14;
      pumpkin.classList.toggle('is-beam-lit', level > threshold);
    });
    leafStates.forEach((leaf) => {
      const bounds = leaf.node.getBoundingClientRect();
      const level = getLightLevel(
        bounds.left + bounds.width / 2,
        bounds.top + bounds.height / 2,
        originX,
        originY,
        unitX,
        unitY,
        beamLength,
        beamHeight,
      );
      leaf.target = level > 0.08 ? level : 0;
    });
    const wolf = document.querySelector('.summit-stage image');
    const wolfStage = document.querySelector('.summit-stage');
    if (wolf && wolfStage) {
      const bounds = wolf.getBoundingClientRect();
      const level = getLightLevel(
        bounds.left + bounds.width * 0.6,
        bounds.top + bounds.height * 0.5,
        originX,
        originY,
        unitX,
        unitY,
        beamLength,
        beamHeight,
      );
      wolfStage.classList.toggle('is-beam-lit', level > (wolfStage.classList.contains('is-beam-lit') ? 0.06 : 0.14));
    }
    animateLitLeaves();
  }

  function setPasswordReveal(enabled: boolean): void {
    revealEnabled = enabled;
    document.body.classList.toggle('flashlight-on', nightMode && enabled);
    passwordInput.type = !nightMode && enabled ? 'text' : 'password';
    if (confirmPasswordInput) {
      confirmPasswordInput.type = enabled ? 'text' : 'password';
    }
    toggleButton.setAttribute('aria-pressed', String(enabled));
    const description = nightMode ? texts[enabled ? 'lightOff' : 'lightOn'] : texts[enabled ? 'hide' : 'show'];
    toggleButton.setAttribute('aria-label', description);
    if (nightMode && enabled) {
      renderPassword();
      const fieldRect = passwordInput.getBoundingClientRect();
      beamAngle = Math.PI;
      cursor = { x: fieldRect.left, y: fieldRect.top + fieldRect.height / 2 };
      updateFlashlight();
    } else {
      passwordChars.replaceChildren();
      document.querySelector('.summit-stage')?.classList.remove('is-beam-lit');
      owl.style.opacity = '0';
      updateOwlGaze(0, 0, false);
      document.querySelectorAll('.pumpkin-reaction').forEach((pumpkin) => pumpkin.classList.remove('is-beam-lit'));
      leafStates.forEach((leaf) => {
        leaf.target = 0;
      });
      animateLitLeaves();
    }
  }

  let dayTransitionTimer = 0;
  const departingFlights: Animation[] = [];
  function setNightMode(enabled: boolean): void {
    clearTimeout(dayTransitionTimer);
    departingFlights.forEach((animation) => animation.cancel());
    departingFlights.length = 0;
    nightMode = enabled;
    try {
      sessionStorage.setItem('mf_halloween_night', enabled ? '1' : '0');
    } catch {
      // ignore storage errors
    }
    const retiring = !enabled && document.body.classList.contains('night') && !reduced.matches;
    document.body.classList.toggle('night-exiting', retiring);
    if (enabled) document.body.classList.add('night');
    else if (!retiring) document.body.classList.remove('night');
    if (retiring) {
      document.querySelectorAll('.sky-bat, .sky-witch').forEach((flyer) => {
        const bounds = flyer.getBoundingClientRect();
        const direction = bounds.left + bounds.width / 2 < innerWidth / 2 ? -1 : 1;
        const transform = getComputedStyle(flyer).transform;
        const opacity = getComputedStyle(flyer).opacity;
        departingFlights.push(
          flyer.animate(
            [
              { transform, opacity },
              { transform: `translate(${direction * 90}px, -90px) rotate(${direction * 12}deg)`, opacity: 0 },
            ],
            { duration: 1200, easing: 'cubic-bezier(.4,0,.7,1)', fill: 'forwards' },
          ),
        );
      });
      dayTransitionTimer = window.setTimeout(() => {
        document.body.classList.remove('night', 'night-exiting');
        departingFlights.forEach((animation) => animation.cancel());
        departingFlights.length = 0;
      }, 3700);
    }
    animateVines(enabled);
    themeButton.setAttribute('aria-pressed', String(enabled));
    themeButton.setAttribute('aria-label', enabled ? texts.day : texts.night);
    setPasswordReveal(false);
  }

  const onPointerMove = (event: PointerEvent): void => {
    if (!nightMode || !revealEnabled) return;
    cursor = { x: event.clientX, y: event.clientY };
    updateFlashlight();
  };
  document.addEventListener('pointermove', onPointerMove, { passive: true });
  cleanups.push(() => document.removeEventListener('pointermove', onPointerMove));

  const syncPasswordOverlay = (): void => {
    if (nightMode && revealEnabled) {
      renderPassword();
      updateFlashlight();
    }
  };
  passwordInput.addEventListener('input', syncPasswordOverlay);
  passwordInput.addEventListener('keyup', syncPasswordOverlay);
  passwordInput.addEventListener('keydown', () => requestAnimationFrame(syncPasswordOverlay));
  passwordInput.addEventListener('click', syncPasswordOverlay);
  passwordInput.addEventListener('focus', syncPasswordOverlay);
  passwordInput.addEventListener('blur', syncPasswordOverlay);
  passwordInput.addEventListener('scroll', updateFlashlight);
  const onResize = (): void => updateFlashlight();
  window.addEventListener('resize', onResize);
  cleanups.push(() => window.removeEventListener('resize', onResize));
  const onScroll = (): void => updateFlashlight();
  window.addEventListener('scroll', onScroll, true);
  cleanups.push(() => window.removeEventListener('scroll', onScroll, true));

  toggleButton.addEventListener('click', () => setPasswordReveal(!revealEnabled));
  themeButton.addEventListener('click', () => setNightMode(!nightMode));

  // --- Dây leo SVG ---
  let vineNodes: Element[] = [];
  let vineFrames: Record<string, number>[][] = [];
  let vineProgress = nightMode ? 1 : 0;
  let vineTarget = nightMode ? 1 : 0;
  let vineAnimation = 0;

  if (nightMode) {
    document.body.classList.add('night');
    themeButton.setAttribute('aria-pressed', 'true');
    themeButton.setAttribute('aria-label', texts.day);
  }

  function paintVineFrame(progress: number): void {
    if (!vineFrames.length) return;
    const position = progress * (vineFrames.length - 1);
    const first = Math.floor(position);
    const second = Math.min(first + 1, vineFrames.length - 1);
    const mix = position - first;
    vineNodes.forEach((node, index) => {
      const a = vineFrames[first][index];
      const b = vineFrames[second][index];
      if (!a || !b) return;
      const interpolate = (key: string): number => a[key] + (b[key] - a[key]) * mix;
      if ('dash' in a) {
        const dash = interpolate('dash');
        node.setAttribute('stroke-dashoffset', dash.toFixed(2));
        node.setAttribute('opacity', dash >= 999.99 ? '0' : '1');
      } else {
        node.setAttribute('opacity', interpolate('opacity').toFixed(3));
        node.setAttribute('transform', `rotate(${interpolate('angle').toFixed(2)}) scale(${interpolate('scale').toFixed(4)})`);
      }
    });
  }

  function animateVines(enabled: boolean): void {
    vineTarget = enabled ? 1 : 0;
    cancelAnimationFrame(vineAnimation);
    if (!vineFrames.length) return;
    if (reduced.matches) {
      vineProgress = vineTarget;
      paintVineFrame(vineProgress);
      return;
    }
    let previous: number | undefined;
    const tick = (now: number): void => {
      if (previous !== undefined) {
        const step = Math.min(now - previous, 50) / 3600;
        vineProgress = vineTarget ? Math.min(1, vineProgress + step) : Math.max(0, vineProgress - step);
      }
      previous = now;
      paintVineFrame(vineProgress);
      if (vineProgress !== vineTarget) vineAnimation = requestAnimationFrame(tick);
    };
    vineAnimation = requestAnimationFrame(tick);
  }

  function fitVineArtwork(svg: SVGSVGElement): void {
    const host = document.getElementById('halloween-vines');
    const main = Array.from(svg.querySelectorAll<SVGGElement>('[data-layout="main"]'));
    const branches = Array.from(svg.querySelectorAll<SVGGElement>('[data-layout="branch"]'));
    const ornaments = Array.from(svg.querySelectorAll<SVGGElement>('[data-layout="ornament"]'));
    const numbers = /-?\d+(?:\.\d+)?/g;
    const rootOf = (group: SVGGElement): number[] => (group.dataset.path ?? '').match(numbers)!.slice(0, 2).map(Number);

    function resize(): void {
      if (!host) return;
      const { width, height } = host.getBoundingClientRect();
      if (!width || !height) return;
      const unit = Math.min(width / 1000, height / 620);
      const card = document.querySelector('.login-card');
      if (!card) return;
      const bounds = card.getBoundingClientRect();
      const frame = host.getBoundingClientRect();
      const left = bounds.left - frame.left;
      const top = bounds.top - frame.top;
      const right = bounds.right - frame.left;
      const bottom = bounds.bottom - frame.top;
      const radius = parseFloat(getComputedStyle(card).borderTopLeftRadius) || 32;
      const interpolate = (value: number, source: number[], target: number[]): number => {
        const i = value < source[1] ? 0 : value > source[2] ? 2 : 1;
        return target[i] + ((value - source[i]) * (target[i + 1] - target[i])) / (source[i + 1] - source[i]);
      };
      const map = (x: number, y: number): [number, number] => [
        interpolate(x, [58, 98, 902, 942], [left, left + radius, right - radius, right]),
        interpolate(y, [55, 95, 537, 565], [top, top + radius, bottom - radius, bottom]),
      ];
      svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
      const draw = (group: SVGGElement, mapping: (x: number, y: number) => [number, number]): void => {
        const values = (group.dataset.path ?? '').match(numbers)!.map(Number);
        let n = 0;
        const path = (group.dataset.path ?? '').replace(numbers, () => {
          const coordinate = n % 2;
          const at = n - coordinate;
          const point = mapping(values[at], values[at + 1]);
          n++;
          return point[coordinate].toFixed(3);
        });
        for (const node of Array.from(group.children)) {
          node.setAttribute('d', path);
          node.setAttribute('stroke-width', String(Number((node as SVGElement).dataset.width ?? 0) * unit));
        }
      };
      main.forEach((group) => draw(group, map));
      const samples = main.flatMap((group) => {
        const path = group.firstElementChild as SVGPathElement | null;
        if (!path) return [];
        const length = path.getTotalLength();
        return Array.from({ length: 401 }, (_, i) => path.getPointAtLength((length * i) / 400));
      });
      const anchor = (x: number, y: number): [number, number] => {
        const [px, py] = map(x, y);
        let closest = samples[0];
        for (const point of samples) {
          if ((point.x - px) ** 2 + (point.y - py) ** 2 < (closest.x - px) ** 2 + (closest.y - py) ** 2) {
            closest = point;
          }
        }
        return [closest.x, closest.y];
      };
      if (samples.length) {
        branches.forEach((group) => {
          const [x, y] = rootOf(group);
          const [px, py] = anchor(x, y);
          draw(group, (cx, cy) => [px + (cx - x) * unit, py + (cy - y) * unit]);
        });
        ornaments.forEach((group) => {
          const { art, x, y, scale, rotation } = group.dataset;
          let point = art === 'pumpkin' ? map(Number(x), Number(y)) : anchor(Number(x), Number(y));
          if (group.dataset.branchRootX !== undefined) {
            const rx = Number(group.dataset.branchRootX);
            const ry = Number(group.dataset.branchRootY);
            const root = anchor(rx, ry);
            point = [root[0] + (Number(x) - rx) * unit, root[1] + (Number(y) - ry) * unit];
          }
          if (art === 'lantern') {
            const lanternRoot = Number(x) < 500 ? [65, 219] : [946, 300];
            const root = anchor(lanternRoot[0], lanternRoot[1]);
            point = [root[0] + (Number(x) - lanternRoot[0]) * unit, root[1] + (Number(y) - lanternRoot[1]) * unit];
          }
          group.setAttribute('transform', `translate(${point[0]} ${point[1]}) rotate(${rotation}) scale(${Number(scale) * unit})`);
        });
      }
    }

    let resizeRaf = 0;
    const scheduleResize = (): void => {
      cancelAnimationFrame(resizeRaf);
      resizeRaf = requestAnimationFrame(resize);
    };
    const observer = new ResizeObserver(scheduleResize);
    if (host) {
      observer.observe(host);
    }
    resize();
    cleanups.push(() => {
      cancelAnimationFrame(resizeRaf);
      observer.disconnect();
    });
  }

  async function loadVines(): Promise<void> {
    try {
      const [source, frames] = await Promise.all([
        resources.text('images/vine-styles/outer/artwork.svg'),
        resources.json<Record<string, number>[][]>('images/vine-styles/outer/keyframes.json'),
      ]);
      const artwork = new DOMParser().parseFromString(source, 'image/svg+xml');
      const svg = document.importNode(artwork.documentElement, true) as unknown as SVGSVGElement;
      const nodes = Array.from(svg.querySelectorAll('[data-grow]'));
      if (!frames.length || frames.some((frame) => frame.length !== nodes.length)) {
        throw new Error('Vine frames do not match artwork');
      }
      cancelAnimationFrame(vineAnimation);
      svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
      document.getElementById('halloween-vines')?.replaceChildren(svg);
      fitVineArtwork(svg);
      vineNodes = nodes;
      vineFrames = frames;
      leafStates = Array.from(svg.querySelectorAll('.leaf-reaction')).map((node, index) => ({
        node,
        strength: 0,
        target: 0,
        phase: index * 1.31,
      }));
      paintVineFrame(vineProgress);
      animateVines(nightMode);
    } catch (error) {
      console.warn('Không tải được dây leo:', (error as Error).message);
    }
  }
  void loadVines();
  const onReducedChange = (): void => animateVines(nightMode);
  reduced.addEventListener('change', onReducedChange);
  cleanups.push(() => reduced.removeEventListener('change', onReducedChange));

  const onOwlAnimationEnd = (event: AnimationEvent): void => {
    if (event.animationName === 'owl-startle') owl.classList.remove('just-lit');
  };
  owl.addEventListener('animationend', onOwlAnimationEnd);

  // Phù thuỹ bay theo khung thẻ
  const witch = document.querySelector<HTMLElement>('.sky-witch');
  const cardElement = document.querySelector<HTMLElement>('.login-card');
  function updateWitchRoute(): void {
    if (!witch || !cardElement || !witch.parentElement) return;
    const card = cardElement.getBoundingClientRect();
    const sky = witch.parentElement.getBoundingClientRect();
    const width = parseFloat(getComputedStyle(witch).width) || 100;
    witch.style.setProperty('--witch-left', `${Math.max(6, card.left - sky.left - 94)}px`);
    witch.style.setProperty('--witch-right', `${Math.min(sky.width - width - 6, card.right - sky.left + 94 - width)}px`);
    witch.style.setProperty('--witch-top', `${Math.max(16, card.top - sky.top - 150)}px`);
  }
  if (witch && cardElement) {
    updateWitchRoute();
    const witchObserver = new ResizeObserver(updateWitchRoute);
    witchObserver.observe(cardElement);
    cleanups.push(() => witchObserver.disconnect());
    const onWitchResize = (): void => updateWitchRoute();
    window.addEventListener('resize', onWitchResize);
    cleanups.push(() => window.removeEventListener('resize', onWitchResize));
  }

  void prepareAssets().then(() => inlineSvgPlaceholders(document));
  if (statusMessage) statusMessage.textContent = '';

  return () => {
    clearTimeout(dayTransitionTimer);
    cancelAnimationFrame(leafAnimation);
    cancelAnimationFrame(vineAnimation);
    departingFlights.forEach((animation) => animation.cancel());
    owl.removeEventListener('animationend', onOwlAnimationEnd);
    document.body.classList.remove('night', 'night-exiting', 'flashlight-on');
    cleanups.forEach((cleanup) => cleanup());
  };
}
