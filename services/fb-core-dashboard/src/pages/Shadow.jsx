import React, { useState, useEffect } from 'react';

const TIER_COLORS = {
  'Strong Alt': { bg: 'rgba(99,102,241,0.15)', border: '#6366f1', badge: '#6366f1', text: '#a5b4fc' },
  'Major': { bg: 'rgba(234,179,8,0.12)', border: '#eab308', badge: '#eab308', text: '#fde047' },
  'High Volatility': { bg: 'rgba(239,68,68,0.12)', border: '#ef4444', badge: '#ef4444', text: '#fca5a5' },
  'Desconhecido': { bg: 'rgba(100,116,139,0.15)', border: '#64748b', badge: '#64748b', text: '#94a3b8' },
};

const HOUR_WINDOW_ICONS = {
  'Madrugada (0–6h)': '🌙',
  'Manhã (6–12h)': '🌅',
  'Tarde (12–18h)': '☀️',
  'Noite (18–24h)': '🌆',
};

function pnlColor(val) {
  if (val === null || val === undefined) return '#64748b';
  return val > 0 ? '#10b981' : val < 0 ? '#ef4444' : '#64748b';
}

function pnlSign(val) {
  if (val === null || val === undefined) return '–';
  return (val > 0 ? '+' : '') + val.toFixed(3) + '%';
}

function HeatmapCell({ hour, avg_pnl, count }) {
  const hasData = count > 0;
  let bg = 'rgba(51,65,85,0.5)';
  let textColor = '#475569';
  if (hasData && avg_pnl !== null) {
    const intensity = Math.min(Math.abs(avg_pnl) / 1.0, 1);
    if (avg_pnl > 0) {
      bg = `rgba(16,185,129,${0.15 + intensity * 0.55})`;
      textColor = '#6ee7b7';
    } else {
      bg = `rgba(239,68,68,${0.15 + intensity * 0.55})`;
      textColor = '#fca5a5';
    }
  }

  return (
    <div
      title={hasData ? `${hour}h UTC | Média: ${pnlSign(avg_pnl)} | ${count} sims` : `${hour}h UTC | Sem dados`}
      style={{
        background: bg,
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '6px',
        padding: '6px 4px',
        textAlign: 'center',
        minWidth: '36px',
        cursor: 'default',
        transition: 'transform 0.15s',
      }}
      onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.12)'}
      onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
    >
      <div style={{ fontSize: '10px', color: '#64748b', marginBottom: '2px' }}>{hour}h</div>
      {hasData && avg_pnl !== null
        ? <div style={{ fontSize: '9px', fontWeight: 700, color: textColor }}>{avg_pnl > 0 ? '+' : ''}{avg_pnl.toFixed(2)}</div>
        : <div style={{ fontSize: '9px', color: '#334155' }}>–</div>
      }
    </div>
  );
}

function RSIBar({ range, avg_pnl, win_rate, count }) {
  const maxAbsPnl = 0.5;
  const pct = Math.min(Math.abs(avg_pnl) / maxAbsPnl * 100, 100);
  const color = avg_pnl >= 0 ? '#10b981' : '#ef4444';

  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
        <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: '14px' }}>RSI {range}</span>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <span style={{ color: '#94a3b8', fontSize: '12px' }}>{count} sims</span>
          <span style={{ color: '#94a3b8', fontSize: '12px' }}>WR: {win_rate}%</span>
          <span style={{ color, fontWeight: 700, fontSize: '14px' }}>{pnlSign(avg_pnl)}</span>
        </div>
      </div>
      <div style={{ background: 'rgba(51,65,85,0.6)', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
        <div style={{
          width: count > 0 ? `${pct}%` : '0%',
          height: '100%',
          background: color,
          borderRadius: '4px',
          transition: 'width 0.6s ease',
        }} />
      </div>
    </div>
  );
}

