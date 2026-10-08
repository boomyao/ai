// Line-art illustrations, authored as SVG path data in local coordinates.
// Each entry is { w, h, paths: [...], accents?: [...] } and is drawn with C.art().
const ART = (window.ART = {});

// Boiling cauldron over a fire (local box 600×520).
ART.cauldron = {
  w: 600,
  h: 520,
  paths: [
    // rim
    'M110 170 C 110 150 490 150 490 170 C 490 190 110 190 110 170 Z',
    // body
    'M120 178 C 112 300 170 392 300 396 C 430 392 488 300 480 178',
    // handles
    'M112 196 C 70 196 64 248 104 252',
    'M488 196 C 530 196 536 248 496 252',
    // legs
    'M190 372 L170 430 M410 372 L430 430 M300 396 L300 440',
    // fire
    'M200 470 C 190 440 220 430 214 404 C 240 424 236 446 248 452 C 252 432 268 424 270 404 C 296 432 286 452 300 470',
    'M300 470 C 296 446 322 436 318 408 C 344 430 336 452 352 456 C 356 438 372 430 376 412 C 398 440 388 462 400 470',
    'M150 470 H450',
  ],
  // bubbles & steam drawn separately (animated)
};

// Stylised hand reaching down (local 260×360), fingertips at bottom.
ART.hand = {
  w: 260,
  h: 360,
  paths: [
    'M70 0 C 66 80 62 150 58 200 C 40 214 30 236 34 262 C 38 290 56 300 64 336 C 66 348 82 350 84 336 C 84 312 82 292 88 280 C 92 310 96 336 100 352 C 104 362 120 360 120 348 C 118 318 114 294 116 280 C 122 306 128 332 134 344 C 138 354 154 352 152 340 C 148 314 140 290 142 274 C 150 296 158 316 166 326 C 172 334 186 330 182 318 C 172 290 164 262 162 240 C 160 214 168 196 184 172 C 196 154 190 140 176 146 C 160 154 148 172 140 190 C 136 140 134 70 136 0',
  ],
};

// A small river stone (local 120×70).
ART.stone = { w: 120, h: 70, paths: ['M10 40 C 6 18 40 6 64 8 C 96 10 116 22 112 42 C 108 62 76 66 52 64 C 28 62 12 58 10 40 Z', 'M40 26 C 54 22 70 24 80 30'] };

// Balance scale (local 900×560), pivot at (450, 120).
ART.scaleStand = {
  w: 900,
  h: 560,
  paths: ['M450 120 V500', 'M360 520 H540 M390 500 H510', 'M450 96 A14 14 0 1 0 450.01 96'],
};

// Prison bars window (local 320×360).
ART.bars = {
  w: 320,
  h: 360,
  paths: ['M20 20 H300 V340 H20 Z', 'M80 20 V340', 'M140 20 V340', 'M200 20 V340', 'M260 20 V340', 'M20 120 H300', 'M20 240 H300'],
};

// Interrogation room in one-point perspective (local 1200×680).
ART.room = {
  w: 1200,
  h: 680,
  paths: [
    // back wall
    'M360 150 H840 V470 H360 Z',
    // floor/ceiling edges
    'M0 0 L360 150 M1200 0 L840 150 M0 680 L360 470 M1200 680 L840 470',
    // lamp cord + shade
    'M600 0 V170 M540 230 L600 170 L660 230 Z',
    // table
    'M430 430 H770 L820 500 H380 Z M400 500 V600 M800 500 V600',
    // chairs
    'M300 470 V610 M300 470 H360 V540 H300 M360 540 V610',
    'M900 470 V610 M900 470 H840 V540 H900 M840 540 V610',
    // door on back wall
    'M720 260 H800 V470 H720 Z',
  ],
};

// Great Wall silhouette inside a photo (local 520×360).
ART.wall = {
  w: 520,
  h: 360,
  paths: [
    'M0 300 L60 250 L120 270 L190 200 L260 230 L330 160 L400 190 L470 130 L520 150',
    'M0 330 L60 280 L120 300 L190 230 L260 260 L330 190 L400 220 L470 160 L520 180',
    'M180 206 V180 H204 V196 M322 166 V138 H346 V158 M462 136 V110 H486 V128',
    'M20 120 C 80 90 140 110 200 90 C 280 64 340 100 420 70 C 460 56 500 64 520 60',
  ],
};

// Bell (local 200×240).
ART.bell = {
  w: 200,
  h: 240,
  paths: ['M100 10 V34', 'M100 34 C 60 34 46 70 44 110 C 42 150 30 170 14 190 H186 C 170 170 158 150 156 110 C 154 70 140 34 100 34 Z', 'M84 196 C 84 216 116 216 116 196'],
};

// Draw an ART piece at (x, y) scaled; returns the group.
C.art = (s, parent, piece, { x = 0, y = 0, scale = 1, ...opts } = {}) => {
  const g = E.s('g', { transform: `translate(${x} ${y}) scale(${scale})` });
  parent.append(g);
  C.draw(s, g, piece.paths, opts);
  return g;
};
