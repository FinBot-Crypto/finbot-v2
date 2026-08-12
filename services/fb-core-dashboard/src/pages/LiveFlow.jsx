import React, { useState, useEffect } from 'react';

const LABELS = {
  market: { icon: '📡', label: 'Market Selection', color: 'border-blue-500' },
  strategy: { icon: '🧠', label: 'Strategy ML', color: 'border-purple-500' },
  decision: { icon: '🎯', label: 'Decision Engine', color: 'border-amber-500' },
  trade: { icon: '💼', label: 'Trade Decision', color: 'border-green-500' },
  exec: { icon: '⚡', label: 'Execution', color: 'border-red-500' },
};

function adjustTime(utcStr, offsetHours = -3) {
  try {
    const ts = utcStr.split(',')[0].replace('T', ' ');  // remove milissegundos
    const parts = ts.split(/[- :]/);
    const d = new Date(Date.UTC(+parts[0], +parts[1]-1, +parts[2], +parts[3], +parts[4], +parts[5]));
    d.setHours(d.getHours() + offsetHours);
    return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch { return utcStr; }
}

function parseBatches(logs) {
  const all = [];
  Object.entries(LABELS).forEach(([key, { icon, label }]) => {
    (logs[key] || []).forEach(line => {
      const timeMatch = line.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/);
      if (timeMatch) {
        all.push({ time: timeMatch[1], timeLocal: adjustTime(timeMatch[1]), service: key, icon, line });
      }
    });
  });
  all.sort((a, b) => a.time.localeCompare(b.time));

  const batches = [];
  let current = null;

  all.forEach(item => {
    if (item.service === 'market' && item.line.includes('Publicado')) {
      if (current) batches.push(current);
      current = { id: item.time, time: item.timeLocal, items: [] };
    }
    if (current) {
      // Remove timestamp prefix e INFO prefix
      let clean = item.line.replace(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ - \w+ - \w+ - /, '');
      current.items.push({ icon: item.icon, line: clean, service: item.service });
    }
  });
  if (current && current.items.length > 0) batches.push(current);
  
  return batches.reverse().slice(0, 4);
}

function getResultEmoji(line) {
  if (line.includes('SIGNAL LONG')) return '🟢';
  if (line.includes('ignora')) return '⏭️';
  if (line.includes('BUY executado')) return '✅';
  if (line.includes('max posições')) return '🚫';
  if (line.includes('Publicados') || line.includes('Publicado')) return '📤';
  if (line.includes('Selecionados')) return '🔍';
  if (line.includes('SELL executado')) return '💰';
  if (line.includes('trailing')) return '📈';
  return '  ';
}

export default function LiveFlow() {
  const [logs, setLogs] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = () => {
      fetch('/api/live-flow')
        .then(res => res.json())
        .then(data => {
          setLogs(data.logs || {});
          setLoading(false);
        })
        .catch(() => {});
    };
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="p-6 text-white">Carregando live flow...</div>;

  const batches = parseBatches(logs);
  const noData = Object.values(logs).every(arr => arr.length === 0);

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-white mb-6">Live Flow</h1>
      
      {noData && <p className="text-slate-500">Aguardando dados dos containers...</p>}

      {batches.map((batch, i) => (
        <div key={i} className="mb-6 bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <div className="bg-slate-900 px-4 py-3 flex items-center gap-2 border-b border-slate-700">
            <span className="text-slate-400 text-sm font-mono">{batch.time}</span>
            <span className="text-accentGreen text-xs font-bold uppercase">Lote {batch.id?.split('T')[0]} {batch.time}</span>
            <span className="text-slate-500 text-xs ml-auto">{batch.items.length} eventos</span>
          </div>
          <div className="divide-y divide-slate-700/50">
            {batch.items.map((item, j) => (
              <div key={j} className="px-4 py-2 hover:bg-slate-700/30 transition-colors flex items-start gap-3">
                <span className="text-sm mt-0.5">{item.icon}</span>
                <span className="text-slate-300 text-xs font-mono flex-1">
                  {getResultEmoji(item.line)} {item.line}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
