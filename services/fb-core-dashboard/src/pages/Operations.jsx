import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Spinner, playNewTradeSound } from '../components/UI';

function SLTPBar({ current, sl, tp, entry, entryTime, maxHoldHours }) {
  if (!entry || !current) return null;

  // 1. Barra de Preço (Entry -> TP ou SL -> Entry -> TP)
  let priceProgressHtml = null;
  const slActive = sl && sl > 0;
  
  if (slActive && tp && tp > sl) {
    // Modo OCO legado com SL ativo
    const range = tp - sl;
    const pct = ((current - sl) / range) * 100;
    const clamped = Math.max(0, Math.min(100, pct));
    const barColor = current >= entry ? 'bg-accentGreen' : 'bg-accentRed';
    priceProgressHtml = (
      <div className="mt-3">
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>SL ${sl.toFixed(6)}</span>
          <span className="text-slate-400">Entry ${entry.toFixed(6)}</span>
          <span>TP ${tp.toFixed(6)}</span>
        </div>
        <div className="h-3 bg-slate-700/80 rounded-full relative overflow-hidden">
          <div className={`h-full ${barColor} rounded-full transition-all duration-500`} style={{ width: `${clamped}%` }} />
          <div className="absolute top-0 bottom-0 w-0.5 bg-white/50" style={{ left: `${((entry - sl) / range) * 100}%` }} />
        </div>
        <div className="text-center text-xs text-slate-400 mt-1">
          ${current.toFixed(6)} ({clamped.toFixed(0)}% até TP)
        </div>
      </div>
    );
  } else if (tp && tp > entry) {
    // Novo modo sem SL (Entry -> TP) com suporte a preço negativo com limite dinâmico
    const defaultFloor = entry - (tp - entry) * (30 / 70);
    // Se a perda for maior que o defaultFloor, esticamos a escala (deixando margem de 50% além do atual)
    const minPrice = current < entry 
      ? Math.min(defaultFloor, current - (entry - current) * 0.5) 
      : defaultFloor;

    const totalRange = tp - minPrice;
    const entryPct = ((entry - minPrice) / totalRange) * 100;
    const currentPct = ((current - minPrice) / totalRange) * 100;

    const clampedEntryPct = Math.max(0, Math.min(100, entryPct));
    const clampedCurrentPct = Math.max(0, Math.min(100, currentPct));

    let leftPos = clampedEntryPct;
    let widthPct = 0;
    let barColor = 'bg-accentGreen';
    let progressLabel = '';

    if (current >= entry) {
      leftPos = clampedEntryPct;
      widthPct = Math.max(0, clampedCurrentPct - clampedEntryPct);
      barColor = 'bg-accentGreen';
      const pctToTP = ((current - entry) / (tp - entry)) * 100;
      progressLabel = `+${((current / entry - 1) * 100).toFixed(2)}% do entry (${pctToTP.toFixed(0)}% do TP)`;
    } else {
      leftPos = clampedCurrentPct;
      widthPct = Math.max(0, clampedEntryPct - clampedCurrentPct);
      barColor = 'bg-accentRed';
      progressLabel = `${((current / entry - 1) * 100).toFixed(2)}% abaixo do entry`;
    }

    priceProgressHtml = (
      <div className="mt-3">
        <div className="relative text-xs text-slate-500 mb-1 h-4">
          <span className="absolute left-0 text-slate-500/80">Min ${minPrice.toFixed(6)}</span>
          <span className="absolute text-slate-400 font-bold" style={{ left: `${clampedEntryPct}%`, transform: 'translateX(-50%)' }}>Entry ${entry.toFixed(6)}</span>
          <span className="absolute right-0 text-slate-500">TP ${tp.toFixed(6)}</span>
        </div>
        <div className="h-3 bg-slate-700/80 rounded-full relative overflow-hidden">
          {/* Barra de progresso bidirecional */}
          <div 
            className={`absolute top-0 bottom-0 ${barColor} rounded-full transition-all duration-500`} 
            style={{ left: `${leftPos}%`, width: `${widthPct}%` }} 
          />
          {/* Linha do Entrypoint */}
          <div className="absolute top-0 bottom-0 w-0.5 bg-white/60" style={{ left: `${clampedEntryPct}%` }} />
        </div>
        <div className="text-center text-xs text-slate-400 mt-1">
          ${current.toFixed(6)} ({progressLabel})
        </div>
      </div>
    );
  }

  // 2. Barra de Tempo (Time Exit Dinâmico)
  let timeProgressHtml = null;
  if (entryTime && maxHoldHours) {
    const elapsedSeconds = (Date.now() / 1000) - entryTime;
    const elapsedHours = Math.max(0, elapsedSeconds / 3600);
    const timePct = (elapsedHours / maxHoldHours) * 100;
    const clampedTimePct = Math.max(0, Math.min(100, timePct));
    
    let timeBarColor = 'bg-blue-500';
    if (clampedTimePct > 80) timeBarColor = 'bg-amber-500';
    if (clampedTimePct > 95) timeBarColor = 'bg-accentRed';

    timeProgressHtml = (
      <div className="mt-3 border-t border-slate-700/50 pt-2">
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>Tempo decorrido</span>
          <span>Timeout {maxHoldHours}h</span>
        </div>
        <div className="h-2 bg-slate-700/80 rounded-full relative overflow-hidden">
          <div className={`h-full ${timeBarColor} rounded-full transition-all duration-500`} style={{ width: `${clampedTimePct}%` }} />
        </div>
        <div className="text-center text-xs text-slate-400 mt-1">
          {elapsedHours.toFixed(1)}h decorridas ({clampedTimePct.toFixed(0)}% do tempo)
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {priceProgressHtml}
      {timeProgressHtml}
    </div>
  );
}

function TradeChart({ order, onClose }) {
  if (!order.tp_price || !order.entry_price) return null;
  const sl = order.sl_price && order.sl_price > 0 ? order.sl_price : null;
  const tp = order.tp_price;
  const entry = order.entry_price;
  const current = order.current_price || entry;
  
  const data = [
    { name: 'Entrada', price: entry },
    { name: 'Atual', price: current },
    { name: 'TP', price: tp },
  ];
  if (sl) {
    data.unshift({ name: 'SL', price: sl });
  }
  
  const min = sl ? sl * 0.998 : entry * 0.98;
  const max = tp * 1.002;
  
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="bg-slate-900 rounded-xl p-6 max-w-2xl w-full border border-slate-700" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-white font-bold text-lg">{order.symbol}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">&times;</button>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" stroke="#94a3b8" />
            <YAxis domain={[min, max]} stroke="#94a3b8" tickFormatter={v => '$' + v.toFixed(4)} />
            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#fff' }} />
            <ReferenceLine y={entry} stroke="#fbbf24" strokeDasharray="5 5" label={{ value: 'Entry', fill: '#fbbf24', fontSize: 12 }} />
            {sl && <ReferenceLine y={sl} stroke="#ef4444" strokeDasharray="5 5" label={{ value: 'SL', fill: '#ef4444', fontSize: 12 }} />}
            <ReferenceLine y={tp} stroke="#22c55e" strokeDasharray="5 5" label={{ value: 'TP', fill: '#22c55e', fontSize: 12 }} />
            <Line type="monotone" dataKey="price" stroke="#38bdf8" strokeWidth={2} dot={{ r: 4, fill: '#38bdf8' }} />
          </LineChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-3 gap-4 mt-4 text-sm text-slate-400">
          <div><span className="text-red-400">SL:</span> {sl ? `$${sl.toFixed(6)}` : 'Nulo (Sem SL)'}</div>
          <div><span className="text-amber-400">Entry:</span> ${entry.toFixed(6)}</div>
          <div><span className="text-green-400">TP:</span> ${tp.toFixed(6)}</div>
        </div>
      </div>
    </div>
  );
}

