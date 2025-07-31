import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";

export default function ComparativaGlobal() {
  const [datos, setDatos] = useState([]);
  const [tipoPrecio, setTipoPrecio] = useState("open");

  const etiquetasPrecios = {
    open: "Apertura",
    close: "Cierre",
  };

  const colores = {
    MIN: "#34d399",     // Verde menta
    MEDIAN: "#fbbf24",  // Amarillo
    MEAN: "#60a5fa",    // Azul claro
    MAX: "#f87171",     // Rojo claro
  };

  const etiquetasEstadisticas = {
    MIN: "Mínimo",
    MEDIAN: "Mediana",
    MEAN: "Media",
    MAX: "Máximo",
  };

  useEffect(() => {
    fetch("http://localhost:8001/stats/prices")
      .then((res) => res.json())
      .then((data) => {
        const stats = data.price_statistics;
        const orden = ["min", "median", "mean", "max"];
        const transformados = orden.map((tipo) => ({
          name: tipo.toUpperCase(),
          valor: stats[tipo][tipoPrecio],
        }));
        setDatos(transformados);
      });
  }, [tipoPrecio]);

  return (
    <div className="p-4">
      <h2 className="text-xl font-semibold mb-4 text-red-300">
        Precios Globales de {etiquetasPrecios[tipoPrecio]}
      </h2>

      <div className="mb-4">
        <label className="text-xl font-semibold mb-4 text-red-300">
          Selecciona tipo de precio:
        </label>
        <select
          value={tipoPrecio}
          onChange={(e) => setTipoPrecio(e.target.value)}
          className="bg-white text-black px-3 py-1 rounded-md shadow-sm border border-gray-300"
        >
          <option value="open">Apertura</option>
          <option value="close">Cierre</option>
        </select>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={datos}
          barCategoryGap={50}
          margin={{ top: 20, right: 30, left: 10, bottom: 40 }}
        >
          <XAxis
            dataKey="name"
            tickFormatter={(value) => etiquetasEstadisticas[value] || value}
            tick={{ fontSize: 14, fill: "#e5e7eb" }}
          />
          <YAxis
            scale="log"
            domain={["auto", "auto"]}
            tickFormatter={(value) =>
              `$${value.toLocaleString("en-US", {
                minimumFractionDigits: 2,
              })}`
            }
            tick={{ fontSize: 12, fill: "#e5e7eb" }}
          />
          <Tooltip
            formatter={(value, name, props) => [
              value.toLocaleString("en-US", {
                style: "currency",
                currency: "USD",
                minimumFractionDigits: 2,
              }),
              etiquetasEstadisticas[props.payload.name] || name,
            ]}
          />
          <Legend
            content={() => (
              <div style={{ color: "#ffffff", textAlign: "center", marginTop: "10px" }}>
                {etiquetasPrecios[tipoPrecio]}
              </div>
            )}
          />
          <Bar dataKey="valor" name={etiquetasPrecios[tipoPrecio]} radius={[4, 4, 0, 0]}>
            {datos.map((entrada, index) => (
              <Cell key={`cell-${index}`} fill={colores[entrada.name]} />
            ))}
            <LabelList
              dataKey="valor"
              position="top"
              formatter={(value) =>
                value.toLocaleString("en-US", {
                  style: "currency",
                  currency: "USD",
                  minimumFractionDigits: 2,
                })
              }
              style={{ fontSize: 12, fill: "#ffffff", fontWeight: "bold" }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
