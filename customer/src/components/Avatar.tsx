// A free, stylized concierge avatar for APEX — deliberately NOT photorealistic (a clearly-AI
// avatar avoids the deepfake/impersonation problem). Pure SVG + CSS, no API, no cost.
// • mouth: a gentle smile when idle, animating open while the browser TTS is speaking
//   (driven by utterance start/end — speechSynthesis exposes no audio stream to analyse)
// • eyes blink on a loop; the whole head breathes (idle float); a soft aura pulses while speaking.
export default function Avatar({ speaking, size = 32 }: { speaking: boolean; size?: number }) {
  return (
    <div style={{ width: size, height: size, lineHeight: 0 }}>
      <style>{`
        @keyframes apex-talk  { 0%,100% { transform: scaleY(0.28) } 50% { transform: scaleY(1) } }
        @keyframes apex-blink { 0%,92%,100% { transform: scaleY(1) } 96% { transform: scaleY(0.08) } }
        @keyframes apex-float { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-2px) } }
        @keyframes apex-aura  { 0%,100% { opacity:.30; transform: scale(1) } 50% { opacity:.8; transform: scale(1.09) } }
        .apex-svg  { animation: apex-float 4s ease-in-out infinite; }
        .apex-eye  { transform-box: fill-box; transform-origin: center; animation: apex-blink 5.5s infinite; }
        .apex-mouth{ transform-box: fill-box; transform-origin: center; }
        .apex-mouth.talking { animation: apex-talk 0.22s ease-in-out infinite; }
        .apex-aura { transform-box: fill-box; transform-origin: center; opacity: .3; }
        .apex-aura.on { animation: apex-aura 1.1s ease-in-out infinite; }
      `}</style>
      <svg className="apex-svg" viewBox="0 0 100 100" width={size} height={size} aria-hidden>
        <defs>
          <radialGradient id="apexHead" cx="50%" cy="30%" r="85%">
            <stop offset="0%" stopColor="#7cb1ff" />
            <stop offset="55%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#1e40af" />
          </radialGradient>
          <linearGradient id="apexBand" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#bfdbfe" />
            <stop offset="100%" stopColor="#93c5fd" />
          </linearGradient>
          <filter id="apexBlur" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="4.5" />
          </filter>
        </defs>

        {/* soft aura — pulses only while speaking */}
        <circle className={`apex-aura ${speaking ? 'on' : ''}`} cx="50" cy="52" r="40"
                fill="#60a5fa" filter="url(#apexBlur)" />

        {/* headset: band over the top, ear cups, mic boom (the 'concierge' cue) */}
        <path d="M24 48 A27 27 0 0 1 76 48" fill="none" stroke="url(#apexBand)" strokeWidth="5" strokeLinecap="round" />
        <rect x="15" y="46" width="11" height="22" rx="5.5" fill="#93c5fd" />
        <rect x="74" y="46" width="11" height="22" rx="5.5" fill="#93c5fd" />
        <path d="M80 60 q7 9 -3 18" fill="none" stroke="#93c5fd" strokeWidth="3" strokeLinecap="round" />
        <circle cx="76" cy="78" r="2.8" fill="#bfdbfe" />

        {/* head */}
        <rect x="27" y="31" width="46" height="46" rx="17" fill="url(#apexHead)" />
        <ellipse cx="50" cy="41" rx="17" ry="8" fill="#ffffff" opacity="0.12" />

        {/* eyes (white + highlight, blink together) */}
        <g className="apex-eye">
          <rect x="39" y="47" width="7" height="10" rx="3.5" fill="#fff" />
          <circle cx="42.4" cy="50" r="1.5" fill="#1e3a8a" />
        </g>
        <g className="apex-eye">
          <rect x="54" y="47" width="7" height="10" rx="3.5" fill="#fff" />
          <circle cx="57.4" cy="50" r="1.5" fill="#1e3a8a" />
        </g>

        {/* mouth: smile when idle, animated open when speaking */}
        {speaking ? (
          <ellipse className="apex-mouth talking" cx="50" cy="67" rx="9" ry="6" fill="#08122b" />
        ) : (
          <path d="M43 65 q7 6.5 14 0" fill="none" stroke="#08122b" strokeWidth="3.5" strokeLinecap="round" />
        )}
      </svg>
    </div>
  )
}
