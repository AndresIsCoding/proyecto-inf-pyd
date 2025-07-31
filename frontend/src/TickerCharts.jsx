import {
    RadarChart, Radar, PolarGrid, PolarAngleAxis, Tooltip
} from 'recharts';

export default function TickerCharts({ stats }) {
    if (!stats || !stats.statistics) {
        return <p className="text-red-500">No hay estadísticas disponibles</p>;
    }

    const { mean } = stats.statistics;

    // Traducciones de métricas
    const traduccionMetricas = {
        "open": "Apertura",
        "close": "Cierre",
        "high": "Máximo",
        "low": "Mínimo",
        "adj close": "Cierre Ajustado"
    };

    // Filtrar columnas, sin "volume"
    const columnasNumericas = (stats.numeric_columns ?? ["open", "close", "high", "low", "adj close"])
        .filter(col => col.toLowerCase() !== "volume");

    // Datos para el RadarChart con traducciones
    const datosRadar = columnasNumericas.map(col => ({
        métrica: traduccionMetricas[col] || col,
        promedio: mean[col]
    }));

    return (
        <div className="flex justify-center mt-6">
            <div className="bg-gray-900 p-6 rounded-lg shadow border border-gray-700">
                <h3 className="text-xl font-semibold text-indigo-400 mb-4">Promedio por Métrica Financiera</h3>
                <RadarChart cx="50%" cy="50%" outerRadius="80%" width={400} height={300} data={datosRadar}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="métrica" stroke="#ccc" />
                    <Tooltip 
                        formatter={(valor) => [`$${valor.toFixed(2)}`, "Precio promedio"]} 
                        labelFormatter={(label) => `Métrica: ${label}`} 
                    />
                    <Radar 
                        name="Promedio" 
                        dataKey="promedio" 
                        stroke="#38bdf8" 
                        fill="#38bdf8" 
                        fillOpacity={0.6} 
                    />
                </RadarChart>
            </div>
        </div>
    );
}