export default function Operations() {
  const [data, setData] = useState({ open: [], closed: [], total_open: 0, total_closed: 0, total_pnl: 0, max_hold_hours: 12, spot_balance: 0, spot_balance_free: 0, spot_balance_used: 0, futures_balance: 0, futures_balance_free: 0, futures_balance_used: 0, tier_by_day: {} });

  const TIER_STYLES = {
    'Major':           { bg: 'rgba(234,179,8,0.15)',   border: '#ca8a04', text: '#fde047', icon: '💎' },
    'Strong Alt':      { bg: 'rgba(99,102,241,0.15)',  border: '#6366f1', text: '#a5b4fc', icon: '⚡' },
    'High Volatility': { bg: 'rgba(239,68,68,0.15)',   border: '#ef4444', text: '#fca5a5', icon: '🔥' },
  };
  const tierStyle = (t) => TIER_STYLES[t] || { bg: 'rgba(100,116,139,0.15)', border: '#475569', text: '#94a3b8', icon: '❓' };
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [page, setPage] = useState(1);
  const [btcTrend, setBtcTrend] = useState({ trend: "neutral" });
  const prevOpenCount = useRef(0);

  useEffect(() => {
    let active = true;
    let timeoutId = null;

    const fetchData = () => {
      const t0 = performance.now();
      console.log('[DEBUG] Fetch /api/operations iniciando...');
      fetch(`/api/operations?page=${page}&limit=50`)
        .then(res => {
          console.log(`[DEBUG] HTTP ${res.status} em ${(performance.now() - t0).toFixed(0)}ms`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then(resData => {
          const elapsed = (performance.now() - t0).toFixed(0);
          console.log(`[DEBUG] Dados recebidos em ${elapsed}ms:`, {
            open: resData.open?.length,
            closed: resData.closed?.length,
            openDetails: resData.open?.map(o => ({
              sym: o.symbol, score: o.score, rsi: o.rsi,
              current: o.current_price, tp: o.tp_price, sl: o.sl_price,
              entry_time: o.entry_time
            }))
          });
          if (!active) return;
          if (resData.open.length > prevOpenCount.current && prevOpenCount.current > 0) {
            playNewTradeSound();
          }
          prevOpenCount.current = resData.open.length;
          setData(resData);
          setLoading(false);
          // Próximo fetch 10s APÓS completar (evita pileup de requests)
          timeoutId = setTimeout(fetchData, 10000);
        })
        .catch(err => {
          console.error(`[DEBUG] ERRO em ${(performance.now() - t0).toFixed(0)}ms:`, err);
          if (!active) return;
          setLoading(false);
          timeoutId = setTimeout(fetchData, 10000);
        });
    };
    fetchData();
    return () => {
      active = false;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [page]);

  useEffect(() => {
    const fetchTrend = () => {
      fetch('/api/btc-trend').then(r => r.json()).then(setBtcTrend).catch(() => {});
    };
    fetchTrend();
    const id = setInterval(fetchTrend, 60000);
    return () => clearInterval(id);
  }, []);

  if (loading) return <div className="p-6"><Spinner /></div>;

  const totalInvested = data.open.reduce((sum, o) => sum + (o.entry_price * o.quantity), 0);
  const totalCurrent = data.open.reduce((sum, o) => sum + ((o.current_price || o.entry_price) * o.quantity), 0);
  const totalReturn = totalCurrent - totalInvested;

  // Agrupamento de Histórico por Dia
  const dailyGroups = {};
  data.closed.forEach(order => {
    const day = order.updated_at ? order.updated_at.split(' ')[0] : 'Sem data';
    if (!dailyGroups[day]) {
      dailyGroups[day] = {
        day,
        orders: [],
        pnl: 0,
        wins: 0,
        total: 0
      };
    }
    const invested = order.entry_price * order.quantity;
    const pnl_dollar = (order.pnl_pct / 100) * invested;
    dailyGroups[day].orders.push(order);
    dailyGroups[day].pnl += pnl_dollar;
    dailyGroups[day].total += 1;
    if (order.pnl_pct > 0) {
      dailyGroups[day].wins += 1;
    }
  });

  const sortedDays = Object.keys(dailyGroups).sort((a, b) => {
    const [dayA, monthA] = a.split('/');
    const [dayB, monthB] = b.split('/');
    if (monthA !== monthB) return monthB.localeCompare(monthA);
    return dayB.localeCompare(dayA);
  });

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-white mb-6">Operações</h1>
      
      {/* BTC Trend Banner */}
      {(() => {
        const t = btcTrend;
        if (!t.trend) return null;
        const isBull = t.trend === 'bull';
        const isBear = t.trend === 'bear';
        return (
          <div style={{
            background: isBull ? 'rgba(16,185,129,0.1)' : isBear ? 'rgba(239,68,68,0.1)' : 'rgba(100,116,139,0.05)',
            border: `1px solid ${isBull ? 'rgba(16,185,129,0.3)' : isBear ? 'rgba(239,68,68,0.3)' : 'rgba(100,116,139,0.2)'}`,
            borderRadius: '12px', padding: '12px 20px', marginBottom: '20px',
            display: 'flex', alignItems: 'center', gap: '12px',
          }}>
            <span style={{ fontSize: '20px' }}>{isBull ? '🐂' : isBear ? '🐻' : '➖'}</span>
            <span style={{ color: '#e2e8f0', fontWeight: 700, fontSize: '14px' }}>
              {isBull ? 'BTC Bull' : isBear ? 'BTC Bear' : 'BTC Neutral'}
            </span>
            <span style={{ color: '#64748b', fontSize: '13px' }}>
              ${t.btc_price?.toLocaleString()} | SMA(12) ${t.sma?.toLocaleString()} | {t.pct > 0 ? '+' : ''}{t.pct}%
            </span>
            <span style={{ color: '#475569', fontSize: '12px', marginLeft: 'auto' }}>
              {isBull ? 'Só LONG' : isBear ? 'Só SHORT' : 'Ambos'}
            </span>
          </div>
        );
      })()}

      {selectedOrder && <TradeChart order={selectedOrder} onClose={() => setSelectedOrder(null)} />}

      {/* Card de Resumo */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 mb-6 grid grid-cols-2 md:grid-cols-6 gap-4">
        <div>
          <div className="text-slate-400 text-sm">Em operação</div>
          <div className="text-white text-xl font-bold">${totalInvested.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-slate-400 text-sm">Valor atual</div>
          <div className="text-white text-xl font-bold">${totalCurrent.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-slate-400 text-sm">Retorno</div>
          <div className={`text-xl font-bold ${totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {totalReturn >= 0 ? '+' : ''}{totalReturn.toFixed(4)} USDT
          </div>
        </div>
        <div>
          <div className="text-slate-400 text-sm">% Retorno</div>
          <div className={`text-xl font-bold ${totalReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {totalReturn >= 0 ? '+' : ''}{(totalInvested > 0 ? (totalReturn / totalInvested * 100) : 0).toFixed(2)}%
          </div>
        </div>
        <div>
          <div className="text-slate-400 text-sm">Saldo Spot</div>
          <div className="text-blue-400 text-xl font-bold">${data.spot_balance}</div>
          <div className="text-xs text-slate-500 mt-1">Livre: ${data.spot_balance_free} | Uso: ${data.spot_balance_used} | BNB: ${data.bnb_balance}</div>
        </div>
        <div>
          <div className="text-slate-400 text-sm">Saldo Futures</div>
          <div className="text-purple-400 text-xl font-bold">${data.futures_balance}</div>
          <div className="text-xs text-slate-500 mt-1">Livre: ${data.futures_balance_free} | Uso: ${data.futures_balance_used}</div>
        </div>
      </div>

      {/* Ordens Abertas */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-white mb-4">Ordens Abertas ({data.open.length})</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.open.map((order) => {
            const current = order.current_price;
            const isProfit = current && current >= order.entry_price;
            const pnlDollar = current ? (current - order.entry_price) * order.quantity : 0;
            const pnlPct = current ? ((current / order.entry_price) - 1) * 100 : 0;
            const wlInfo = order.coin_total > 0 
              ? <span className={`text-xs ${order.coin_wins >= order.coin_losses ? 'text-green-400' : 'text-red-400'}`}>
                  ({order.coin_wins}W/{order.coin_losses}L)
                </span>
              : null;

            const elapsedSeconds = order.entry_time ? (Date.now() / 1000) - order.entry_time : 0;
            const elapsedHours = elapsedSeconds / 3600;
            const remainingHours = Math.max(0, data.max_hold_hours - elapsedHours);
            const remainingText = order.entry_time 
              ? `${remainingHours.toFixed(1)}h restam`
              : null;

            const marketTag = order.is_futures 
              ? <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-semibold border border-blue-500/30">FUTURES {order.leverage}x</span>
              : <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-600/20 text-slate-400 font-semibold border border-slate-600/30">SPOT</span>;

            const directionTag = order.direction === 'SHORT'
              ? <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 font-semibold border border-red-500/30">SHORT</span>
              : <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-semibold border border-blue-500/30">LONG</span>;

            const ts = tierStyle(order.tier);
            const tierTag = order.tier ? (
              <span style={{ background: ts.bg, border: `1px solid ${ts.border}`, color: ts.text }}
                className="text-[10px] px-2 py-0.5 rounded-full font-semibold">
                {ts.icon} {order.tier}
              </span>
            ) : null;

            return (
              <div key={order.id}
                onClick={() => setSelectedOrder(order)}
                 className={`bg-slate-800 p-5 rounded-xl border cursor-pointer transition-all hover:scale-[1.02] flex flex-col justify-between ${isProfit ? 'border-green-500/30 hover:border-green-500' : 'border-red-500/30 hover:border-red-500'}`}
              >
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-white font-bold text-lg">{order.symbol}</span>
                      {order.block_id && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-semibold border border-purple-500/30 uppercase">
                          {order.block_id}
                        </span>
                      )}
                      {marketTag}
                      {directionTag}
                      {tierTag}
                      {wlInfo}
                    </div>
                    <div className="flex items-center gap-2">
                      {remainingText && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-700 text-slate-300" title="Tempo restante para Time Exit">
                          {remainingText}
                        </span>
                      )}
                      <span className={`text-xs px-2 py-1 rounded-full uppercase ${isProfit ? 'bg-accentGreen/20 text-accentGreen' : 'bg-accentRed/20 text-accentRed'}`}>
                        {isProfit ? 'Lucro' : 'Perda'}
                      </span>
                    </div>
                  </div>
                  
                  {/* Mini-card de PnL */}
                  <div className={`text-center py-4 my-2 rounded-lg ${isProfit ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                    <div className={`text-3xl font-bold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                      {isProfit ? '+' : ''}{pnlDollar.toFixed(4)} USDT
                    </div>
                    <div className={`text-sm mt-1 ${isProfit ? 'text-green-300' : 'text-red-300'}`}>
                      {isProfit ? '+' : ''}{pnlPct.toFixed(2)}% da entrada
                    </div>
                  </div>
                </div>

                <div>
                  <div className="text-xs text-slate-500 space-y-1 mb-2">
                    <div className="flex justify-between"><span>Qtd:</span><span className="text-white">{order.quantity}</span></div>
                    <div className="flex justify-between"><span>Entrada:</span><span className="text-white">${order.entry_price}</span></div>
                    <div className="flex justify-between"><span>Atual:</span><span className={`font-bold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>${current?.toFixed(6) || '...'}</span></div>
                    <div className="flex justify-between border-t border-slate-700/50 pt-1 mt-1 text-[11px]">
                      <span>Métricas de Entrada:</span>
                      <span className="text-slate-300">
                        Score: <strong className="text-white">{order.score !== undefined && order.score !== null ? order.score.toFixed(2) : '-'}</strong> | 
                        RSI: <strong className="text-white">{order.rsi !== undefined && order.rsi !== null ? order.rsi.toFixed(1) : '-'}</strong>
                      </span>
                    </div>
                  </div>
                  <SLTPBar 
                    current={current} 
                    sl={order.sl_price} 
                    tp={order.tp_price} 
                    entry={order.entry_price}
                    entryTime={order.entry_time}
                    maxHoldHours={data.max_hold_hours}
                  />
                </div>
              </div>
            );
          })}
          {data.open.length === 0 && (
            <p className="text-slate-500 col-span-full">Nenhuma ordem aberta.</p>
          )}
        </div>
      </div>

      {/* Ordens Fechadas com Cabeçalhos por Dia */}
      <div>
        <h2 className="text-xl font-bold text-white mb-4">Histórico ({data.total_closed})</h2>
        <div className="text-slate-400 text-sm mb-6">PnL total geral: <span className={`font-bold ${data.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>{data.total_pnl >= 0 ? '+' : ''}${data.total_pnl}</span></div>
        
        <div className="space-y-8">
          {sortedDays.map(dayKey => {
            const group = dailyGroups[dayKey];
            const isDayProfit = group.pnl >= 0;
            const winRate = group.total > 0 ? (group.wins / group.total * 100) : 0;
            return (
              <div key={dayKey} className="border-l-2 border-slate-700 pl-4 py-1">
                {/* Cabeçalho do Dia */}
                <div className="flex flex-wrap items-center justify-between gap-4 mb-3 bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-white">{dayKey}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                      {group.total} trades ({winRate.toFixed(0)}% WR)
                    </span>
                  </div>
                  <span className={`font-bold text-base ${isDayProfit ? 'text-green-400' : 'text-red-400'}`}>
                    Resultado: {isDayProfit ? '+' : ''}${group.pnl.toFixed(4)} USDT
                  </span>
                </div>

                {/* Breakdown por Tier */}
                {data.tier_by_day && data.tier_by_day[dayKey] && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {data.tier_by_day[dayKey].map(td => {
                      const ts = tierStyle(td.tier);
                      const isPnlPos = td.pnl_money >= 0;
                      return (
                        <div key={td.tier}
                          style={{ background: ts.bg, border: `1px solid ${ts.border}` }}
                          className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs"
                        >
                          <span style={{ color: ts.text }} className="font-bold">{ts.icon} {td.tier}</span>
                          <span className="text-green-400 font-semibold">{td.wins}W</span>
                          <span className="text-red-400 font-semibold">{td.losses}L</span>
                          <span style={{ color: isPnlPos ? '#10b981' : '#ef4444' }} className="font-bold">
                            {isPnlPos ? '+' : ''}{td.pnl_money.toFixed(4)} USDT
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Cards do Dia */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {group.orders.map((order) => {
                    const isWin = order.pnl_pct > 0;
                    const invested = order.entry_price * order.quantity;
                    const pnl_dollar = (order.pnl_pct / 100) * invested;
                    let badgeText = order.exit_reason || 'Encerrado';
                    if (order.exit_reason === 'STOP_LOSS' && isWin) badgeText = 'Trailing Stop';

                    const marketTag = order.is_futures 
                      ? <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-semibold border border-blue-500/20">FUTURES {order.leverage}x</span>
                      : <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-600/20 text-slate-400 font-semibold border border-slate-600/20">SPOT</span>;

                    const directionTag = order.direction === 'SHORT'
                      ? <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-semibold border border-red-500/20">SHORT</span>
                      : <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-semibold border border-blue-500/20">LONG</span>;

                    const ts2 = tierStyle(order.tier);
                    const closedTierTag = order.tier ? (
                      <span style={{ background: ts2.bg, border: `1px solid ${ts2.border}`, color: ts2.text }}
                        className="text-[9px] px-1.5 py-0.5 rounded font-semibold">
                        {ts2.icon} {order.tier}
                      </span>
                    ) : null;

                    return (
                      <div key={order.id} className={`bg-slate-800 p-5 rounded-xl border ${isWin ? 'border-accentGreen/30' : 'border-accentRed/30'}`}>
                        <div className="flex justify-between items-center mb-3">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-white font-bold text-lg">{order.symbol}</span>
                            {order.block_id && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-semibold border border-purple-500/30 uppercase">
                          {order.block_id}
                        </span>
                      )}
                      {marketTag}
                            {directionTag}
                            {closedTierTag}
                          </div>
                          <span className={`text-xs px-2 py-1 rounded-full uppercase ${isWin ? 'bg-accentGreen/20 text-accentGreen' : 'bg-accentRed/20 text-accentRed'}`}>
                            {badgeText}
                          </span>
                        </div>
                        <div className="text-sm text-slate-400 space-y-1">
                          <div className="flex justify-between">
                            <span>Resultado:</span>
                            <span className={`font-bold ${isWin ? 'text-accentGreen' : 'text-accentRed'}`}>
                              {isWin ? '+' : ''}{pnl_dollar.toFixed(4)} USDT ({isWin ? '+' : ''}{order.pnl_pct?.toFixed(2)}%)
                            </span>
                          </div>
                          <div className="flex justify-between"><span>Entrada:</span><span className="text-white">${order.entry_price}</span></div>
                          <div className="flex justify-between"><span>Saída:</span><span className="text-white">${order.exit_price}</span></div>
                          <div className="flex justify-between"><span>Fechado:</span><span className="text-white">{order.updated_at.split(' ')[1]}</span></div>
                          <div className="flex justify-between border-t border-slate-700/50 pt-1 mt-1 text-[11px]">
                            <span>Métricas:</span>
                            <span className="text-slate-300">
                              Score: <strong className="text-white">{order.score !== undefined && order.score !== null ? order.score.toFixed(2) : '-'}</strong> | 
                              RSI: <strong className="text-white">{order.rsi !== undefined && order.rsi !== null ? order.rsi.toFixed(1) : '-'}</strong>
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
          {data.closed.length === 0 && (
            <p className="text-slate-500">Nenhuma ordem fechada no histórico.</p>
          )}
        </div>

        {/* Pagination */}
        <div className="flex justify-center gap-3 mt-8">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-4 py-2 bg-slate-800 text-white rounded-lg border border-slate-700 hover:border-accentGreen disabled:opacity-50">
            Anterior
          </button>
          <span className="px-4 py-2 text-slate-400">Página {page}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={data.closed.length < 50}
            className="px-4 py-2 bg-slate-800 text-white rounded-lg border border-slate-700 hover:border-accentGreen disabled:opacity-50">
            Próxima
          </button>
        </div>
      </div>
    </div>
  );
}
