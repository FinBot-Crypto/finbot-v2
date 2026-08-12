import React, { useState, useEffect } from 'react';

export default function Status() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/status')
      .then(res => res.json())
      .then(data => {
        setServices(data.services);
        setLoading(false);
      })
      .catch(err => console.error(err));
  }, []);

  if (loading) {
    return <div className="p-6 text-white">Carregando status do sistema...</div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-white mb-6">Status do Sistema</h1>
      <p className="text-slate-400 mb-6">Monitoramento em tempo real dos serviços do robô.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {services.map((service, index) => {
          const isOnline = service.status === "Online";
          return (
            <div key={index} className="bg-slate-800 p-6 rounded-xl border border-slate-700 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">{service.name}</h3>
                <p className="text-sm text-slate-500">Serviço do ecossistema</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${isOnline ? 'bg-accentGreen pulse' : 'bg-accentRed'}`}></span>
                <span className={`text-sm font-medium ${isOnline ? 'text-accentGreen' : 'text-accentRed'}`}>
                  {service.status}
                </span>
              </div>
            </div>
          );
        })}
        {services.length === 0 && (
          <p className="text-slate-500 col-span-full">Nenhum serviço mapeado.</p>
        )}
      </div>
    </div>
  );
}
