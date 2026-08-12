import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

export default function Dashboard() {
  const [data, setData] = useState({
    total_pnl_money: 0,
    win_rate: 0,
    total_closed: 0,
    wins: 0,
    losses: 0,
    active_positions: [],
    patrimony: 0,
    spot_balance: 0,
    spot_balance_free: 0,
    spot_balance_used: 0,
    futures_balance: 0,
    futures_balance_free: 0,
    futures_balance_used: 0,
    bnb_balance: 0,
    rankings: { best: [], worst: [], most_traded: [] },
    curve: []
  });
  const [loading, setLoading] = useState(true);
  const [btcTrend, setBtcTrend] = useState({ trend: "neutral", btc_price: 0, sma: 0, pct: 0 });

  useEffect(() => {
    fetch('/api/dashboard')
      .then(res => res.json())
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(err => console.error(err));

    fetch('/api/btc-trend')
      .then(res => res.json())
      .then(setBtcTrend)
      .catch(() => {});

    const trendInterval = setInterval(() => {
      fetch('/api/btc-trend')
        .then(res => res.json())
        .then(setBtcTrend)
        .catch(() => {});
    }, 60000);
    return () => clearInterval(trendInterval);
  }, []);

  if (loading) {
    return <div className="p-6 text-white">Carregando dados do Dashboard...</div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-white mb-6">Dashboard</h1>
      
       {/* KPIs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-7 gap-6 mb-8">
        {/* Card 0 - BTC Trend */}
        {(() => {
          const t = btcTrend;
          const isBull = t.trend === 'bull';
          const isBear = t.trend === 'bear';
          const bg = isBull ? 'rgba(16,185,129,0.15)' : isBear ? 'rgba(239,68,68,0.15)' : 'rgba(100,116,139,0.1)';
          const border = isBull ? '#10b981' : isBear ? '#ef4444' : '#64748b';
          const icon = isBull ? '🐂' : isBear ? '🐻' : '➖';
          const label = isBull ? 'BTC Bull' : isBear ? 'BTC Bear' : 'BTC Neutral';
          return (
            <div className="bg-slate-800 p-6 rounded-xl border transition-colors cursor-pointer" style={{ borderColor: border, background: bg }}>
              <p className="text-slate-400 text-sm font-medium">{icon} {label}</p>
              <p className="text-2xl font-bold mt-2" style={{ color: isBull ? '#10b981' : isBear ? '#ef4444' : '#94a3b8' }}>
                ${t.btc_price?.toLocaleString()}
              </p>
              <span className="text-slate-400 text-xs font-medium">
                SMA({12}) ${t.sma?.toLocaleString()} | {t.pct > 0 ? '+' : ''}{t.pct}%
              </span>
            </div>
          );
        })()}

        {/* Card 1 - Patrimônio */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 hover:border-accentGreen transition-colors cursor-pointer">
          <p className="text-slate-400 text-sm font-medium">Patrimônio Total</p>
          <p className="text-2xl font-bold text-white mt-2">${data.patrimony}</p>
          <span className="text-slate-400 text-xs font-medium">Spot + Futures</span>
        </div>

        {/* Card 2 - Saldo Spot */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 hover:border-blue-500 transition-colors cursor-pointer">
          <p className="text-slate-400 text-sm font-medium">Saldo Spot (USDT)</p>
          <p className="text-2xl font-bold text-blue-400 mt-2">${data.spot_balance}</p>
          <span className="text-slate-400 text-xs font-medium">Livre: ${data.spot_balance_free} | Em uso: ${data.spot_balance_used} | BNB: ${data.bnb_balance}</span>
        </div>

        {/* Card 3 - Saldo Futures */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 hover:border-purple-500 transition-colors cursor-pointer">
          <p className="text-slate-400 text-sm font-medium">Saldo Futures (USDT)</p>
          <p className="text-2xl font-bold text-purple-400 mt-2">${data.futures_balance}</p>
          <span className="text-slate-400 text-xs font-medium">Livre: ${data.futures_balance_free} | Em uso: ${data.futures_balance_used}</span>
        </div>
        
        {/* Card 4 - BNB Taxas */}
        <div className="bg-slate-800 p-6 rounded-xl border border-amber-500/30 hover:border-amber-500 transition-colors cursor-pointer">
          <p className="text-slate-400 text-sm font-medium">BNB (Taxas)</p>
          <p className="text-2xl font-bold text-amber-400 mt-2">${data.bnb_balance}</p>
          <span className="text-slate-400 text-xs font-medium">Colchão p/ taxas</span>
        </div>
        
        {/* Card 5 - Lucro Líquido */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 hover:border-accentGreen transition-colors cursor-pointer">
          <p className="text-slate-400 text-sm font-medium">Lucro Líquido (DB)</p>
          <p className={`text-2xl font-bold mt-2 ${data.total_pnl_money >= 0 ? 'text-accentGreen' : 'text-accentRed'}`}>
            {data.total_pnl_money >= 0 ? '+' : ''}${data.total_pnl_money}
          </p>
          <span className="text-accentGreen text-xs font-medium">Soma real de lucros</span>
        </div>
        
        {/* Card 6 - Win Rate e Trades */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 hover:border-accentGreen transition-colors cursor-pointer">
          <p className="text-slate-400 text-sm font-medium">Win Rate Geral</p>
          <p className="text-2xl font-bold text-white mt-2">{data.win_rate}%</p>
          <span className="text-slate-400 text-xs font-medium">{data.total_closed} trades ({data.wins}W/{data.losses}L)</span>
        </div>
      </div>

      {/* Charts Section */}
      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 mb-8">
        <h2 className="text-xl font-bold text-white mb-4">Curva de Patrimônio (Evolução em Dólar)</h2>
        <div className="h-64">
          {data.curve?.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.curve}>
                <XAxis dataKey="date" stroke="#64748b" />
                <YAxis stroke="#64748b" unit=" $" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff' }} />
                <Line type="monotone" dataKey="pnl" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full border-2 border-dashed border-slate-700 rounded-lg">
              <p className="text-slate-500">Nenhum dado histórico para gerar a curva.</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Active Positions */}
      <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 mb-8">
        <h2 className="text-xl font-bold text-white mb-4">Posições Abertas Agora</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-slate-300">
            <thead className="text-slate-500 border-b border-slate-700">
              <tr>
                <th className="pb-3">Moeda</th>
                <th className="pb-3">Preço Entrada</th>
                <th className="pb-3">Quantidade</th>
                <th className="pb-3">Investido</th>
                <th className="pb-3">Aberto em</th>
              </tr>
            </thead>
            <tbody>
              {data.active_positions.map((pos, index) => (
                <tr key={index} className="border-b border-slate-700 last:border-b-0">
                  <td className="py-4 font-medium text-white">{pos.symbol}</td>
                  <td className="py-4">${pos.entry_price}</td>
                  <td className="py-4">{pos.quantity}</td>
                  <td className="py-4">${(pos.entry_price * pos.quantity).toFixed(2)}</td>
                  <td className="py-4">{pos.created_at}</td>
                </tr>
              ))}
              {data.active_positions.length === 0 && (
                <tr>
                  <td colSpan="5" className="py-4 text-center text-slate-500">Nenhuma posição aberta no banco de dados.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rankings Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Melhores Moedas */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 hover:border-accentGreen transition-colors">
          <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <span className="text-accentGreen">🏆</span> Melhores Moedas
          </h2>
          <div className="space-y-3">
            {data.rankings.best.map((coin, index) => (
              <div key={index} className="flex justify-between items-center text-sm border-b border-slate-700 pb-2 last:border-b-0 last:pb-0">
                <span className="text-white font-medium">{coin.symbol}</span>
                <span className={`font-bold ${coin.pnl >= 0 ? 'text-accentGreen' : 'text-accentRed'}`}>
                  {coin.pnl >= 0 ? '+' : ''}${coin.pnl}
                </span>
              </div>
            ))}
            {data.rankings.best.length === 0 && <p className="text-slate-500 text-sm">Sem dados.</p>}
          </div>
        </div>

        {/* Piores Moedas */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 hover:border-accentRed transition-colors">
          <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <span className="text-accentRed">📉</span> Piores Moedas
          </h2>
          <div className="space-y-3">
            {data.rankings.worst.map((coin, index) => (
              <div key={index} className="flex justify-between items-center text-sm border-b border-slate-700 pb-2 last:border-b-0 last:pb-0">
                <span className="text-white font-medium">{coin.symbol}</span>
                <span className={`font-bold ${coin.pnl >= 0 ? 'text-accentGreen' : 'text-accentRed'}`}>
                  {coin.pnl >= 0 ? '+' : ''}${coin.pnl}
                </span>
              </div>
            ))}
            {data.rankings.worst.length === 0 && <p className="text-slate-500 text-sm">Sem dados.</p>}
          </div>
        </div>

        {/* Mais Operadas */}
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 hover:border-blue-500 transition-colors">
          <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <span className="text-blue-400">🔄</span> Mais Operadas
          </h2>
          <div className="space-y-3">
            {data.rankings.most_traded.map((coin, index) => (
              <div key={index} className="flex justify-between items-center text-sm border-b border-slate-700 pb-2 last:border-b-0 last:pb-0">
                <span className="text-white font-medium">{coin.symbol}</span>
                <span className="text-slate-400">
                  <span className="text-accentGreen">{coin.wins}W</span> / <span className="text-accentRed">{coin.losses}L</span> ({coin.total} total)
                </span>
              </div>
            ))}
            {data.rankings.most_traded.length === 0 && <p className="text-slate-500 text-sm">Sem dados.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
