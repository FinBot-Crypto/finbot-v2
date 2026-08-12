import React, { useState, useEffect } from 'react';

const TIER_LABELS = {
  'Major': 'Major (BTC, ETH)',
  'Strong Alt': 'Strong Alt (SOL, BNB, etc.)',
  'High Volatility': 'High Volatility (PEPE, TRX, etc.)'
};

const TIER_COLORS = {
  'Major': { border: 'rgba(234,179,8,0.3)', glow: 'rgba(234,179,8,0.1)' },
  'Strong Alt': { border: 'rgba(99,102,241,0.3)', glow: 'rgba(99,102,241,0.1)' },
  'High Volatility': { border: 'rgba(239,68,68,0.3)', glow: 'rgba(239,68,68,0.1)' }
};

// Configurações ótimas detectadas pelas simulações dos Shadows
const SHADOW_OPTIMAL = {
  'long_Major_min_score': 0.50,
  'long_Major_max_rsi': 30,
  'long_Major_allowed_regimes': ['bear', 'neutral'],
  'long_Strong Alt_min_score': 0.60,
  'long_Strong Alt_max_rsi': 32,
  'long_Strong Alt_allowed_regimes': ['bear', 'neutral'],
  'long_High Volatility_min_score': 0.55,
  'long_High Volatility_max_rsi': 25,
  'long_High Volatility_allowed_regimes': ['bear', 'neutral'],

  'short_Major_min_score': 0.54,
  'short_Major_min_rsi': 65,
  'short_Major_allowed_regimes': ['bull', 'neutral'],
  'short_Strong Alt_min_score': 0.50,
  'short_Strong Alt_min_rsi': 65,
  'short_Strong Alt_allowed_regimes': ['bull', 'neutral'],
  'short_High Volatility_min_score': 0.54,
  'short_High Volatility_min_rsi': 70,
  'short_High Volatility_allowed_regimes': ['bull', 'neutral']
};

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [lemeHistory, setLemeHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [activeTooltip, setActiveTooltip] = useState(null); // formato: 'long_Major_min_score' ou null

  const fetchLemeHistory = () => {
    fetch('/api/leme/history')
      .then(res => res.json())
      .then(data => setLemeHistory(data))
      .catch(err => console.error("Erro ao buscar histórico do Leme:", err));
  };

  useEffect(() => {
    fetch('/api/settings')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        setSettings(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });

    fetchLemeHistory();
  }, []);

  const handleChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // Para inputs numéricos: guarda string bruta durante edição, converte só no save
  const handleNumericChange = (key, rawValue) => {
    setSettings(prev => ({
      ...prev,
      [key]: rawValue
    }));
  };

  const toggleTooltip = (fieldKey) => {
    setActiveTooltip(prev => prev === fieldKey ? null : fieldKey);
  };

  const handleSave = () => {
    // Converte valores de string para número antes de validar e enviar
    const cleanedSettings = {};
    for (let k in settings) {
      let v = settings[k];
      // Converte strings numéricas para números
      if (typeof v === 'string' && v !== '' && !isNaN(Number(v))) {
        v = Number(v);
      }
      cleanedSettings[k] = v;
    }

    // Validação de limites
    for (let k in cleanedSettings) {
      if (k.endsWith('_min_score')) {
        const val = parseFloat(cleanedSettings[k]);
        if (isNaN(val) || val <= 0 || val >= 1.0) {
          setFeedback({ type: 'error', text: `O score mínimo para ${k.replace('long_', '').replace('short_', '').replace('_min_score', '')} deve ser um decimal entre 0.0 e 1.0 (ex: 0.70)` });
          return;
        }
      }
      if (k.endsWith('_sl') || k.endsWith('_tp')) {
        const val = parseFloat(cleanedSettings[k]);
        if (isNaN(val) || val <= 0 || val > 100) {
          setFeedback({ type: 'error', text: `Stop Loss / Take Profit para ${k} deve ser um valor numérico entre 0.1% e 100%` });
          return;
        }
      }
      if (k.endsWith('_max_rsi') || k.endsWith('_min_rsi')) {
        const val = parseFloat(cleanedSettings[k]);
        if (isNaN(val) || val <= 0 || val > 100) {
          setFeedback({ type: 'error', text: `O limite de RSI para ${k} deve ser um valor numérico entre 1 e 100` });
          return;
        }
      }
      if (k.endsWith('_lev_2x_pct') || k.endsWith('_lev_3x_pct') || k.endsWith('_lev_5x_pct')) {
        const val = parseFloat(cleanedSettings[k]);
        if (isNaN(val) || val < 0.0 || val > 1.0) {
          setFeedback({ type: 'error', text: `O percentual de alavancagem progressiva para ${k} deve ser entre 0.00 e 1.00 (ex: 0.20)` });
          return;
        }
      }
      if (k === 'leme_max_consecutive_sl') {
        const val = parseInt(cleanedSettings[k]);
        if (isNaN(val) || val <= 0 || val > 20) {
          setFeedback({ type: 'error', text: 'O limite de Stop Losses seguidos do Leme deve ser entre 1 e 20.' });
          return;
        }
      }
      if (k === 'leme_min_win_rate' || k === 'leme_shadow_min_winrate') {
        const val = parseFloat(cleanedSettings[k]);
        if (isNaN(val) || val < 0 || val > 100) {
          setFeedback({ type: 'error', text: 'As taxas de win-rate do Leme devem ser entre 0% e 100%.' });
          return;
        }
      }
      if (k === 'leme_cooldown_hours') {
        const val = parseInt(cleanedSettings[k]);
        if (isNaN(val) || val <= 0 || val > 720) {
          setFeedback({ type: 'error', text: 'O prazo de cooldown do Leme deve ser entre 1 e 720 horas.' });
          return;
        }
      }
      if (k === 'leme_shadow_min_trades') {
        const val = parseInt(cleanedSettings[k]);
        if (isNaN(val) || val <= 0 || val > 50) {
          setFeedback({ type: 'error', text: 'A quantidade mínima de trades shadow do Leme deve ser entre 1 e 50.' });
          return;
        }
      }
    }

    setSaving(true);
    setFeedback(null);
    fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cleanedSettings)
    })
      .then(res => {
        if (!res.ok) throw new Error('Falha ao salvar');
        return res.json();
      })
      .then(() => {
        setFeedback({ type: 'success', text: 'Configurações salvas e aplicadas em tempo real com sucesso!' });
        setSaving(false);
        fetchLemeHistory();
        setTimeout(() => setFeedback(null), 5000);
      })
      .catch(err => {
        setFeedback({ type: 'error', text: `Erro ao salvar: ${err.message}` });
        setSaving(false);
      });
  };

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ color: '#6366f1', fontSize: '32px', marginBottom: '12px' }}>⚙️</div>
        <div style={{ color: '#94a3b8', fontSize: '16px' }}>Carregando configurações do sistema...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ color: '#ef4444' }}>Erro ao carregar configurações: {error}</div>
      </div>
    );
  }

  const sectionStyle = {
    background: 'rgba(15,23,42,0.6)',
    border: '1px solid rgba(71,85,105,0.3)',
    borderRadius: '16px',
    padding: '24px',
    marginBottom: '24px',
    backdropFilter: 'blur(8px)',
  };

  const inputStyle = {
    background: '#0f172a',
    color: '#f1f5f9',
    border: '1px solid rgba(71,85,105,0.6)',
    borderRadius: '8px',
    padding: '8px 12px',
    width: '100%',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box'
  };

  const labelStyle = {
    color: '#94a3b8',
    fontSize: '12px',
    fontWeight: 500,
    marginBottom: '6px',
    display: 'block'
  };

  // Renderizador Inteligente de Input com Detector de Discrepância Shadow e Tooltip Explicativo + Ação Rápida
  const SmartField = ({ fieldKey, label, type = 'number', step = '0.01', min = '0.0', max = '100.0' }) => {
    const rawValue = settings[fieldKey] ?? '';
    const numericValue = parseFloat(rawValue);
    const currentValue = isNaN(numericValue) ? 0 : numericValue;
    const optimalValue = SHADOW_OPTIMAL[fieldKey];
    
    // Identifica se há discrepância (se difere do ótimo recomendado pelos simuladores)
    const isDiscrepant = optimalValue !== undefined && !isNaN(numericValue) && Math.abs(currentValue - optimalValue) > 0.001;

    // Explicações customizadas para as discrepâncias
    let rationale = '';
    if (isDiscrepant) {
      if (fieldKey.endsWith('_min_score')) {
        rationale = `Seu score atual (${currentValue}) está desalinhado do ótimo (${optimalValue}). O backtest shadow mostra que este limite aumenta a taxa de acerto média para ~72% (Major) ou ~85% (Strong Alt) preservando o volume de ordens diárias.`;
      } else if (fieldKey.endsWith('_max_rsi') || fieldKey.endsWith('_min_rsi')) {
        rationale = `Seu RSI atual (${currentValue}) está diferente do sugerido (${optimalValue}). Valores fora do ponto ótimo do simulador geram entradas prematuras ou squeezes de perda.`;
      }
    }

    return (
      <div style={{ position: 'relative', marginBottom: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label style={labelStyle}>{label}</label>
          {isDiscrepant && (
            <span 
              onClick={() => toggleTooltip(fieldKey)}
              style={{
                background: 'rgba(234,179,8,0.15)',
                color: '#fde047',
                border: '1px solid rgba(234,179,8,0.4)',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: 700,
                padding: '1px 6px',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              ⚠️ Destoante
            </span>
          )}
        </div>
        
        <input 
          type={type}
          step={step}
          min={min}
          max={max}
          value={rawValue}
          onChange={(e) => handleNumericChange(fieldKey, e.target.value)}
          style={{
            ...inputStyle,
            border: isDiscrepant ? '1px solid rgba(234, 179, 8, 0.6)' : '1px solid rgba(71,85,105,0.6)',
            boxShadow: isDiscrepant ? '0 0 8px rgba(234, 179, 8, 0.15)' : 'none'
          }}
        />

        {/* Floating Premium Tooltip Overlay */}
        {activeTooltip === fieldKey && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
            border: '1px solid rgba(234,179,8,0.5)',
            borderRadius: '8px',
            padding: '12px 14px',
            zIndex: 100,
            marginTop: '6px',
            boxShadow: '0 8px 20px rgba(0,0,0,0.4)',
            color: '#e2e8f0',
            fontSize: '11px',
            lineHeight: '1.4'
          }}>
            <p style={{ margin: '0 0 8px 0', color: '#fde047', fontWeight: 700 }}>🔬 Recomendação do Shadow Simulator</p>
            <p style={{ margin: '0 0 10px 0', color: '#cbd5e1' }}>{rationale}</p>
            <button
              type="button"
              onClick={() => {
                handleChange(fieldKey, optimalValue);
                setActiveTooltip(null);
              }}
              style={{
                background: 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)',
                color: '#0f172a',
                border: 'none',
                borderRadius: '4px',
                padding: '4px 10px',
                fontWeight: 700,
                fontSize: '10px',
                cursor: 'pointer',
                boxShadow: '0 2px 6px rgba(234, 179, 8, 0.3)'
              }}
            >
              🪄 Aplicar {optimalValue}
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <span style={{ fontSize: '28px' }}>⚙️</span>
            <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#f1f5f9', margin: 0 }}>
              Painel de Configurações
            </h1>
          </div>
          <p style={{ color: '#64748b', fontSize: '14px', margin: 0 }}>
            Gerencie em tempo real os limites operacionais de LONG e SHORT para os 6 grupos de Tiers.
          </p>
        </div>
        
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
            color: '#fff',
            border: 'none',
            borderRadius: '10px',
            padding: '12px 24px',
            fontWeight: 700,
            fontSize: '14px',
            cursor: 'pointer',
            boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)',
            transition: 'all 0.2s',
            opacity: saving ? 0.7 : 1
          }}
        >
          {saving ? 'Gravando...' : 'Salvar Alterações'}
        </button>
      </div>

      {feedback && (
        <div style={{
          background: feedback.type === 'success' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
          border: `1px solid ${feedback.type === 'success' ? '#10b981' : '#ef4444'}`,
          borderRadius: '12px',
          padding: '14px 20px',
          color: feedback.type === 'success' ? '#6ee7b7' : '#fca5a5',
          fontSize: '14px',
          fontWeight: 600,
          marginBottom: '24px'
        }}>
          {feedback.type === 'success' ? '✅' : '❌'} {feedback.text}
        </div>
      )}

      {/* O Leme Config Card */}
      <div style={{
        ...sectionStyle,
        border: '1px solid rgba(99, 102, 241, 0.3)',
        boxShadow: '0 4px 20px rgba(99, 102, 241, 0.1)',
        marginBottom: '32px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '14px', marginBottom: '20px' }}>
          <div>
            <h2 style={{ color: '#e2e8f0', fontSize: '18px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              ☸️ O Leme (Piloto Autônomo)
            </h2>
            <p style={{ color: '#64748b', fontSize: '12px', margin: '4px 0 0 0' }}>
              Gerenciamento dinâmico de risco. Ajusta e pausa automaticamente a operação dos Tiers com base em perdas reais e shadow.
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label style={{ color: '#f1f5f9', fontSize: '14px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <input 
                type="checkbox" 
                checked={settings.leme_active ?? true}
                onChange={(e) => handleChange('leme_active', e.target.checked)}
                style={{ cursor: 'pointer', transform: 'scale(1.2)' }}
              />
              Piloto Ativo
            </label>
          </div>
        </div>

        {/* Leme Parameters Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          <div>
            <label style={labelStyle}>Stop Losses Consecutivos (Max)</label>
            <input 
              type="number" 
              step="1"
              min="1"
              max="20"
              value={settings.leme_max_consecutive_sl ?? 3}
              onChange={(e) => handleNumericChange('leme_max_consecutive_sl', e.target.value)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Win-Rate Mínimo Real (%)</label>
            <input 
              type="number" 
              step="1"
              min="10"
              max="100"
              value={settings.leme_min_win_rate ?? 50.0}
              onChange={(e) => handleNumericChange('leme_min_win_rate', e.target.value)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Prazo de Cooldown (Horas)</label>
            <input 
              type="number" 
              step="1"
              min="1"
              max="720"
              value={settings.leme_cooldown_hours ?? 24}
              onChange={(e) => handleNumericChange('leme_cooldown_hours', e.target.value)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Mínimo de Trades Shadow</label>
            <input 
              type="number" 
              step="1"
              min="1"
              max="50"
              value={settings.leme_shadow_min_trades ?? 5}
              onChange={(e) => handleNumericChange('leme_shadow_min_trades', e.target.value)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Win-Rate Recuperação Shadow (%)</label>
            <input 
              type="number" 
              step="1"
              min="10"
              max="100"
              value={settings.leme_shadow_min_winrate ?? 60.0}
              onChange={(e) => handleNumericChange('leme_shadow_min_winrate', e.target.value)}
              style={inputStyle}
            />
          </div>
        </div>

        {/* Leme History Decisions Log Table */}
        <div style={{ marginTop: '28px' }}>
          <h3 style={{ color: '#e2e8f0', fontSize: '14px', fontWeight: 700, marginBottom: '12px' }}>
            📜 Histórico de Decisões do Piloto
          </h3>
          {lemeHistory.length === 0 ? (
            <div style={{ padding: '16px', background: '#0f172a', border: '1px solid rgba(71,85,105,0.2)', borderRadius: '8px', color: '#64748b', fontSize: '13px', textAlign: 'center' }}>
              Nenhuma decisão automática registrada ainda pelo piloto do Leme.
            </div>
          ) : (
            <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid rgba(71,85,105,0.3)', background: '#0f172a' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: 'rgba(30,41,59,0.8)', borderBottom: '1px solid rgba(71,85,105,0.4)' }}>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600 }}>Data/Hora</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600 }}>Grupo</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600 }}>Ação</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600 }}>Motivo</th>
                  </tr>
                </thead>
                <tbody>
                  {lemeHistory.map((h, i) => {
                    let actionBadgeStyle = {
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 700,
                      display: 'inline-block'
                    };
                    if (h.action === 'DISABLE') {
                      actionBadgeStyle = { ...actionBadgeStyle, background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.3)' };
                    } else if (h.action === 'ENABLE') {
                      actionBadgeStyle = { ...actionBadgeStyle, background: 'rgba(34, 197, 94, 0.15)', color: '#86efac', border: '1px solid rgba(34, 197, 94, 0.3)' };
                    } else {
                      actionBadgeStyle = { ...actionBadgeStyle, background: 'rgba(100, 116, 139, 0.15)', color: '#cbd5e1', border: '1px solid rgba(100, 116, 139, 0.3)' };
                    }

                    return (
                      <tr key={h.id || i} style={{ borderBottom: i === lemeHistory.length - 1 ? 'none' : '1px solid rgba(71,85,105,0.2)' }}>
                        <td style={{ padding: '10px 14px', color: '#94a3b8', whiteSpace: 'nowrap' }}>
                          {h.created_at ? new Date(h.created_at).toLocaleString('pt-BR') : '-'}
                        </td>
                        <td style={{ padding: '10px 14px', color: '#f1f5f9', fontWeight: 600 }}>
                          {h.group_name}
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={actionBadgeStyle}>{h.action}</span>
                        </td>
                        <td style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                          {h.reason}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Tiers Loop */}
      {['Major', 'Strong Alt', 'High Volatility'].map(tier => {
        const colors = TIER_COLORS[tier];
        
        // Verifica se regimes permitidos de Long ou Short divergem do ideal
        const longRegimesOptimal = SHADOW_OPTIMAL[`long_${tier}_allowed_regimes`].slice().sort().join(',');
        const longRegimesCurrent = (settings[`long_${tier}_allowed_regimes`] ?? []).slice().sort().join(',');
        const isLongRegimeDivergent = longRegimesOptimal !== longRegimesCurrent;

        const shortRegimesOptimal = SHADOW_OPTIMAL[`short_${tier}_allowed_regimes`].slice().sort().join(',');
        const shortRegimesCurrent = (settings[`short_${tier}_allowed_regimes`] ?? []).slice().sort().join(',');
        const isShortRegimeDivergent = shortRegimesOptimal !== shortRegimesCurrent;

        return (
          <div key={tier} style={{
            ...sectionStyle,
            border: `1px solid ${colors.border}`,
            boxShadow: `0 4px 20px ${colors.glow}`
          }}>
            <h2 style={{ color: '#e2e8f0', fontSize: '18px', fontWeight: 800, marginTop: 0, marginBottom: '20px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '10px' }}>
              💎 {TIER_LABELS[tier]}
            </h2>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px' }}>
              
              {/* LONG CONFIG */}
              <div style={{ background: 'rgba(99,102,241,0.03)', border: '1px solid rgba(99,102,241,0.1)', borderRadius: '12px', padding: '18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ color: '#818cf8', fontSize: '15px', fontWeight: 700, margin: 0 }}>🟢 Operações LONG</h3>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input 
                      type="checkbox"
                      checked={settings[`long_${tier}_allowed`] ?? true}
                      onChange={(e) => handleChange(`long_${tier}_allowed`, e.target.checked)}
                      style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                    <span style={{ color: '#f1f5f9', fontSize: '13px', fontWeight: 600 }}>Ativo</span>
                  </label>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <SmartField 
                    fieldKey={`long_${tier}_min_score`}
                    label="Score Mínimo"
                  />
                  <SmartField 
                    fieldKey={`long_${tier}_max_rsi`}
                    label="RSI Máximo (LONG)"
                    step="1"
                    min="10"
                    max="60"
                  />
                  <div>
                    <label style={labelStyle}>Stop Loss (SL %)</label>
                    <input 
                      type="number" 
                      step="0.1"
                      min="0.5"
                      max="20"
                      value={settings[`long_${tier}_sl`] ?? 3.0}
                      onChange={(e) => handleNumericChange(`long_${tier}_sl`, e.target.value)}
                      style={inputStyle}
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>Take Profit (TP %)</label>
                    <input 
                      type="number" 
                      step="0.1"
                      min="0.5"
                      max="50"
                      value={settings[`long_${tier}_tp`] ?? 3.0}
                      onChange={(e) => handleNumericChange(`long_${tier}_tp`, e.target.value)}
                      style={inputStyle}
                    />
                  </div>
                </div>

                {/* Progressive Alavancagem Indication and Controls */}
                <div style={{ marginTop: '14px', background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <label style={{ ...labelStyle, marginBottom: '8px', color: '#818cf8', fontWeight: 700 }}>⚡ Escalonamento de Alavancagem Progressiva</label>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '12px' }}>
                    <div>
                      <label style={{ ...labelStyle, fontSize: '10px' }}>Threshold 2x (%)</label>
                      <input 
                        type="number"
                        step="0.05"
                        min="0.0"
                        max="1.0"
                        value={settings[`long_${tier}_lev_2x_pct`] ?? 0.20}
                        onChange={(e) => handleNumericChange(`long_${tier}_lev_2x_pct`, e.target.value)}
                        style={{ ...inputStyle, padding: '4px 6px', fontSize: '12px' }}
                      />
                    </div>
                    <div>
                      <label style={{ ...labelStyle, fontSize: '10px' }}>Threshold 3x (%)</label>
                      <input 
                        type="number"
                        step="0.05"
                        min="0.0"
                        max="1.0"
                        value={settings[`long_${tier}_lev_3x_pct`] ?? 0.50}
                        onChange={(e) => handleNumericChange(`long_${tier}_lev_3x_pct`, e.target.value)}
                        style={{ ...inputStyle, padding: '4px 6px', fontSize: '12px' }}
                      />
                    </div>
                    <div>
                      <label style={{ ...labelStyle, fontSize: '10px' }}>Threshold 5x (%)</label>
                      <input 
                        type="number"
                        step="0.05"
                        min="0.0"
                        max="1.0"
                        value={settings[`long_${tier}_lev_5x_pct`] ?? 0.80}
                        onChange={(e) => handleNumericChange(`long_${tier}_lev_5x_pct`, e.target.value)}
                        style={{ ...inputStyle, padding: '4px 6px', fontSize: '12px' }}
                      />
                    </div>
                  </div>

                  <p style={{ color: '#cbd5e1', fontSize: '11px', margin: '4px 0 0 0', lineHeight: '1.4' }}>
                    • Score &lt; {((parseFloat(settings[`long_${tier}_min_score`]) || 0.60) + (1.0 - (parseFloat(settings[`long_${tier}_min_score`]) || 0.60)) * (parseFloat(settings[`long_${tier}_lev_2x_pct`]) || 0.20)).toFixed(2)}: <strong>1x (Spot)</strong>
                    <br />
                    • Score &gt;= {((parseFloat(settings[`long_${tier}_min_score`]) || 0.60) + (1.0 - (parseFloat(settings[`long_${tier}_min_score`]) || 0.60)) * (parseFloat(settings[`long_${tier}_lev_2x_pct`]) || 0.20)).toFixed(2)}: <strong>2x isolated</strong>
                    <br />
                    • Score &gt;= {((parseFloat(settings[`long_${tier}_min_score`]) || 0.60) + (1.0 - (parseFloat(settings[`long_${tier}_min_score`]) || 0.60)) * (parseFloat(settings[`long_${tier}_lev_3x_pct`]) || 0.50)).toFixed(2)}: <strong>3x isolated</strong>
                    <br />
                    • Score &gt;= {((parseFloat(settings[`long_${tier}_min_score`]) || 0.60) + (1.0 - (parseFloat(settings[`long_${tier}_min_score`]) || 0.60)) * (parseFloat(settings[`long_${tier}_lev_5x_pct`]) || 0.80)).toFixed(2)}: <strong>5x isolated</strong>
                  </p>
                </div>

                {/* Long Allowed Regimes Selection */}
                <div style={{ marginTop: '14px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '10px', position: 'relative' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={labelStyle}>Regimes Permitidos (Mercado)</label>
                    {isLongRegimeDivergent && (
                      <span
                        onClick={() => toggleTooltip(`long_${tier}_allowed_regimes`)}
                        style={{
                          background: 'rgba(234,179,8,0.15)',
                          color: '#fde047',
                          border: '1px solid rgba(234,179,8,0.4)',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '1px 6px',
                          cursor: 'pointer'
                        }}
                      >
                        ⚠️ Destoante
                      </span>
                    )}
                  </div>

                  {activeTooltip === `long_${tier}_allowed_regimes` && (
                    <div style={{
                      position: 'absolute',
                      bottom: '100%',
                      left: 0,
                      right: 0,
                      background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                      border: '1px solid rgba(234,179,8,0.5)',
                      borderRadius: '8px',
                      padding: '12px 14px',
                      zIndex: 100,
                      marginBottom: '6px',
                      boxShadow: '0 8px 20px rgba(0,0,0,0.4)',
                      color: '#cbd5e1',
                      fontSize: '11px',
                      lineHeight: '1.4'
                    }}>
                      <p style={{ margin: '0 0 6px 0', color: '#fde047', fontWeight: 700 }}>🔬 Recomendação de Regimes LONG</p>
                      <p style={{ margin: '0 0 10px 0' }}>O simulador shadow detectou que operar LONG durante mercado em Bull desgasta a rentabilidade por entrar em topos esticados. O ideal é operar apenas em Bear / Neutral.</p>
                      <button
                        type="button"
                        onClick={() => {
                          handleChange(`long_${tier}_allowed_regimes`, SHADOW_OPTIMAL[`long_${tier}_allowed_regimes`]);
                          setActiveTooltip(null);
                        }}
                        style={{
                          background: 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)',
                          color: '#0f172a',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '4px 10px',
                          fontWeight: 700,
                          fontSize: '10px',
                          cursor: 'pointer'
                        }}
                      >
                        🪄 Alinhar para Bear/Neutral
                      </button>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                    {['bull', 'bear', 'neutral'].map(reg => {
                      const currentRegimes = settings[`long_${tier}_allowed_regimes`] ?? ['bull', 'neutral'];
                      const active = currentRegimes.includes(reg);
                      return (
                        <button
                          key={reg}
                          type="button"
                          onClick={() => {
                            const next = active 
                              ? currentRegimes.filter(r => r !== reg)
                              : [...currentRegimes, reg];
                            handleChange(`long_${tier}_allowed_regimes`, next);
                          }}
                          style={{
                            flex: 1,
                            background: active ? 'rgba(99,102,241,0.2)' : 'transparent',
                            color: active ? '#a5b4fc' : '#64748b',
                            border: `1px solid ${active ? 'rgba(99,102,241,0.5)' : 'rgba(71,85,105,0.3)'}`,
                            borderRadius: '6px',
                            padding: '6px 4px',
                            fontSize: '11px',
                            fontWeight: 700,
                            cursor: 'pointer',
                            transition: 'all 0.15s',
                            textTransform: 'uppercase'
                          }}
                        >
                          {reg === 'bull' ? '🐂 Bull' : reg === 'bear' ? '🐻 Bear' : '➖ Lateral'}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* SHORT CONFIG */}
              <div style={{ background: 'rgba(239,68,68,0.03)', border: '1px solid rgba(239,68,68,0.1)', borderRadius: '12px', padding: '18px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ color: '#f87171', fontSize: '15px', fontWeight: 700, margin: 0 }}>🔴 Operações SHORT</h3>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input 
                      type="checkbox"
                      checked={settings[`short_${tier}_allowed`] ?? true}
                      onChange={(e) => handleChange(`short_${tier}_allowed`, e.target.checked)}
                      style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                    />
                    <span style={{ color: '#f1f5f9', fontSize: '13px', fontWeight: 600 }}>Ativo</span>
                  </label>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <SmartField 
                    fieldKey={`short_${tier}_min_score`}
                    label="Score Mínimo"
                  />
                  <SmartField 
                    fieldKey={`short_${tier}_min_rsi`}
                    label="RSI Mínimo (SHORT)"
                    step="1"
                    min="50"
                    max="95"
                  />
                  <div>
                    <label style={labelStyle}>Stop Loss (SL %)</label>
                    <input 
                      type="number" 
                      step="0.1"
                      min="0.5"
                      max="20"
                      value={settings[`short_${tier}_sl`] ?? 3.0}
                      onChange={(e) => handleNumericChange(`short_${tier}_sl`, e.target.value)}
                      style={inputStyle}
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>Take Profit (TP %)</label>
                    <input 
                      type="number" 
                      step="0.1"
                      min="0.5"
                      max="50"
                      value={settings[`short_${tier}_tp`] ?? 3.0}
                      onChange={(e) => handleNumericChange(`short_${tier}_tp`, e.target.value)}
                      style={inputStyle}
                    />
                  </div>
                </div>

                {/* Progressive Alavancagem Indication and Controls for SHORT */}
                <div style={{ marginTop: '14px', background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <label style={{ ...labelStyle, marginBottom: '8px', color: '#f87171', fontWeight: 700 }}>⚡ Escalonamento de Alavancagem Progressiva</label>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '12px' }}>
                    <div>
                      <label style={{ ...labelStyle, fontSize: '10px' }}>Threshold 2x (%)</label>
                      <input 
                        type="number"
                        step="0.05"
                        min="0.0"
                        max="1.0"
                        value={settings[`short_${tier}_lev_2x_pct`] ?? 0.20}
                        onChange={(e) => handleNumericChange(`short_${tier}_lev_2x_pct`, e.target.value)}
                        style={{ ...inputStyle, padding: '4px 6px', fontSize: '12px' }}
                      />
                    </div>
                    <div>
                      <label style={{ ...labelStyle, fontSize: '10px' }}>Threshold 3x (%)</label>
                      <input 
                        type="number"
                        step="0.05"
                        min="0.0"
                        max="1.0"
                        value={settings[`short_${tier}_lev_3x_pct`] ?? 0.50}
                        onChange={(e) => handleNumericChange(`short_${tier}_lev_3x_pct`, e.target.value)}
                        style={{ ...inputStyle, padding: '4px 6px', fontSize: '12px' }}
                      />
                    </div>
                    <div>
                      <label style={{ ...labelStyle, fontSize: '10px' }}>Threshold 5x (%)</label>
                      <input 
                        type="number"
                        step="0.05"
                        min="0.0"
                        max="1.0"
                        value={settings[`short_${tier}_lev_5x_pct`] ?? 0.80}
                        onChange={(e) => handleNumericChange(`short_${tier}_lev_5x_pct`, e.target.value)}
                        style={{ ...inputStyle, padding: '4px 6px', fontSize: '12px' }}
                      />
                    </div>
                  </div>

                  <p style={{ color: '#cbd5e1', fontSize: '11px', margin: '4px 0 0 0', lineHeight: '1.4' }}>
                    • Score &lt; {((parseFloat(settings[`short_${tier}_min_score`]) || 0.50) + (1.0 - (parseFloat(settings[`short_${tier}_min_score`]) || 0.50)) * (parseFloat(settings[`short_${tier}_lev_2x_pct`]) || 0.20)).toFixed(2)}: <strong>1x (Margem Cheia)</strong>
                    <br />
                    • Score &gt;= {((parseFloat(settings[`short_${tier}_min_score`]) || 0.50) + (1.0 - (parseFloat(settings[`short_${tier}_min_score`]) || 0.50)) * (parseFloat(settings[`short_${tier}_lev_2x_pct`]) || 0.20)).toFixed(2)}: <strong>2x isolated</strong>
                    <br />
                    • Score &gt;= {((parseFloat(settings[`short_${tier}_min_score`]) || 0.50) + (1.0 - (parseFloat(settings[`short_${tier}_min_score`]) || 0.50)) * (parseFloat(settings[`short_${tier}_lev_3x_pct`]) || 0.50)).toFixed(2)}: <strong>3x isolated</strong>
                    <br />
                    • Score &gt;= {((parseFloat(settings[`short_${tier}_min_score`]) || 0.50) + (1.0 - (parseFloat(settings[`short_${tier}_min_score`]) || 0.50)) * (parseFloat(settings[`short_${tier}_lev_5x_pct`]) || 0.80)).toFixed(2)}: <strong>5x isolated</strong>
                  </p>
                </div>

                {/* Short Allowed Regimes Selection */}
                <div style={{ marginTop: '14px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '10px', position: 'relative' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <label style={labelStyle}>Regimes Permitidos (Mercado)</label>
                    {isShortRegimeDivergent && (
                      <div 
                        onClick={() => toggleTooltip(`short_${tier}_allowed_regimes`)}
                        style={{ display: 'inline-block', position: 'relative', cursor: 'pointer' }}
                      >
                        <span
                          style={{
                            background: 'rgba(234,179,8,0.15)',
                            color: '#fde047',
                            border: '1px solid rgba(234,179,8,0.4)',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: 700,
                            padding: '1px 6px',
                            cursor: 'pointer'
                          }}
                        >
                          ⚠️ Destoante
                        </span>

                        {activeTooltip === `short_${tier}_allowed_regimes` && (
                          <div style={{
                            position: 'absolute',
                            bottom: '100%',
                            right: 0,
                            width: '260px',
                            background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                            border: '1px solid rgba(234,179,8,0.5)',
                            borderRadius: '8px',
                            padding: '12px 14px',
                            zIndex: 200,
                            marginBottom: '6px',
                            boxShadow: '0 8px 20px rgba(0,0,0,0.5)',
                            color: '#cbd5e1',
                            fontSize: '11px',
                            lineHeight: '1.4'
                          }}>
                            <p style={{ margin: '0 0 6px 0', color: '#fde047', fontWeight: 700 }}>🔬 Recomendação de Regimes SHORT</p>
                            <p style={{ margin: '0 0 10px 0' }}>O simulador shadow detectou que operar SHORT durante mercados de queda (Bear) aumenta o risco de repiques violentos e estocada de perdas. O ideal é operar apenas em Bull / Neutral.</p>
                            <button
                              type="button"
                              onClick={() => {
                                handleChange(`short_${tier}_allowed_regimes`, SHADOW_OPTIMAL[`short_${tier}_allowed_regimes`]);
                                setActiveTooltip(null);
                              }}
                              style={{
                                background: 'linear-gradient(135deg, #eab308 0%, #ca8a04 100%)',
                                color: '#0f172a',
                                border: 'none',
                                borderRadius: '4px',
                                padding: '4px 10px',
                                fontWeight: 700,
                                fontSize: '10px',
                                cursor: 'pointer'
                              }}
                            >
                              🪄 Alinhar para Bull/Neutral
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                    {['bull', 'bear', 'neutral'].map(reg => {
                      const currentRegimes = settings[`short_${tier}_allowed_regimes`] ?? ['bear', 'neutral'];
                      const active = currentRegimes.includes(reg);
                      return (
                        <button
                          key={reg}
                          type="button"
                          onClick={() => {
                            const next = active 
                              ? currentRegimes.filter(r => r !== reg)
                              : [...currentRegimes, reg];
                            handleChange(`short_${tier}_allowed_regimes`, next);
                          }}
                          style={{
                            flex: 1,
                            background: active ? 'rgba(239,68,68,0.15)' : 'transparent',
                            color: active ? '#fca5a5' : '#64748b',
                            border: `1px solid ${active ? 'rgba(239,68,68,0.4)' : 'rgba(71,85,105,0.3)'}`,
                            borderRadius: '6px',
                            padding: '6px 4px',
                            fontSize: '11px',
                            fontWeight: 700,
                            cursor: 'pointer',
                            transition: 'all 0.15s',
                            textTransform: 'uppercase'
                          }}
                        >
                          {reg === 'bull' ? '🐂 Bull' : reg === 'bear' ? '🐻 Bear' : '➖ Lateral'}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

            </div>
          </div>
        );
      })}

      {/* Floating Save Button on bottom mobile */}
      <div style={{ marginTop: '12px', textAlign: 'right' }}>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
            color: '#fff',
            border: 'none',
            borderRadius: '10px',
            padding: '14px 32px',
            fontWeight: 700,
            fontSize: '15px',
            cursor: 'pointer',
            boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)',
            transition: 'all 0.2s',
            opacity: saving ? 0.7 : 1
          }}
        >
          {saving ? 'Gravando...' : 'Salvar Todas as Configurações'}
        </button>
      </div>

    </div>
  );
}
