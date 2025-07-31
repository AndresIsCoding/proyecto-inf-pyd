import React, { useState, useEffect } from 'react'; 
import './App.css'
import Top5Chart from './Top5Chart'; 
import GlobalPriceComparisonChart from './GlobalPriceComparisonChart';
import ComparativaAperturaCierre from "./ComparativaAperturaCierre";
import TickerCharts from './TickerCharts'
import DualRadarChart from './DualRadarChart';

const MS_STATS_URL = "http://localhost:8001"; // Your ms_stats service URL

// Helper component to display JSON data
const JsonDisplay = ({ data, error }) => {
    if (error) {
        return <pre className="bg-red-900 text-red-200 p-4 rounded-lg overflow-auto text-sm whitespace-pre-wrap break-all min-h-[100px]">{JSON.stringify(error, null, 2)}</pre>;
    }
    if (!data) {
        return <pre className="bg-gray-800 text-gray-400 p-4 rounded-lg overflow-auto text-sm whitespace-pre-wrap break-all min-h-[100px]">No data loaded yet.</pre>;
    }
    return <pre className="bg-gray-800 text-gray-200 p-4 rounded-lg overflow-auto text-sm whitespace-pre-wrap break-all min-h-[100px]">{JSON.stringify(data, null, 2)}</pre>;
};

