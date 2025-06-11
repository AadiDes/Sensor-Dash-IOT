import React, { useEffect, useState, useRef } from "react";
import { Card, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Line } from "react-chartjs-2";
import Chart from "chart.js/auto";
import mqtt from "mqtt";
import * as XLSX from "xlsx";
import useDarkMode from "./hooks/useDarkMode";

export default function IOTDashboard() {
  const [theme, toggleTheme] = useDarkMode();
  const [readings, setReadings] = useState([]);
  const [analyticsData, setAnalyticsData] = useState([]);
  const [sensorId, setSensorId] = useState("device1");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [analytics, setAnalytics] = useState(null);
  const [showAnalytics, setShowAnalytics] = useState(false);

  // MQTT client ref to persist across renders
  const mqttClient = useRef(null);

  // Helper to set preset ranges
  const setPreset = (days) => {
    // Set end date to tomorrow to include today's readings
    const end = new Date();
    end.setDate(end.getDate() + 1);
    const start = new Date();
    start.setDate(start.getDate() - days);
    const startStr = start.toISOString().slice(0, 10);
    const endStr = end.toISOString().slice(0, 10);
    setStartDate(startStr);
    setEndDate(endStr);
    fetchData(sensorId, startStr, endStr);
  };

  // Calculate analytics from readings
  const calculateAnalytics = (data) => {
    if (!data || data.length === 0) return null;

    const temps = data.map(r => r.readings?.temperature?.value).filter(v => v != null);
    const humidities = data.map(r => r.readings?.humidity?.value).filter(v => v != null);

    if (temps.length === 0 && humidities.length === 0) return null;

    const tempStats = temps.length > 0 ? {
      min: Math.min(...temps),
      max: Math.max(...temps),
      avg: temps.reduce((a, b) => a + b, 0) / temps.length,
      count: temps.length
    } : null;

    const humidityStats = humidities.length > 0 ? {
      min: Math.min(...humidities),
      max: Math.max(...humidities),
      avg: humidities.reduce((a, b) => a + b, 0) / humidities.length,
      count: humidities.length
    } : null;

    return {
      temperature: tempStats,
      humidity: humidityStats,
      totalReadings: data.length,
      dateRange: {
        start: data[data.length - 1]?.timestamp,
        end: data[0]?.timestamp
      }
    };
  };

  const fetchData = async (id = sensorId, start = startDate, end = endDate) => {
    setLoading(true);
    setError(null);
    try {
      // First fetch data for display (with pagination)
      let url = `http://localhost:5000/api/readings/${id}`;
      const params = [];
      if (start) params.push(`start=${start}`);
      if (end) params.push(`end=${end}`);
      if (params.length) url += "?" + params.join("&");
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }
      const data = await response.json();
      setReadings(data);

      // For analytics, fetch ALL data for the selected period (no pagination limit)
      await fetchAnalyticsData(id, start, end);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalyticsData = async (id = sensorId, start = startDate, end = endDate) => {
    try {
      // Fetch all data for analytics by setting a high page_size
      let url = `http://localhost:5000/api/readings/${id}?page_size=10000`;
      const params = [];
      if (start) params.push(`start=${start}`);
      if (end) params.push(`end=${end}`);
      if (params.length) url += "&" + params.join("&");

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Analytics API returned status ${response.status}`);
      }
      const allData = await response.json();

      // Store complete dataset for analytics and exports
      setAnalyticsData(allData);

      // Calculate analytics on complete dataset
      const analyticsResults = calculateAnalytics(allData);
      setAnalytics(analyticsResults);
    } catch (err) {
      console.error("Failed to fetch analytics data:", err);
      // Fallback to visible data if analytics fetch fails
      setAnalyticsData(readings);
      const analyticsResults = calculateAnalytics(readings);
      setAnalytics(analyticsResults);
    }
  };

  // Export functions - now use complete analyticsData instead of limited readings
  const exportToCSV = () => {
    const dataToExport = analyticsData.length > 0 ? analyticsData : readings;
    if (dataToExport.length === 0) {
      alert("No data to export");
      return;
    }

    const csvData = dataToExport.map(reading => ({
      Timestamp: reading.timestamp,
      'Sensor ID': reading.sensor_id || sensorId,
      'Temperature (°C)': reading.readings?.temperature?.value?.toFixed(2) || 'N/A',
      'Humidity (%)': reading.readings?.humidity?.value?.toFixed(2) || 'N/A'
    }));

    const csvContent = [
      Object.keys(csvData[0]).join(','),
      ...csvData.map(row => Object.values(row).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `sensor_data_${sensorId}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportToExcel = () => {
    const dataToExport = analyticsData.length > 0 ? analyticsData : readings;
    if (dataToExport.length === 0) {
      alert("No data to export");
      return;
    }

    // Prepare data for Excel
    const excelData = dataToExport.map(reading => ({
      'Timestamp': reading.timestamp,
      'Sensor ID': reading.sensor_id || sensorId,
      'Temperature (°C)': reading.readings?.temperature?.value || 'N/A',
      'Humidity (%)': reading.readings?.humidity?.value || 'N/A'
    }));

    // Create workbook and worksheet
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(excelData);

    // Add analytics sheet if available
    if (analytics) {
      const analyticsSheetData = [
        ['Metric', 'Temperature', 'Humidity'],
        ['Minimum', analytics.temperature?.min?.toFixed(2) || 'N/A', analytics.humidity?.min?.toFixed(2) || 'N/A'],
        ['Maximum', analytics.temperature?.max?.toFixed(2) || 'N/A', analytics.humidity?.max?.toFixed(2) || 'N/A'],
        ['Average', analytics.temperature?.avg?.toFixed(2) || 'N/A', analytics.humidity?.avg?.toFixed(2) || 'N/A'],
        ['Count', analytics.temperature?.count || 'N/A', analytics.humidity?.count || 'N/A'],
        ['', '', ''],
        ['Total Readings', analytics.totalReadings, ''],
        ['Date Range', `${analytics.dateRange.start} to ${analytics.dateRange.end}`, ''],
        ['', '', ''],
        ['Period Selected', startDate && endDate ? `${startDate} to ${endDate}` : 'All Data', '']
      ];

      const analyticsWs = XLSX.utils.aoa_to_sheet(analyticsSheetData);
      XLSX.utils.book_append_sheet(wb, analyticsWs, 'Analytics');
    }

    XLSX.utils.book_append_sheet(wb, ws, 'Sensor Data');

    // Save file
    XLSX.writeFile(wb, `sensor_data_${sensorId}_${new Date().toISOString().split('T')[0]}.xlsx`);
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    // Only fetch if both dates are set (to avoid fetching on initial render)
    if (startDate && endDate) {
      fetchData(sensorId, startDate, endDate);
    }
    // eslint-disable-next-line
  }, [startDate, endDate]);

  // --- MQTT Real-time Integration ---
  useEffect(() => {
    // Connect to EMQX public broker over WebSocket
    const client = mqtt.connect("ws://broker.emqx.io:8083/mqtt", {
      username: "emqx",
      password: "public"
    });
    mqttClient.current = client;

    client.on("connect", () => {
      console.log("Connected to EMQX via WebSocket");
      client.subscribe("TEMP/SUB/#");
    });

    client.on("message", (topic, message) => {
      // Parse the message (try JSON, fallback to regex)
      let parsed;
      try {
        parsed = JSON.parse(message.toString());
      } catch {
        const matches = message.toString().match(/([-+]?\d*\.?\d+)/g);
        parsed = {
          temperature: matches && matches[0] ? parseFloat(matches[0]) : null,
          humidity: matches && matches[1] ? parseFloat(matches[1]) : null
        };
      }
      // Create a new reading object
      const newReading = {
        timestamp: new Date().toLocaleString(),
        readings: {
          temperature: { value: parsed.temperature, unit: "C" },
          humidity: { value: parsed.humidity, unit: "%" }
        },
        sensor_id: topic.split("/").pop()
      };
      // Add to readings (prepend, keep max 100)
      setReadings(prev => {
        const updated = [newReading, ...prev].slice(0, 100);
        // Update analytics for real-time data
        const newAnalytics = calculateAnalytics(updated);
        setAnalytics(newAnalytics);
        return updated;
      });
    });

    return () => {
      client.end();
    };
  }, []);

  // Prepare data for the chart
  const labels = readings.map(r => r.timestamp).reverse(); // oldest to newest
  const tempData = readings.map(r => r.readings?.temperature?.value || 0).reverse();
  const humidityData = readings.map(r => r.readings?.humidity?.value || 0).reverse();

  const data = {
    labels,
    datasets: [
      {
        label: "Temperature (°C)",
        data: tempData,
        fill: false,
        borderColor: "rgb(75, 192, 192)",
        tension: 0.1,
        backgroundColor: "rgba(75, 192, 192, 0.2)"
      },
      {
        label: "Humidity (%)",
        data: humidityData,
        fill: false,
        borderColor: "rgb(255, 99, 132)",
        tension: 0.1,
        backgroundColor: "rgba(255, 99, 132, 0.2)"
      }
    ]
  };

  const options = {
    responsive: true,
    scales: {
      x: {
        ticks: {
          autoSkip: false,
          maxTicksLimit: 50,
          color: "#9ca3af"
        },
        grid: {
          color: "rgba(255, 255, 255, 0.1)"
        }
      },
      y: {
        beginAtZero: true,
        ticks: {
          maxTicksLimit: 20,
          color: "#9ca3af"
        },
        grid: {
          color: "rgba(255, 255, 255, 0.1)"
        }
      }
    },
    plugins: {
      legend: {
        labels: {
          color: "#9ca3af"
        }
      }
    }
  };

  return (
    <div className="w-full min-h-screen h-full p-6 grid gap-8 bg-[#fdf6e3] text-black dark:bg-gray-800 dark:text-gray-100 transition-colors duration-300">
    <div className="flex justify-between items-center mb-2">
      <h1 className="text-3xl font-bold flex items-center gap-2 text-black dark:text-gray-100">
        🌡️ IoT Sensor Dashboard
      </h1>
      <button
        onClick={toggleTheme}
        className="text-sm px-3 py-1 rounded bg-black hover:bg-gray-900 text-white dark:bg-gray-200 dark:text-black border border-gray-400 dark:border-gray-600"
      >
          Toggle {theme === 'dark' ? 'Light' : 'Dark'} Mode
        </button>
      </div>

       {/* Additional style override for light mode visibility */}
       <style>{`
        .text-gray-200, .text-gray-400 {
          color:rgb(131, 159, 237) !important; /* navy blue in light mode */
        }
        .bg-gray-700 {
          background-color: #e5e7eb !important; /* lighter input bg */
        }
        .border-gray-600 {
          border-color: #9ca3af !important; /* visible in both modes */
        }
        .hover\:bg-gray-700:hover {
          background-color: #d1d5db !important;
        }
        input[type='date'], input[type='text'], input {
          background-color: #f8f9fa !important; /* light cream box */
          color: #1e3a8a !important;
          border: 1px solid #9ca3af !important;
        }
        .dark input[type='date'],
        .dark input[type='text'],
        .dark input {
          background-color: #1f2937 !important; /* dark bg */
          color: #f3f4f6 !important; /* light text */
          border: 1px solid #4b5563 !important; /* darker border */
        }
      `}</style> 

      {/* Controls Card */}
      <Card className="mb-4 bg-gray-800 border-grey-700 w-full">
        <CardContent className="p-6 flex flex-col gap-4">
          <div className="flex flex-col md:flex-row md:items-end gap-4 flex-wrap">
            <div className="flex flex-col">
              <label className="font-semibold mb-1 text-gray-200">Sensor ID</label>
              <div>
                <Input
                  placeholder="Enter Sensor ID"
                  value={sensorId}
                  onChange={(e) => setSensorId(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      fetchData(sensorId, startDate, endDate);
                    }
                  }}
                  className="min-w-[180px] bg-gray-700 border-gray-600 text-gray-100"
                />
              </div>
            </div>
            <div className="flex flex-col">
              <label className="font-semibold mb-1 text-gray-200">Date Range</label>
              <div className="flex gap-2 items-center">
                <input
                  type="date"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="border rounded px-2 py-1 bg-gray-700 border-gray-600 text-gray-100"
                  disabled={!sensorId}
                />
                <span>to</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  className="border rounded px-2 py-1 bg-gray-700 border-gray-600 text-gray-100"
                  disabled={!sensorId}
                />
              </div>
              <span className="text-xs text-gray-400 mt-1">Select a custom date range or use a preset below.</span>
            </div>
            <div className="flex flex-col gap-1">
              <label className="font-semibold mb-1 text-gray-200">Presets</label>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPreset(1)}
                  className="border-gray-600 text-gray-200 hover:bg-gray-700"
                  disabled={!sensorId}
                >
                  Last 1 Day
                </Button>
                <Button size="sm" variant="outline" onClick={() => setPreset(7)} className="border-gray-600 text-gray-200 hover:bg-gray-700" disabled={!sensorId}>Last 7 Days</Button>
                <Button size="sm" variant="outline" onClick={() => setPreset(30)} className="border-gray-600 text-gray-200 hover:bg-gray-700" disabled={!sensorId}>Last 30 Days</Button>
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label className="font-semibold mb-1 invisible">Actions</label>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => { setStartDate(""); setEndDate(""); fetchData(); }}
                  className="border-gray-600 text-gray-200 hover:bg-gray-700"
                >
                  Clear
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Export & Analytics Controls */}
      <Card className="mb-4 bg-gray-800 border-gray-700 w-full">
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex gap-2 items-center">
              <h3 className="text-lg font-semibold text-gray-200">Data Export & Analytics</h3>
              <span className="text-sm text-gray-400">
                ({readings.length} displayed, {analyticsData.length > 0 ? analyticsData.length : readings.length} total for analysis)
              </span>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button
                onClick={() => setShowAnalytics(!showAnalytics)}
                className="bg-blue-600 hover:bg-blue-700 text-white"
                disabled={readings.length === 0}
              >
                📊 {showAnalytics ? 'Hide' : 'Show'} Analytics
              </Button>
              <Button
                onClick={exportToCSV}
                className="bg-green-600 hover:bg-green-700 text-white"
                disabled={readings.length === 0}
              >
                📄 Export CSV
              </Button>
              <Button
                onClick={exportToExcel}
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                disabled={readings.length === 0}
              >
                📊 Export Excel
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analytics Card */}
      {showAnalytics && analytics && (
        <Card className="mb-4 bg-gray-800 border-gray-700 w-full">
          <CardContent className="p-6">
            <h3 className="text-xl font-semibold mb-4 text-gray-200">📈 Analytics Summary</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
  <div className="p-4 rounded-lg bg-[354066] text-[#1e3a8a] dark:bg-[354066] dark:text-white transition-colors duration-300">
    <h4 className="font-semibold mb-2">Total Readings</h4>
    <p className="text-2xl font-bold">{analytics.totalReadings}</p>
  </div>
  <div className="p-4 rounded-lg bg-[354066] text-[#1e3a8a] dark:bg-[354066] dark:text-white transition-colors duration-300">
    <h4 className="font-semibold mb-2">Temperature Range</h4>
    <p className="text-sm">Min: <span className="font-bold">{analytics.temperature?.min?.toFixed(2) || 'N/A'}°C</span></p>
    <p className="text-sm">Max: <span className="font-bold">{analytics.temperature?.max?.toFixed(2) || 'N/A'}°C</span></p>
    <p className="text-sm">Avg: <span className="font-bold">{analytics.temperature?.avg?.toFixed(2) || 'N/A'}°C</span></p>
  </div>
  <div className="p-4 rounded-lg bg-[354066] text-[#1e3a8a] dark:bg-[354066] dark:text-white transition-colors duration-300">
    <h4 className="font-semibold mb-2">Humidity Range</h4>
    <p className="text-sm">Min: <span className="font-bold">{analytics.humidity?.min?.toFixed(2) || 'N/A'}%</span></p>
    <p className="text-sm">Max: <span className="font-bold">{analytics.humidity?.max?.toFixed(2) || 'N/A'}%</span></p>
    <p className="text-sm">Avg: <span className="font-bold">{analytics.humidity?.avg?.toFixed(2) || 'N/A'}%</span></p>
  </div>
  <div className="p-4 rounded-lg bg-[354066] text-[#1e3a8a] dark:bg-[354066] dark:text-white transition-colors duration-300">
    <h4 className="font-semibold mb-2">Date Range</h4>
    <p className="text-xs">From: <span className="font-bold">{analytics.dateRange.start}</span></p>
    <p className="text-xs">To: <span className="font-bold">{analytics.dateRange.end}</span></p>
  </div>
</div>

          </CardContent>
        </Card>
      )}

      {error && (
        <div className="bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded">
          Error: {error}
        </div>
      )}

      {/* Chart Card */}
      <Card className="mb-4 bg-grey-800 border-gray-700 w-full">
        <CardContent className="p-4">
          <h2 className="text-xl font-semibold mb-2 text-grey-200">Sensor Data Chart</h2>
          {loading ? (
            <div className="flex justify-center items-center h-40">
              <svg className="animate-spin h-8 w-8 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
              </svg>
            </div>
          ) : readings.length === 0 ? (
            <div className="text-center text-gray-400">No data available</div>
          ) : (
            <div className="p-2 bg-gray-900 rounded"><Line data={data} options={options} /></div>
          )}
        </CardContent>
      </Card>

      {/* Data Table Card */}
      <Card className="bg-gray-800 border-gray-700 w-full">
      <CardContent className="overflow-x-auto pt-2 pb-4">
        <h2 className="text-xl font-semibold text-gray-100 mb-1">Raw Data Table</h2>
        <table className="w-full text-sm border border-gray-700 rounded overflow-hidden">
  <thead>
    <tr>
      <th className="text-left px-4 py-2">Timestamp</th>
      <th className="text-left px-4 py-2">Temp (°C)</th>
      <th className="text-left px-4 py-2">Humidity (%)</th>
    </tr>
  </thead>
  <tbody>
  {readings.map((row, idx) => (
    <tr
      key={idx}
      className={`${
        idx % 2 === 0 ? 'bg-gray-800' : 'bg-gray-900'
      } hover:bg-gray-600 text-gray-100`}
    >
      <td className="px-4 py-2">{row.timestamp}</td>
      <td className="px-4 py-2">{row.readings?.temperature?.value?.toFixed(2) || 'N/A'}</td>
      <td className="px-4 py-2">{row.readings?.humidity?.value?.toFixed(2) || 'N/A'}</td>
    </tr>
  ))}
</tbody>

          </table>
        </CardContent>
      </Card>
    </div>
  );
}
    