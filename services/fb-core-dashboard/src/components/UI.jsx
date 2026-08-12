import React from 'react';

export function Spinner() {
  return (
    <div className="flex items-center justify-center p-12">
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 border-4 border-slate-700 rounded-full" />
        <div className="absolute inset-0 border-4 border-transparent border-t-accentGreen rounded-full animate-spin" />
      </div>
    </div>
  );
}

export function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative w-10 h-10">
        <div className="absolute inset-0 bg-gradient-to-br from-green-400 to-emerald-600 rounded-xl rotate-45" />
        <div className="absolute inset-[3px] bg-slate-900 rounded-lg rotate-45 flex items-center justify-center">
          <span className="text-green-400 font-black text-sm -rotate-45">FB</span>
        </div>
      </div>
      <div>
        <span className="text-white font-bold text-lg">FinBot</span>
        <span className="text-green-400 font-bold text-lg">Crypto</span>
      </div>
    </div>
  );
}

export function playNewTradeSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(800, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.1);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.4);
  } catch(e) {}
}
