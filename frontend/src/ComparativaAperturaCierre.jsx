import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export default function ComparativaAperturaCierre() {
  const [datos, setDatos] = useState([]);

  const etiquetasEstadisticas = {
    min: "Mínimo",
    median: "Mediana",
    mean: "Media",
    max: "Máximo",
  };

  useEffect(() => {
    fetch("http://localhost:8001/stats/prices")
      .then((res) => res.json())
      .then((data) => {
        const stats = data.price_statistics;
        const orden = ["min", "median", "mean", "max"];

        const transformados = orden.map((tipo) => ({
          name: etiquetasEstadisticas[tipo],
          apertura: stats[tipo]["open"],
          cierre: stats[tipo]["close"],
        }));

        setDatos(transformados);
      });
  }, []);

  return (
    <div className="p-4">
      <h2 className="ext-xl font-semibold mb-4 text-blue-300">
        Comparativa Apertura vs Cierre
      </h2>

      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={datos}>
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip
            formatter={(value, name) => [
              value.toLocaleString("en-US", {
                style: "currency",
                currency: "USD",
                minimumFractionDigits: 2,
              }),
              name, // Usa directamente el nombre que ya definiste en cada <Bar />
            ]}
          />

          <Legend
            payload={[
              { id: "apertura", type: "square", value: "Apertura", color: "#60a5fa" },
              { id: "cierre", type: "square", value: "Cierre", color: "#f87171" },
            ]}
          />
          <Bar dataKey="apertura" name="Apertura" fill="#60a5fa" />
          <Bar dataKey="cierre" name="Cierre" fill="#f87171" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