function SLTPRow({ rank, config, avg_pnl, win_rate, count }) {
  const isPos = avg_pnl >= 0;
  const medals = ['🥇', '🥈', '🥉'];
  const medal = rank < 3 ? medals[rank] : `${rank + 1}º`;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '12px 16px',
      borderRadius: '10px',
      marginBottom: '8px',
      background: isPos ? 'rgba(16,185,129,0.07)' : 'rgba(239,68,68,0.07)',
      border: `1px solid ${isPos ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
      transition: 'background 0.2s',
    }}>
      <span style={{ fontSize: '18px', minWidth: '32px', textAlign: 'center' }}>{medal}</span>
      <span style={{ flex: 1, color: '#e2e8f0', fontWeight: 600, fontSize: '14px' }}>{config}</span>
      <span style={{ color: '#94a3b8', fontSize: '12px', minWidth: '70px', textAlign: 'right' }}>{count} trades</span>
      <span style={{ color: '#94a3b8', fontSize: '12px', minWidth: '60px', textAlign: 'right' }}>WR {win_rate}%</span>
      <span style={{
        color: isPos ? '#10b981' : '#ef4444',
        fontWeight: 700,
        fontSize: '15px',
        minWidth: '80px',
        textAlign: 'right',
      }}>{pnlSign(avg_pnl)}</span>
    </div>
  );
}

export default function Shadow() {
  const [data, setData] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sltpTab, setSltpTab] = useState('all');
  const [minModelScore, setMinModelScore] = useState(0.50);
  const [activeTierTab, setActiveTierTab] = useState('Major');

  useEffect(() => {
    // Carregar configurações primeiro
    fetch('/api/settings')
      .then(res => res.json())
      .then(setSettings)
      .catch(err => console.error("Erro ao carregar settings no Shadow:", err));
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/shadow?min_model_score=${minModelScore}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(d => { setData(d); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, [minModelScore]);

  if (loading) return (
    <div style={{ padding: '40px', textAlign: 'center' }}>
      <div style={{ color: '#6366f1', fontSize: '32px', marginBottom: '12px' }}>⚗️</div>
      <div style={{ color: '#94a3b8', fontSize: '16px' }}>Carregando laboratório de estratégias...</div>
    </div>
  );

  if (error) return (
    <div style={{ padding: '40px', textAlign: 'center' }}>
      <div style={{ color: '#ef4444' }}>Erro ao carregar dados: {error}</div>
    </div>
  );

  const tierData = data?.tiers?.[activeTierTab] || null;

  const noData = !tierData || tierData.total_simulations === 0;
  const rankingSltp = tierData?.ranking_sltp || [];
  const rankingRsi = tierData?.ranking_rsi || [];
  const rankingHour = tierData?.ranking_hour || [];
  const rankingSymbol = tierData?.ranking_symbol || [];
  const bestCombo = tierData?.best_combo;
  const bestScores = tierData?.best_scores || [];
  const rankingHourWindows = tierData?.ranking_hour_windows || [];
  
  const rankingTier = data?.ranking_tier || [];

  // Agrupar horas em janelas para o heatmap
  const heatmapRows = [
    { label: '🌙 Madrugada', hours: rankingHour.slice(0, 6) },
    { label: '🌅 Manhã', hours: rankingHour.slice(6, 12) },
    { label: '☀️ Tarde', hours: rankingHour.slice(12, 18) },
    { label: '🌆 Noite', hours: rankingHour.slice(18, 24) },
  ];

  const sectionStyle = {
    background: 'rgba(15,23,42,0.6)',
    border: '1px solid rgba(71,85,105,0.4)',
    borderRadius: '16px',
    padding: '24px',
    marginBottom: '24px',
    backdropFilter: 'blur(8px)',
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>

      {/* Header */}
      <div style={{ marginBottom: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <span style={{ fontSize: '28px' }}>⚗️</span>
            <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#f1f5f9', margin: 0 }}>
              Shadow LONG (modelo)
            </h1>
            {!noData && (
              <span style={{
                background: 'rgba(99,102,241,0.2)',
                border: '1px solid rgba(99,102,241,0.4)',
                color: '#a5b4fc',
                fontSize: '12px',
                fontWeight: 600,
                padding: '3px 10px',
                borderRadius: '20px',
              }}>
                {data.total_simulations.toLocaleString()} simulações
              </span>
            )}
          </div>
          <p style={{ color: '#64748b', fontSize: '14px', margin: 0 }}>
            Laboratório paralelo de estratégias — análise por configuração de SL/TP, Tier, RSI de entrada e horário.
          </p>
        </div>

        {/* Score Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(15,23,42,0.4)', border: '1px solid rgba(71,85,105,0.4)', padding: '6px 12px', borderRadius: '10px' }}>
          <span style={{ color: '#94a3b8', fontSize: '13px', fontWeight: 500 }}>Score Mínimo:</span>
          <select 
            value={minModelScore} 
            onChange={(e) => setMinModelScore(parseFloat(e.target.value))}
            style={{
              background: '#0f172a',
              color: '#f1f5f9',
              border: '1px solid rgba(71,85,105,0.6)',
              borderRadius: '6px',
              padding: '4px 8px',
              fontSize: '13px',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="0.0">Todos (0.00)</option>
            <option value="0.40">0.40</option>
            <option value="0.45">0.45</option>
            <option value="0.50">0.50</option>
            <option value="0.60">0.60</option>
            <option value="0.65">0.65</option>
            <option value="0.70">0.70</option>
            <option value="0.73">0.73 (Prod)</option>
          </select>
        </div>
      </div>

      {/* Tier Selector Tabs */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '24px', background: 'rgba(15,23,42,0.3)', padding: '6px', borderRadius: '12px', border: '1px solid rgba(71,85,105,0.2)', overflowX: 'auto' }}>
        {['Major', 'Strong Alt', 'High Volatility'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTierTab(tab)}
            style={{
              flex: 1,
              padding: '10px 16px',
              borderRadius: '8px',
              background: activeTierTab === tab ? 'rgba(99,102,241,0.2)' : 'transparent',
              color: activeTierTab === tab ? '#a5b4fc' : '#94a3b8',
              border: activeTierTab === tab ? '1px solid rgba(99,102,241,0.4)' : '1px solid transparent',
              fontWeight: activeTierTab === tab ? 700 : 500,
              fontSize: '14px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s'
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Regimes Status Banner */}
      {settings && (
        <div style={{
          background: 'rgba(15,23,42,0.4)',
          border: '1px solid rgba(71,85,105,0.2)',
          borderRadius: '12px',
          padding: '12px 18px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backdropFilter: 'blur(8px)'
        }}>
          <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 500 }}>
            Configuração de Regimes para <strong>LONG {activeTierTab}</strong>:
          </span>
          <div style={{ display: 'flex', gap: '6px' }}>
            {['bull', 'bear', 'neutral'].map(r => {
              const allowed = (settings[`long_${activeTierTab}_allowed_regimes`] ?? ['bull', 'neutral']).includes(r);
              return (
                <span 
                  key={r}
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '6px',
                    background: allowed ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                    color: allowed ? '#86efac' : '#fca5a5',
                    border: `1px solid ${allowed ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`
                  }}
                >
                  {r === 'bull' ? '🐂 BULL' : r === 'bear' ? '🐻 BEAR' : '➖ LATERAL'} {allowed ? '✅' : '❌'}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {noData ? (
        <div style={{ ...sectionStyle, textAlign: 'center', padding: '48px' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔬</div>
          <div style={{ color: '#94a3b8', fontSize: '16px' }}>
            Nenhum dado de simulação disponível ainda.
            <br />
            <span style={{ color: '#64748b', fontSize: '13px' }}>O simulador processa trades com mais de 12h automaticamente.</span>
          </div>
        </div>
      ) : (
        <>

          {/* Best Combo Insight */}
          {bestCombo && (
            <div style={{
              background: 'linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(139,92,246,0.15) 100%)',
              border: '1px solid rgba(139,92,246,0.4)',
              borderRadius: '16px',
              padding: '20px 24px',
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              gap: '20px',
            }}>
              <div style={{ fontSize: '36px' }}>🏆</div>
              <div style={{ flex: 1 }}>
                <div style={{ color: '#c4b5fd', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
                  Melhor Combinação Detectada
                </div>
                <div style={{ color: '#f1f5f9', fontSize: '18px', fontWeight: 700, marginBottom: '4px' }}>
                  {bestCombo.label}
                </div>
                <div style={{ color: '#94a3b8', fontSize: '13px' }}>
                  Baseado em {bestCombo.count} simulações com {bestCombo.win_rate}% de acerto
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ color: '#10b981', fontSize: '28px', fontWeight: 800 }}>
                  {pnlSign(bestCombo.avg_pnl)}
                </div>
                <div style={{ color: '#6ee7b7', fontSize: '12px' }}>PnL médio / simulação</div>
              </div>
            </div>
          )}

          {/* Premium Reference Calibration Table for LONG */}
          <div style={{
            background: 'linear-gradient(145deg, rgba(30,41,59,0.7) 0%, rgba(15,23,42,0.85) 100%)',
            border: '1px solid rgba(99,102,241,0.3)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '24px',
            boxShadow: '0 10px 25px -5px rgba(0,0,0,0.3)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
              <span style={{ fontSize: '20px' }}>🎯</span>
              <div>
                <h2 style={{ color: '#f1f5f9', fontSize: '17px', fontWeight: 800, margin: 0 }}>
                  Tabela Recomendada de Calibração (LONG)
                </h2>
                <p style={{ color: '#94a3b8', fontSize: '12px', margin: '4px 0 0 0', lineHeight: '1.4' }}>
                  Compare estes números com o painel de <strong>Configurações</strong>.
                  <br />
                  <span style={{ color: '#38bdf8' }}>💡 <strong>Por que Bear / Neutral?</strong></span> As simulações do Shadow detectaram que operar LONG em mercados de alta esticada (Bull) degrada a rentabilidade média porque o robô compra rompimentos tardios perto de topos locais. Operar em Bear/Lateral entra em fundos acumulativos sólidos com taxa de acerto expressiva.
                </p>
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8', textAlign: 'left' }}>
                    <th style={{ padding: '10px' }}>Tier</th>
                    <th style={{ padding: '10px' }}>Score Mínimo</th>
                    <th style={{ padding: '10px' }}>RSI Máximo (LONG)</th>
                    <th style={{ padding: '10px' }}>Regimes Permitidos</th>
                    <th style={{ padding: '10px' }}>Win-Rate Histórico</th>
                    <th style={{ padding: '10px' }}>PnL Médio</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#fde047' }}>🥇 Major</td>
                    <td style={{ padding: '12px 10px', color: '#f1f5f9' }}>0.50 ou 0.51</td>
                    <td style={{ padding: '12px 10px', color: '#f1f5f9' }}>&lt;= 30</td>
                    <td style={{ padding: '12px 10px', color: '#86efac' }}>Bear / Neutral</td>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#10b981' }}>72.7%</td>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#10b981' }}>+1.07%</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#a5b4fc' }}>🥈 Strong Alt</td>
                    <td style={{ padding: '12px 10px', color: '#f1f5f9' }}>0.60</td>
                    <td style={{ padding: '12px 10px', color: '#f1f5f9' }}>&lt;= 32</td>
                    <td style={{ padding: '12px 10px', color: '#86efac' }}>Bear / Neutral</td>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#10b981' }}>85.0%</td>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#10b981' }}>+1.05%</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#fca5a5' }}>🥉 High Volatility</td>
                    <td style={{ padding: '12px 10px', color: '#f1f5f9' }}>0.55</td>
                    <td style={{ padding: '12px 10px', color: '#f1f5f9' }}>&lt;= 25</td>
                    <td style={{ padding: '12px 10px', color: '#86efac' }}>Bear / Neutral</td>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#10b981' }}>59.8%</td>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#10b981' }}>+0.93%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Performance por Tier */}
          <div style={sectionStyle}>
            <h2 style={{ color: '#e2e8f0', fontSize: '17px', fontWeight: 700, marginTop: 0, marginBottom: '20px' }}>
              📊 Performance por Tier de Moeda
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
              {rankingTier.length === 0
                ? <div style={{ color: '#64748b', fontSize: '13px' }}>Sem dados de tier ainda.</div>
                : rankingTier.map(t => {
                  const colors = TIER_COLORS[t.tier] || TIER_COLORS['Desconhecido'];
                  return (
                    <div key={t.tier} style={{
                      background: colors.bg,
                      border: `1px solid ${colors.border}`,
                      borderRadius: '12px',
                      padding: '20px',
                    }}>
                      <div style={{
                        display: 'inline-block',
                        background: colors.badge,
                        color: '#fff',
                        fontSize: '10px',
                        fontWeight: 700,
                        padding: '2px 10px',
                        borderRadius: '20px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        marginBottom: '12px',
                      }}>
                        {t.tier}
                      </div>
                      <div style={{ color: pnlColor(t.avg_pnl), fontSize: '26px', fontWeight: 800, marginBottom: '4px' }}>
                        {pnlSign(t.avg_pnl)}
                      </div>
                      <div style={{ color: '#94a3b8', fontSize: '12px', marginBottom: '2px' }}>PnL médio / simulação</div>
                      <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                        <span style={{ color: '#64748b', fontSize: '12px' }}>{t.count} sims</span>
                        <span style={{ color: '#64748b', fontSize: '12px' }}>WR: {t.win_rate}%</span>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* Tendencia de Mercado (BTC) */}
          <div style={sectionStyle}>
            <h2 style={{ color: '#e2e8f0', fontSize: '17px', fontWeight: 700, marginTop: 0, marginBottom: '20px' }}>
              📈 Tendência do BTC vs Resultado (Todos os Regimes)
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
              {['bull', 'bear', 'neutral'].map(tr => {
                const found = (tierData?.ranking_trend || []).find(x => x.trend === tr);
                const avg_pnl = found ? found.avg_pnl : 0.0;
                const win_rate = found ? found.win_rate : 0.0;
                const count = found ? found.count : 0;
                
                return (
                  <div key={tr} style={{
                    background: tr === 'bull' ? 'rgba(16,185,129,0.08)' : tr === 'bear' ? 'rgba(239,68,68,0.08)' : 'rgba(100,116,139,0.08)',
                    border: `1px solid ${tr === 'bull' ? 'rgba(16,185,129,0.3)' : tr === 'bear' ? 'rgba(239,68,68,0.3)' : 'rgba(100,116,139,0.3)'}`,
                    borderRadius: '12px', padding: '20px', textAlign: 'center',
                  }}>
                    <div style={{ fontSize: '24px', marginBottom: '8px' }}>
                      {tr === 'bull' ? '🐂' : tr === 'bear' ? '🐻' : '➖'}
                    </div>
                    <div style={{ color: '#e2e8f0', fontWeight: 700, fontSize: '16px', textTransform: 'uppercase', marginBottom: '8px' }}>
                      {tr === 'bull' ? 'Bull' : tr === 'bear' ? 'Bear' : 'Neutral'}
                    </div>
                    <div style={{ color: count > 0 ? pnlColor(avg_pnl) : '#475569', fontSize: '24px', fontWeight: 800 }}>
                      {count > 0 ? pnlSign(avg_pnl) : '–'}
                    </div>
                    <div style={{ color: '#64748b', fontSize: '12px', marginTop: '4px' }}>
                      {count > 0 ? `${count} sims | WR ${win_rate}%` : 'Sem dados'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* RSI e Hora em duas colunas */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '24px' }}>

            {/* Análise por RSI */}
            <div style={sectionStyle}>
              <h2 style={{ color: '#e2e8f0', fontSize: '17px', fontWeight: 700, marginTop: 0, marginBottom: '20px' }}>
                📡 RSI de Entrada vs. Resultado
              </h2>
              {rankingRsi.length === 0
                ? <div style={{ color: '#64748b', fontSize: '13px' }}>Sem dados de RSI ainda.</div>
                : rankingRsi.map(r => (
                  <RSIBar key={r.range} range={r.range} avg_pnl={r.avg_pnl} win_rate={r.win_rate} count={r.count} />
                ))
              }
              <p style={{ color: '#475569', fontSize: '11px', marginTop: '12px', marginBottom: 0 }}>
                * PnL médio por simulação naquela faixa de RSI de entrada.
              </p>
            </div>

            {/* Janelas Horárias */}
            <div style={sectionStyle}>
              <h2 style={{ color: '#e2e8f0', fontSize: '17px', fontWeight: 700, marginTop: 0, marginBottom: '20px' }}>
                🕐 Janelas Horárias (UTC)
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {rankingHourWindows.length === 0
                  ? <div style={{ color: '#64748b', fontSize: '13px' }}>Sem dados horários ainda.</div>
                  : rankingHourWindows.map(w => {
                    const isPos = w.avg_pnl >= 0;
                    const icon = HOUR_WINDOW_ICONS[w.window] || '⏰';
                    return (
                      <div key={w.window} style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        padding: '14px 16px',
                        borderRadius: '10px',
                        background: isPos ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)',
                        border: `1px solid ${isPos ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.18)'}`,
                      }}>
                        <span style={{ fontSize: '20px' }}>{icon}</span>
                        <div style={{ flex: 1 }}>
                          <div style={{ color: '#e2e8f0', fontWeight: 600, fontSize: '14px' }}>{w.window}</div>
                          <div style={{ color: '#64748b', fontSize: '12px' }}>{w.count} simulações • WR {w.win_rate}%</div>
                        </div>
                        <div style={{ color: pnlColor(w.avg_pnl), fontWeight: 700, fontSize: '16px' }}>
                          {pnlSign(w.avg_pnl)}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>

          {/* Heatmap por hora */}
          <div style={sectionStyle}>
            <h2 style={{ color: '#e2e8f0', fontSize: '17px', fontWeight: 700, marginTop: 0, marginBottom: '16px' }}>
              🗓️ Mapa de Calor — Hora de Entrada (UTC) vs. PnL Médio
            </h2>
            <p style={{ color: '#475569', fontSize: '12px', marginBottom: '16px', marginTop: 0 }}>
              Verde = lucrativo em média · Vermelho = prejuízo em média · Cinza = sem dados
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {heatmapRows.map(row => (
                <div key={row.label} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ color: '#64748b', fontSize: '12px', minWidth: '90px' }}>{row.label}</span>
                  <div style={{ display: 'flex', gap: '4px', flex: 1 }}>
                    {row.hours.map(h => (
                      <HeatmapCell key={h.hour} hour={h.hour} avg_pnl={h.avg_pnl} count={h.count} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Ranking SL/TP */}
          <div style={sectionStyle}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h2 style={{ color: '#e2e8f0', fontSize: '17px', fontWeight: 700, margin: 0 }}>
                🎯 Ranking de Configurações SL/TP
              </h2>
              <span style={{ color: '#64748b', fontSize: '12px' }}>PnL médio por simulação</span>
            </div>
            {rankingSltp.length === 0
              ? <div style={{ color: '#64748b', textAlign: 'center', padding: '24px' }}>Sem dados disponíveis.</div>
              : rankingSltp.map((strat, i) => (
                <SLTPRow
                  key={strat.config}
                  rank={i}
                  config={strat.config}
                  avg_pnl={strat.avg_pnl}
                  win_rate={strat.win_rate}
                  count={strat.count}
                />
              ))
            }
          </div>

          {/* Best Scores Table */}
          {bestScores.length > 0 && (
            <div style={sectionStyle}>
              <h2 style={{ color: '#e2e8f0', fontSize: '17px', fontWeight: 700, marginTop: 0, marginBottom: '20px' }}>
                🚀 Top 10 Melhores Scores Avaliados
              </h2>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(71,85,105,0.4)', color: '#64748b', fontSize: '12px', fontWeight: 600 }}>
                      <th style={{ padding: '12px 8px' }}>Ativo</th>
                      <th style={{ padding: '12px 8px' }}>Score do Modelo</th>
                      <th style={{ padding: '12px 8px' }}>RSI</th>
                      <th style={{ padding: '12px 8px' }}>Horário (UTC)</th>
                      <th style={{ padding: '12px 8px' }}>Config SL/TP</th>
                      <th style={{ padding: '12px 8px' }}>Resultado Simulado</th>
                      <th style={{ padding: '12px 8px' }}>Tempo / Motivo Saída</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bestScores.map((s, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(71,85,105,0.2)', fontSize: '13.5px', color: '#e2e8f0' }}>
                        <td style={{ padding: '12px 8px', fontWeight: 700 }}>{s.symbol}</td>
                        <td style={{ padding: '12px 8px', color: '#818cf8', fontWeight: 600 }}>{(s.score).toFixed(4)}</td>
                        <td style={{ padding: '12px 8px' }}>{s.rsi ? s.rsi.toFixed(1) : 'N/A'}</td>
                        <td style={{ padding: '12px 8px' }}>{s.hour !== null ? `${s.hour.toString().padStart(2, '0')}:00` : 'N/A'}</td>
                        <td style={{ padding: '12px 8px', color: '#94a3b8' }}>SL={s.sl || 'Nulo'} | TP={s.tp || 'Nulo'}</td>
                        <td style={{ padding: '12px 8px', color: s.pnl >= 0 ? '#10b981' : '#ef4444', fontWeight: 700 }}>
                          {pnlSign(s.pnl)}
                        </td>
                        <td style={{ padding: '12px 8px', fontSize: '12px', color: '#64748b' }}>{s.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </>
      )}
    </div>
  );
}
