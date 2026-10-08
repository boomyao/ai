// A brand-free PET water bottle, drawn in SVG. bottle(id, opts) returns markup
// for a <g> whose origin is the top-centre of the cap; total height 900.
window.bottle = (id = 'b', { label = '饮用水', volume = '550 mL', drops = true, seed = 3, labelY = 0 } = {}) => {
  let s = seed;
  const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const body =
    'M -50 92 L 50 92 L 50 128 C 52 200 150 205 150 300 L 150 860 C 150 890 130 900 100 900 L -100 900 C -130 900 -150 890 -150 860 L -150 300 C -150 205 -52 200 -50 128 Z';
  const ribs = [330, 362, 650, 690, 730, 770, 810]
    .map(
      y => `<path d="M -150 ${y} Q 0 ${y + 14} 150 ${y}" fill="none" stroke="rgba(10,40,80,0.35)" stroke-width="3"/>
            <path d="M -150 ${y + 5} Q 0 ${y + 19} 150 ${y + 5}" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="2"/>`,
    )
    .join('');
  let condensation = '';
  if (drops)
    for (let i = 0; i < 46; i++) {
      const y = 215 + r() * 650;
      if (y > 405 && y < 615) continue;
      const half = y < 300 ? 60 + ((y - 200) / 100) * 85 : 140;
      const x = (r() * 2 - 1) * half * 0.92;
      const rad = 2.5 + r() * r() * 9;
      condensation += `<g transform="translate(${x.toFixed(1)} ${y.toFixed(1)})">
        <ellipse rx="${rad}" ry="${(rad * 1.12).toFixed(2)}" fill="url(#${id}-drop)"/>
        <ellipse rx="${(rad * 0.34).toFixed(2)}" ry="${(rad * 0.24).toFixed(2)}" cx="${(-rad * 0.35).toFixed(2)}" cy="${(-rad * 0.42).toFixed(2)}" fill="rgba(255,255,255,0.9)"/>
      </g>`;
    }
  const capRidges = Array.from({ length: 21 }, (_, i) => {
    const x = -58 + i * 5.8;
    return `<line x1="${x.toFixed(1)}" y1="10" x2="${x.toFixed(1)}" y2="74" stroke="${i % 2 ? 'rgba(255,255,255,0.18)' : 'rgba(0,0,30,0.28)'}" stroke-width="2"/>`;
  }).join('');
  return `
  <defs>
    <clipPath id="${id}-clip"><path d="${body}"/></clipPath>
    <linearGradient id="${id}-glass" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="rgb(110,165,220)" stop-opacity="0.62"/>
      <stop offset="0.1" stop-color="rgb(170,210,245)" stop-opacity="0.3"/>
      <stop offset="0.5" stop-color="rgb(225,242,255)" stop-opacity="0.08"/>
      <stop offset="0.9" stop-color="rgb(170,210,245)" stop-opacity="0.3"/>
      <stop offset="1" stop-color="rgb(110,165,220)" stop-opacity="0.62"/>
    </linearGradient>
    <linearGradient id="${id}-water" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="rgb(30,120,200)" stop-opacity="0.75"/>
      <stop offset="0.18" stop-color="rgb(80,175,235)" stop-opacity="0.42"/>
      <stop offset="0.5" stop-color="rgb(150,220,250)" stop-opacity="0.22"/>
      <stop offset="0.82" stop-color="rgb(80,175,235)" stop-opacity="0.42"/>
      <stop offset="1" stop-color="rgb(30,120,200)" stop-opacity="0.75"/>
    </linearGradient>
    <linearGradient id="${id}-waterv" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="rgb(255,255,255)" stop-opacity="0.18"/>
      <stop offset="0.3" stop-color="rgb(255,255,255)" stop-opacity="0"/>
      <stop offset="1" stop-color="rgb(0,40,90)" stop-opacity="0.35"/>
    </linearGradient>
    <linearGradient id="${id}-hl" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/>
      <stop offset="0.15" stop-color="#fff" stop-opacity="0.85"/>
      <stop offset="0.85" stop-color="#fff" stop-opacity="0.7"/>
      <stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="${id}-cap" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#0d2f6e"/>
      <stop offset="0.3" stop-color="#2f74d8"/>
      <stop offset="0.45" stop-color="#6aa6f2"/>
      <stop offset="0.7" stop-color="#1f5bbf"/>
      <stop offset="1" stop-color="#0b2659"/>
    </linearGradient>
    <linearGradient id="${id}-label" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#000" stop-opacity="0.45"/>
      <stop offset="0.18" stop-color="#000" stop-opacity="0.08"/>
      <stop offset="0.42" stop-color="#fff" stop-opacity="0.18"/>
      <stop offset="0.8" stop-color="#000" stop-opacity="0.1"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.5"/>
    </linearGradient>
    <radialGradient id="${id}-drop" cx="0.4" cy="0.35" r="0.65">
      <stop offset="0" stop-color="#fff" stop-opacity="0.05"/>
      <stop offset="0.7" stop-color="#bfe3ff" stop-opacity="0.18"/>
      <stop offset="0.92" stop-color="#ffffff" stop-opacity="0.65"/>
      <stop offset="1" stop-color="#0a3a70" stop-opacity="0.5"/>
    </radialGradient>
    <filter id="${id}-soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>
  </defs>
  <g>
    <path d="${body}" fill="url(#${id}-glass)"/>
    <g clip-path="url(#${id}-clip)">
      <rect x="-160" y="192" width="320" height="720" fill="url(#${id}-water)"/>
      <rect x="-160" y="192" width="320" height="720" fill="url(#${id}-waterv)"/>
      <ellipse cx="0" cy="192" rx="88" ry="9" fill="rgba(220,245,255,0.55)"/>
      <ellipse cx="0" cy="192" rx="88" ry="9" fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="2"/>
      ${ribs}
      <!-- label -->
      <rect x="-160" y="418" width="320" height="190" fill="#f3f7fb"/>
      <rect x="-160" y="418" width="320" height="16" fill="#1f63c9"/>
      <rect x="-160" y="592" width="320" height="16" fill="#1f63c9"/>
      <path d="M -160 560 C -100 535 -40 585 20 560 C 80 535 120 575 160 555 L 160 592 L -160 592 Z" fill="#8cc7f2"/>
      <path d="M -160 572 C -90 552 -30 600 40 574 C 90 556 130 586 160 572 L 160 592 L -160 592 Z" fill="#3c8ee0"/>
      <text x="0" y="512" text-anchor="middle" font-family="Noto Serif SC" font-weight="900" font-size="64" fill="#123a73" letter-spacing="6">${label}</text>
      <text x="0" y="546" text-anchor="middle" font-family="Oswald" font-weight="500" font-size="22" fill="#4b6c94" letter-spacing="4">${volume}</text>
      <rect x="-160" y="418" width="320" height="190" fill="url(#${id}-label)"/>
      <!-- highlights -->
      <rect x="-128" y="215" width="12" height="660" fill="url(#${id}-hl)" opacity="0.8"/>
      <rect x="62" y="230" width="46" height="640" fill="url(#${id}-hl)" opacity="0.28" filter="url(#${id}-soft)"/>
      <rect x="-104" y="230" width="6" height="640" fill="url(#${id}-hl)" opacity="0.35"/>
    </g>
    <path d="${body}" fill="none" stroke="rgba(255,255,255,0.45)" stroke-width="2.5"/>
    <path d="M 150 300 L 150 860" stroke="rgba(0,30,70,0.45)" stroke-width="3"/>
    ${condensation}
    <!-- neck ring & cap -->
    <rect x="-70" y="78" width="140" height="14" rx="6" fill="#dfe9f4" opacity="0.85"/>
    <rect x="-70" y="78" width="140" height="14" rx="6" fill="url(#${id}-label)" opacity="0.6"/>
    <rect x="-62" y="0" width="124" height="80" rx="12" fill="url(#${id}-cap)"/>
    ${capRidges}
    <rect x="-62" y="0" width="124" height="10" rx="6" fill="rgba(255,255,255,0.35)"/>
  </g>`;
};
