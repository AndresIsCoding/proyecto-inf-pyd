import React from 'react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const metricasTraducidas = {
  'adj close': 'Cierre ajustado',
  'close': 'Cierre',
  'high': 'Máximo',
  'low': 'Mínimo',
  'open': 'Apertura'
};

const DualRadarChart = ({ data, tickers }) => {
  if (!tickers || tickers.length !== 2) return null;

  const tickerA = tickers[0];
  const tickerB = tickers[1];

  if (!data[tickerA] || !data[tickerB]) return null;

  const keys = Object.keys(data[tickerA].mean || {}).filter(
    key =>
      key !== 'volume' &&
      key in data[tickerB].mean &&
      !isNaN(data[tickerA].mean[key]) &&
      !isNaN(data[tickerB].mean[key])
  );

  const radarData = keys.map(key => ({
    métrica: metricasTraducidas[key] || key,
    [tickerA]: data[tickerA].mean[key],
    [tickerB]: data[tickerB].mean[key]
  }));

  const formatDolar = (value, name) => {
    return [`$${value.toFixed(2)}`, name];
  };

  return (
    <div className="bg-gray-800 p-6 rounded-xl shadow-lg mt-6">
      <h2 className="text-xl text-white font-semibold mb-4 text-center">Comparación de Métricas (Media)</h2>
      <ResponsiveContainer width="100%" height={400}>
        <RadarChart data={radarData}>
          <PolarGrid />
          <PolarAngleAxis dataKey="métrica" stroke="#ccc" />
          <PolarRadiusAxis angle={30} domain={[0, 'auto']} />
          <Radar
            name={tickerA}
            dataKey={tickerA}
            stroke="#f44336"
            fill="#f44336"
            fillOpacity={0.2}
            strokeWidth={2}
          />
          <Radar
            name={tickerB}
            dataKey={tickerB}
            stroke="#00bcd4"
            fill="#00bcd4"
            fillOpacity={0.2}
            strokeWidth={2}
          />
          <Legend />
          <Tooltip formatter={formatDolar} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default DualRadarChart;
