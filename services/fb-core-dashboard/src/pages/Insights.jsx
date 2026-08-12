import React, { useState, useEffect } from 'react';
import { Spinner } from '../components/UI';

export default function Insights() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(20);
  const [loading, setLoading] = useState(true);

  // Filtros
  const [symbolFilter, setSymbolFilter] = useState('');
  const [decisionFilter, setDecisionFilter] = useState('');
  const [trendFilter, setTrendFilter] = useState('');

  // Estados aplicados para a requisição
  const [appliedSymbol, setAppliedSymbol] = useState('');
  const [appliedDecision, setAppliedDecision] = useState('');
  const [appliedTrend, setAppliedTrend] = useState('');

  const fetchInsights = () => {
    setLoading(true);
    let url = `/api/insights?page=${page}&limit=${limit}`;
    if (appliedSymbol) url += `&symbol=${encodeURIComponent(appliedSymbol)}`;
    if (appliedDecision) url += `&decision=${encodeURIComponent(appliedDecision)}`;
    if (appliedTrend) url += `&trend=${encodeURIComponent(appliedTrend)}`;

    fetch(url)
      .then(res => res.json())
      .then(data => {
        setItems(data.items || []);
        setTotal(data.total || 0);
        setLoading(false);
      })
      .catch(err => {
        console.error("Erro ao buscar insights:", err);
        setLoading(false);
      });
  };

  // Faz a requisição sempre que mudar a paginação ou os filtros aplicados
  useEffect(() => {
    fetchInsights();
  }, [page, limit, appliedSymbol, appliedDecision, appliedTrend]);

  const handleApplyFilters = (e) => {
    e.preventDefault();
    setPage(1);
    setAppliedSymbol(symbolFilter);
    setAppliedDecision(decisionFilter);
    setAppliedTrend(trendFilter);
  };

  const handleClearFilters = () => {
    setSymbolFilter('');
    setDecisionFilter('');
    setTrendFilter('');
    setPage(1);
    setAppliedSymbol('');
    setAppliedDecision('');
    setAppliedTrend('');
  };

  const totalPages = Math.ceil(total / limit) || 1;

  // Renderizadores de badges com cores correspondentes
  const renderDecisionBadge = (decision) => {
    const badges = {
      'ACCEPTED': 'bg-green-500/20 text-green-400 border border-green-500/30',
      'REJECTED_LATERAL': 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
      'REJECTED_REGIME': 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
      'REJECTED_SCORE': 'bg-red-500/20 text-red-400 border border-red-500/30',
      'REJECTED_PENALTY': 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
      'REJECTED_RSI': 'bg-pink-500/20 text-pink-400 border border-pink-500/30',
      'REJECTED_COOLDOWN': 'bg-teal-500/20 text-teal-400 border border-teal-500/30',
      'REJECTED_TIER': 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30',
      'REJECTED_HOURS': 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
      'REJECTED_NO_DATA': 'bg-slate-500/20 text-slate-400 border border-slate-500/30'
    };

    const label = {
      'ACCEPTED': 'Aceito',
      'REJECTED_LATERAL': 'Lateral (Neutral)',
      'REJECTED_REGIME': 'Contra Regime',
      'REJECTED_SCORE': 'Score Baixo',
      'REJECTED_PENALTY': 'Penalidade Risco',
      'REJECTED_RSI': 'RSI Rejeitado',
      'REJECTED_COOLDOWN': 'Cooldown Stop Loss',
      'REJECTED_TIER': 'Tier Rejeitado',
      'REJECTED_HOURS': 'Horário Restrito',
      'REJECTED_NO_DATA': 'Sem Dados'
    };

    const badgeClass = badges[decision] || 'bg-slate-700 text-slate-300';
    const text = label[decision] || decision;

    return (
      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${badgeClass}`}>
        {text}
      </span>
    );
  };

  const renderDirectionBadge = (dir) => {
    return dir === 'SHORT' ? (
      <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-500/10 text-red-400 border border-red-500/20">SHORT</span>
    ) : (
      <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">LONG</span>
    );
  };

  const renderTrendBadge = (trend) => {
    if (trend === 'bull') {
      return <span className="text-green-400 flex items-center gap-1 font-semibold text-xs">🐂 BULL</span>;
    } else if (trend === 'bear') {
      return <span className="text-red-400 flex items-center gap-1 font-semibold text-xs">🐻 BEAR</span>;
    }
    return <span className="text-slate-400 flex items-center gap-1 font-semibold text-xs">➖ NEUTRAL</span>;
  };

  const renderTradeStatus = (trade) => {
    if (!trade) return <span className="text-slate-600">-</span>;
    
    const isClosed = trade.status === 'CLOSED';
    const pnl = trade.pnl_pct;
    
    let pnlClass = 'text-slate-400';
    let pnlText = 'OPEN';
    
    if (isClosed) {
      if (pnl > 0) {
        pnlClass = 'text-green-400 font-bold';
        pnlText = `+${pnl.toFixed(2)}% (${trade.exit_reason || 'TAKE_PROFIT'})`;
      } else if (pnl < 0) {
        pnlClass = 'text-red-400 font-bold';
        pnlText = `${pnl.toFixed(2)}% (${trade.exit_reason || 'STOP_LOSS'})`;
      } else {
        pnlText = `0.00% (${trade.exit_reason})`;
      }
    }
    
    return (
      <div className="text-xs">
        <span className={`px-1.5 py-0.5 rounded mr-1.5 font-bold ${isClosed ? 'bg-slate-700 text-slate-300' : 'bg-green-500/20 text-green-400 border border-green-500/30'}`}>
          {trade.status}
        </span>
        <span className={pnlClass}>{pnlText}</span>
        {trade.is_futures && (
          <span className="ml-1 text-[10px] bg-amber-500/20 text-amber-400 px-1 py-0.2 rounded border border-amber-500/20">
            {trade.leverage}x
          </span>
        )}
      </div>
    );
  };

  return (
    <div className="p-6">
      {/* Cabeçalho */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Insights de Avaliação dos Modelos</h1>
        <p className="text-slate-400">
          Analise o histórico completo de sinais gerados pelos modelos de machine learning e veja detalhadamente as decisões tomadas pelo motor crítico e os resultados correspondentes.
        </p>
      </div>

      {/* Bloco de Filtros */}
      <form onSubmit={handleApplyFilters} className="bg-slate-900/60 backdrop-blur-md border border-slate-800 p-5 rounded-xl mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-slate-400 text-xs font-semibold mb-2 uppercase">Moeda</label>
            <input 
              type="text" 
              placeholder="Ex: BTC/USDT" 
              value={symbolFilter} 
              onChange={e => setSymbolFilter(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2.5 focus:outline-none focus:border-blue-500 text-sm transition-colors placeholder-slate-500"
            />
          </div>

          <div>
            <label className="block text-slate-400 text-xs font-semibold mb-2 uppercase">Decisão</label>
            <select 
              value={decisionFilter} 
              onChange={e => setDecisionFilter(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2.5 focus:outline-none focus:border-blue-500 text-sm transition-colors"
            >
              <option value="">Todas</option>
              <option value="ACCEPTED">Aceito (Operou)</option>
              <option value="REJECTED_LATERAL">Lateral (Neutral)</option>
              <option value="REJECTED_REGIME">Contra Regime</option>
              <option value="REJECTED_SCORE">Score Insuficiente</option>
              <option value="REJECTED_PENALTY">Penalidade de Risco</option>
              <option value="REJECTED_RSI">RSI Inadequado</option>
              <option value="REJECTED_COOLDOWN">Cooldown Stop Loss</option>
              <option value="REJECTED_TIER">Tier Rejeitado</option>
              <option value="REJECTED_HOURS">Horário Restrito</option>
              <option value="REJECTED_NO_DATA">Sem Dados</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 text-xs font-semibold mb-2 uppercase">Regime BTC</label>
            <select 
              value={trendFilter} 
              onChange={e => setTrendFilter(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2.5 focus:outline-none focus:border-blue-500 text-sm transition-colors"
            >
              <option value="">Todos</option>
              <option value="bull">Bull (Alta)</option>
              <option value="bear">Bear (Baixa)</option>
              <option value="neutral">Neutral (Lateral)</option>
            </select>
          </div>

          <div className="flex gap-2">
            <button 
              type="submit"
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg px-4 py-2.5 text-sm transition-colors shadow-lg shadow-blue-500/10 cursor-pointer"
            >
              Filtrar
            </button>
            <button 
              type="button" 
              onClick={handleClearFilters}
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-lg px-4 py-2.5 text-sm transition-colors cursor-pointer"
            >
              Limpar
            </button>
          </div>
        </div>
      </form>

      {/* Tabela de Resultados */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-sm">
        {loading ? (
          <div className="p-20 flex justify-center items-center">
            <Spinner />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 text-xs uppercase font-bold bg-slate-900/80">
                  <th className="py-4 px-6">Data</th>
                  <th className="py-4 px-6">Moeda</th>
                  <th className="py-4 px-6">Direção</th>
                  <th className="py-4 px-6">Regime BTC</th>
                  <th className="py-4 px-6">Score</th>
                  <th className="py-4 px-6">RSI</th>
                  <th className="py-4 px-6">Decisão</th>
                  <th className="py-4 px-6">Resultado do Trade</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300 text-sm">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-4 px-6 text-slate-400 font-mono text-xs">
                      {item.created_at}
                    </td>
                    <td className="py-4 px-6 font-bold text-white">
                      {item.symbol}
                      <span className="block text-[10px] text-slate-500 font-normal">
                        {item.strategy || item.tier}
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      {renderDirectionBadge(item.direction)}
                    </td>
                    <td className="py-4 px-6">
                      {renderTrendBadge(item.btc_trend)}
                    </td>
                    <td className="py-4 px-6 font-mono font-medium">
                      {item.score?.toFixed(3)}
                    </td>
                    <td className="py-4 px-6 font-mono text-slate-400">
                      {item.rsi != null ? item.rsi.toFixed(1) : '-'}
                    </td>
                    <td className="py-4 px-6">
                      {renderDecisionBadge(item.decision)}
                    </td>
                    <td className="py-4 px-6">
                      {renderTradeStatus(item.trade)}
                    </td>
                  </tr>
                ))}

                {items.length === 0 && (
                  <tr>
                    <td colSpan="8" className="py-12 text-center text-slate-500 text-base">
                      Nenhuma avaliação encontrada com os filtros selecionados.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginação */}
        {!loading && total > 0 && (
          <div className="bg-slate-900/60 px-6 py-4 flex flex-col sm:flex-row items-center justify-between border-t border-slate-800 gap-4">
            <div className="text-xs text-slate-500">
              Mostrando <span className="font-semibold text-slate-300">{items.length}</span> de{' '}
              <span className="font-semibold text-slate-300">{total}</span> avaliações.
            </div>
            
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">Exibir</span>
                <select 
                  value={limit} 
                  onChange={e => { setLimit(Number(e.target.value)); setPage(1); }}
                  className="bg-slate-800 border border-slate-700 text-slate-300 text-xs rounded px-2.5 py-1 focus:outline-none"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <button 
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 rounded bg-slate-800 text-slate-400 hover:text-white border border-slate-700 hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-slate-800 disabled:hover:text-slate-400 text-xs font-semibold transition-colors cursor-pointer"
                >
                  Anterior
                </button>
                
                <span className="text-xs text-slate-400 px-2 font-medium">
                  {page} / {totalPages}
                </span>

                <button 
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 rounded bg-slate-800 text-slate-400 hover:text-white border border-slate-700 hover:bg-slate-700 disabled:opacity-30 disabled:hover:bg-slate-800 disabled:hover:text-slate-400 text-xs font-semibold transition-colors cursor-pointer"
                >
                  Próxima
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