// Main App component
const App = () => {
    // State for fetched data
    const [healthData, setHealthData] = useState(null);
    const [reloadResult, setReloadResult] = useState(null);
    const [basicStats, setBasicStats] = useState(null);
    const [summaryStats, setSummaryStats] = useState(null);
    const [priceStats, setPriceStats] = useState(null);
    const [tickerStats, setTickerStats] = useState(null);

    // State for input fields
    const [tickerInput, setTickerInput] = useState('');

    // State for loading indicators
    const [loading, setLoading] = useState({
        health: false,
        reload: false,
        basic: false,
        summary: false,
        price: false,
        ticker: false,
    });

    // State for errors
    const [error, setError] = useState({
        health: null,
        reload: null,
        basic: null,
        summary: null,
        price: null,
        ticker: null,
    });

    

    //Comparation two tickers
    const [compareTickers, setCompareTickers] = useState(['', '']);
    const [compareStats, setCompareStats] = useState({});
    const [loadingCompare, setLoadingCompare] = useState(false);
    const [errorCompare, setErrorCompare] = useState(null);

    const fetchCompareStats = async () => {
    const [t1, t2] = compareTickers.map(t => t.toUpperCase());
    if (!t1 || !t2 || t1 === t2) {
        setErrorCompare({ message: "Introduce dos tickers distintos." });
        return;
    }

    setLoadingCompare(true);
    setErrorCompare(null);

    try {
        const [res1, res2] = await Promise.all([
        fetch(`${MS_STATS_URL}/stats/by_ticker/${t1}`),
        fetch(`${MS_STATS_URL}/stats/by_ticker/${t2}`),
        ]);
        const [data1, data2] = await Promise.all([res1.json(), res2.json()]);

        if (!res1.ok || !res2.ok) {
        throw new Error("Uno o ambos tickers no devolvieron datos válidos.");
        }

        setCompareStats({ [t1]: data1.statistics, [t2]: data2.statistics });
    } catch (err) {
        setErrorCompare({ message: err.message });
        setCompareStats({});
    } finally {
        setLoadingCompare(false);
    }
    };






    // Helper function to make API calls
    const fetchData = async (endpoint, setter, loadingKey, errorKey, method = 'GET') => {
        setLoading(prev => ({ ...prev, [loadingKey]: true }));
        setError(prev => ({ ...prev, [errorKey]: null }));
        try {
            const response = await fetch(`${MS_STATS_URL}${endpoint}`, { method });
            const data = await response.json();
            if (response.ok) {
                setter(data);
            } else {
                setError(prev => ({ ...prev, [errorKey]: data }));
                setter(null); // Clear previous data on error
            }
        } catch (err) {
            setError(prev => ({ ...prev, [errorKey]: { message: `Network error: ${err.message}. Ensure ms_stats is running at ${MS_STATS_URL}.` } }));
            setter(null); // Clear previous data on network error
        } finally {
            setLoading(prev => ({ ...prev, [loadingKey]: false }));
        }
    };
    
    // Fetch Health Status
    const fetchHealth = () => fetchData('/health', setHealthData, 'health', 'health');

    // Reload Data
    const reloadStatsData = async () => {
        setLoading(prev => ({ ...prev, reload: true }));
        setError(prev => ({ ...prev, reload: null }));
        try {
            const response = await fetch(`${MS_STATS_URL}/stats/reload`, { method: 'GET' });
            const data = await response.json();
            setReloadResult(data);
            if (!response.ok) {
                setError(prev => ({ ...prev, reload: data }));
            }
            fetchHealth(); // Refresh health status after reload attempt
        } catch (err) {
            setError(prev => ({ ...prev, reload: { message: `Error reloading data: ${err.message}` } }));
        } finally {
            setLoading(prev => ({ ...prev, reload: false }));
        }
    };

    const [topTickers, setTopTickers] = useState([]);
    const [loadingTop, setLoadingTop] = useState(false);
    const [errorTop, setErrorTop] = useState(null);

    // Fetch Basic Stats
    const fetchBasicStats = () => fetchData('/stats/basic', setBasicStats, 'basic', 'basic');

    // Fetch Summary Stats
    const fetchSummaryStats = () => fetchData('/stats/summary', setSummaryStats, 'summary', 'summary');

    // Fetch Price Stats
    const fetchPriceStats = () => fetchData('/stats/prices', setPriceStats, 'price', 'price');

    // Fetch Ticker Stats
    const fetchTickerStats = () => {
        if (!tickerInput.trim()) {
            setError(prev => ({ ...prev, ticker: { message: "Please enter a ticker symbol." } }));
            setTickerStats(null);
            return;
        }
        fetchData(`/stats/by_ticker/${tickerInput.toUpperCase()}`, setTickerStats, 'ticker', 'ticker');
    };


    const fetchTopValuedTickers = async () => {
        setLoadingTop(true);
        setErrorTop(null);
        try {
            // Paso 1: Obtener sample tickers
            const summaryRes = await fetch(`${MS_STATS_URL}/stats/summary`);
            const summaryData = await summaryRes.json();
            const sampleTickers = summaryData.sample_tickers;

            // Paso 2: Hacer fetch a cada ticker y calcular su promedio de cierre
            const results = await Promise.allSettled(sampleTickers.map(async (ticker) => {
                const res = await fetch(`${MS_STATS_URL}/stats/by_ticker/${ticker}`);
                if (!res.ok) throw new Error(`Error fetching ${ticker}`);
                const data = await res.json();
                return {
                    ticker: data.ticker,
                    averageClose: data.statistics.mean.close
                };
            }));

            // Paso 3: Filtrar errores y ordenar
            const successful = results
                .filter(r => r.status === 'fulfilled')
                .map(r => r.value)
                .sort((a, b) => b.averageClose - a.averageClose)
                .slice(0, 5);

            setTopTickers(successful);
        } catch (err) {
            setErrorTop(err.message);
        } finally {
            setLoadingTop(false);
        }
    };


    //Carga de datos automatica
    const [autoReloadTriggered, setAutoReloadTriggered] = useState(false);

    useEffect(() => {
    if (!autoReloadTriggered && healthData) {
        const isLoaderOk = healthData.ms_loader_connection?.toLowerCase() === 'ok';
        const isStatsNotReady = healthData.data_loaded !== true;

        if (isLoaderOk && isStatsNotReady) {
            console.log('⏳ Triggering auto reload...');
            reloadStatsData();  // ejecuta la recarga
            setAutoReloadTriggered(true); // evita múltiples recargas
        }
    }
}, [healthData, autoReloadTriggered]);

    // Initial load of health status when the component mounts
    useEffect(() => {
    // Llamada inicial
    fetchHealth();

    // Configurar recarga automática cada 10 segundos
    const interval = setInterval(() => {
        fetchHealth();
    }, 60000); // 60000 ms = 1 minuto

    // Limpiar el intervalo al desmontar el componente
    return () => clearInterval(interval);
}, []);

    // Function to render status indicator
    const renderStatusIndicator = (status) => {
        let className = 'status-unknown';
        if (status === 'ok' || status === true) {
            className = 'status-ok';
        } else if (status === 'error' || status === false) {
            className = 'status-error';
        } else if (status === 'starting' || status === 'loading') {
            className = 'status-loading';
        }
        return <span className={`status-indicator ${className}`}></span>;
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-gray-100 p-4 font-inter">
            <div className="max-w-6xl mx-auto py-8 px-6 bg-gray-900 rounded-2xl shadow-2xl">
                <h1 className="text-5xl font-extrabold text-center mb-12 text-blue-400 drop-shadow-lg">
                    📊 Panel de Estadísticas Financieras
                </h1>

                {/* Health Check Section */}
                <div className="bg-gray-800 p-8 rounded-xl shadow-lg mb-8 border border-gray-700">
    {/* Health Title with dynamic color and emoji */}
    {!loading.health && !error.health && healthData ? (() => {
        const isStatsReady = healthData.data_loaded;
        const isLoaderReady = ["connected", "ok"].includes(healthData.ms_loader_connection?.toLowerCase());
        const isLoading = healthData.loading;

        let titleColor = "text-red-400";
        let statusEmoji = "❌";

        if (isStatsReady && isLoaderReady) {
            titleColor = "text-green-400";
            statusEmoji = "🟢";
        } else if (isLoading || healthData.ms_loader_connection?.toLowerCase() === "connecting") {
            titleColor = "text-yellow-400";
            statusEmoji = "⏳";
        }

        return (
            <h2 className={`text-3xl font-semibold mb-6 ${titleColor}`}>
                {statusEmoji} Estado del Servicio
            </h2>
        );
    })() : (
        <h2 className="text-3xl font-semibold mb-6 text-blue-300">Estado del Servicio</h2>
    )}

                    {/* Health Data */}
                    <div className="text-lg mb-6">
                        {loading.health ? (
                            <p className="text-gray-400">Fetching health status...</p>
                        ) : error.health ? (
                            <p className="text-red-400">Error: {error.health.message || JSON.stringify(error.health)}</p>
                        ) : healthData && (
                            <>
                                <p className="mb-2">
                                    <strong>Servicio ms_stats:</strong>{" "}
                                    <span className={healthData.data_loaded ? "text-green-400 font-semibold" : "text-yellow-400 font-semibold"}>
                                        {healthData.data_loaded ? "Ready" : (healthData.loading ? "Loading" : "No Data")}
                                    </span>
                                </p>
                                <p className="ml-4 text-gray-400">Registros Cargados: {healthData.records}</p>
                                <p className="ml-4 text-gray-400">Mensaje: {healthData.message}</p>

                                <p className="mt-4 mb-2">
                                    <strong>Conexión ms_loader:</strong>{" "}
                                    <span className={
                                        ["connected", "ok"].includes(healthData.ms_loader_connection?.toLowerCase())
                                            ? "text-green-400 font-semibold"
                                            : (healthData.ms_loader_connection?.toLowerCase() === "connecting"
                                                ? "text-yellow-400 font-semibold"
                                                : "text-red-400 font-semibold")
                                    }>
                                        {healthData.ms_loader_connection}
                                    </span>
                                </p>
                                
                                <p className="ml-4 text-gray-400">Estado del Cargador: {JSON.stringify(healthData.ms_loader_status, null, 2)}</p>
                            </>
                        )}
                    </div>

                    {/* Refresh Button */}
                    <button
                        onClick={fetchHealth}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition duration-300 ease-in-out transform hover:scale-105"
                        disabled={loading.health}
                    >
                        {loading.health ? 'Refrescando...' : 'Refrescar la Salud'}
                    </button>
                </div>


                {/* Reload Data Section */} 
                            
                <div className="bg-gray-800 p-8 rounded-xl shadow-lg mb-8 border border-gray-700">
                    <h2 className="text-3xl font-semibold mb-6 text-purple-300">Recargar Datos</h2>
                    <p className="mb-6 text-gray-300">Activar manualmente una recarga de datos desde `ms_loader`. Esto resulta útil si la carga de datos ha fallado inicialmente.</p>
                    <button
                        onClick={reloadStatsData}
                        className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-6 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-opacity-50 transition duration-300 ease-in-out transform hover:scale-105"
                        disabled={loading.reload}
                    >
                        {loading.reload ? 'Recargando...' : 'Recargar Datos'}
                    </button>
                    {reloadResult && (
                        <div className="mt-6 text-sm text-gray-300">
                            <p className={reloadResult.success ? 'text-green-400' : 'text-red-400'}>
                                {reloadResult.message}
                            </p>
                        </div>
                    )}
                </div>

                {/* Statistics Sections Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">



                {/* Price Stats */}
                <div className="bg-gray-800 p-8 rounded-xl shadow-lg mb-8 border border-gray-700">
                    <h2 className="text-3xl font-semibold mb-6 text-red-300">Estadísticas de Precio</h2>
                    <button
                        onClick={fetchPriceStats}
                        className="bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-6 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 mb-6 transition duration-300 ease-in-out transform hover:scale-105"
                        disabled={loading.price}
                    >
                        {loading.price ? 'Cargando...' : 'Estadísticas de Precios'}
                    </button>

                    {/* REMOVED: <JsonDisplay data={priceStats} error={error.price} /> */}

                    {priceStats && (
                        <div className="mt-8">
                            <GlobalPriceComparisonChart />
                            <ComparativaAperturaCierre />
                        </div>
                    )}
                </div>







                
                    {/* Top 5 Valued Companies */}
                <div className="bg-gray-800 p-8 rounded-xl shadow-lg mb-8 border border-gray-700">
                    <h2 className="text-3xl font-semibold mb-6 text-green-300">Top 5 Empresas Más Valiosas</h2>
                    <button
                        onClick={fetchTopValuedTickers}
                        className="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50 mb-6 transition duration-300 ease-in-out transform hover:scale-105"
                        disabled={loadingTop}
                    >
                        {loadingTop ? 'Cargando...' : 'Obtener Top 5'}
                    </button>

                    {errorTop && <p className="text-red-400">{errorTop}</p>}

                    {topTickers.length > 0 && (
                        <Top5Chart data={topTickers} />
                    )}
                </div>


                   {/* Ticker Specific Stats */}
                <div className="bg-gray-800 p-8 rounded-xl shadow-lg border border-gray-700">
                    <h2 className="text-3xl font-semibold mb-6 text-indigo-300">Estadísticas de Ticker</h2>
                    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-6">
                        <input
                            type="text"
                            id="tickerInput"
                            placeholder="Introduzca el Ticker (e.g., AAPL)"
                            value={tickerInput}
                            onChange={(e) => setTickerInput(e.target.value)}
                            className="flex-grow bg-gray-700 text-gray-100 border border-gray-600 rounded-lg p-3 text-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition duration-200 ease-in-out"
                        />
                        <button
                            onClick={fetchTickerStats}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-50 w-full sm:w-auto transition duration-300 ease-in-out transform hover:scale-105"
                            disabled={loading.ticker}
                        >
                            {loading.ticker ? 'Cargando...' : 'Estadísticas del Ticker'}
                        </button>
                    </div>
                    {tickerStats && !error.ticker && (
                        <TickerCharts stats={tickerStats} />
                    )}
                </div>







                    {/* Comparador de dos Tickers */}
                    <div className="bg-gray-800 p-8 rounded-xl shadow-lg border border-gray-700 mt-8">
                    <h2 className="text-3xl font-semibold mb-6 text-white">Comparar Dos Tickers</h2>
                    <div className="flex flex-col sm:flex-row gap-4 mb-6">
                        <input
                        type="text"
                        placeholder="Primer Ticker (ej. AAPL)"
                        value={compareTickers[0]}
                        onChange={(e) => setCompareTickers([e.target.value, compareTickers[1]])}
                        className="flex-grow bg-gray-700 text-gray-100 border border-gray-600 rounded-lg p-3 text-lg"
                        />
                        <input
                        type="text"
                        placeholder="Segundo Ticker (ej. MSFT)"
                        value={compareTickers[1]}
                        onChange={(e) => setCompareTickers([compareTickers[0], e.target.value])}
                        className="flex-grow bg-gray-700 text-gray-100 border border-gray-600 rounded-lg p-3 text-lg"
                        />
                        <button
                        onClick={fetchCompareStats}
                        className="bg-white hover:bg-gray-100 text-black font-bold py-3 px-6 rounded-lg focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50 w-full sm:w-auto transition duration-300 ease-in-out transform hover:scale-105"
                        disabled={loadingCompare}
                        >
                        {loadingCompare ? 'Cargando...' : 'Comparar Tickers'}
                        </button>
                    </div>

                    {errorCompare && <p className="text-red-400 mb-4">{errorCompare.message}</p>}

                    {Object.keys(compareStats).length === 2 && (
                        <DualRadarChart
                        data={compareStats}
                        tickers={compareTickers.map((t) => t.toUpperCase())}
                        />
                    )}
                    </div>


              
                    
                </div>
                

            </div>
        </div>
    );
};

export default App;