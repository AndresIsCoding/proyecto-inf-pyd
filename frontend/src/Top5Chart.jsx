import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const opcionesMetricas = [
  { etiqueta: "Promedio de Cierre", valor: "close" },
  { etiqueta: "Promedio de Volumen", valor: "volume" },
  { etiqueta: "Promedio Máximo", valor: "high" },
  { etiqueta: "Promedio Mínimo", valor: "low" },
  { etiqueta: "Promedio de Apertura", valor: "open" },
];

export default function Top5Chart() {
  const [metricaSeleccionada, setMetricaSeleccionada] = useState("close");
  const [top5Datos, setTop5Datos] = useState([]);

  useEffect(() => {
    fetch("http://localhost:8001/stats/summary")
      .then((res) => res.json())
      .then((resumen) => {
        const tickers = resumen.sample_tickers.slice(0, 100);
        Promise.all(
          tickers.map((ticker) =>
            fetch(`http://localhost:8001/stats/by_ticker/${ticker}`)
              .then((res) => res.json())
              .then((data) => ({
                empresa: data.ticker,
                valor: data.statistics.mean[metricaSeleccionada],
              }))
          )
        ).then((datos) => {
          const ordenados = datos
            .filter((d) => !isNaN(d.valor))
            .sort((a, b) => b.valor - a.valor)
            .slice(0, 5);
          setTop5Datos(ordenados);
        });
      });
  }, [metricaSeleccionada]);

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4 text-green-300">
        Empresas por: {opcionesMetricas.find(m => m.valor === metricaSeleccionada)?.etiqueta}
      </h2>

      <select
  className="mb-4 p-2 rounded-lg bg-green-400 text-gray-900 border border-green-600 font-semibold shadow focus:outline-none focus:ring-2 focus:ring-green-600 focus:border-green-700 transition duration-200"
  value={metricaSeleccionada}
  onChange={(e) => setMetricaSeleccionada(e.target.value)}
>
  {opcionesMetricas.map((opcion) => (
    <option
      key={opcion.valor}
      value={opcion.valor}
      className="text-gray-900"
    >
      {opcion.etiqueta}
    </option>
  ))}
</select>


      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={top5Datos}>
          <XAxis dataKey="empresa" />
          <YAxis />
          <Tooltip
  formatter={(value, name) => [
    `${value.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
    })}`,
    name === "valor" ? "Valor promedio" : name,
  ]}
/>
          <Bar dataKey="valor" fill="#10b981" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
