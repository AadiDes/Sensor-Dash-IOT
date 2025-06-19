import React, { useEffect, useState, useRef, useCallback } from "react";
import { Card, CardContent } from "./ui/card";
import { Button } from "./ui/button"; 
import { Line } from "react-chartjs-2";
import * as XLSX from "xlsx";
import useDarkMode from "./hooks/useDarkMode";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LineController,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(
  LineElement,
  PointElement,
  LineController,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend
);


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
  const [sensorOptions, setSensorOptions] = useState([]);
  const [lastFetchTime, setLastFetchTime] = useState(null);

  // MQTT client ref to persist across renders
  const mqttClient = useRef(null);
  const pollingInterval = useRef(null);

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

  const handleResetDashboard = () => {
    setSensorId("device1");
    setStartDate("");
    setEndDate("");
    setReadings([]);
    setAnalytics(null);
    setAnalyticsData([]);
    setShowAnalytics(false);
    setLastFetchTime(null);
  };

  const extractTemperature = (reading) => {
    try {
      const temp = reading?.readings?.temperature;
  
      if (typeof temp === "string") return temp; // new format
      if (typeof temp === "number") return `${temp.toFixed(2)} °C`;
      if (temp?.value && typeof temp.value === "number") return `${temp.value.toFixed(2)} °C`;
  
      if (typeof reading?.temperature === "number") return `${reading.temperature.toFixed(2)} °C`;
      if (reading?.temperature?.value && typeof reading.temperature.value === "number")
        return `${reading.temperature.value.toFixed(2)} °C`;
  
      return "N/A";
    } catch (e) {
      console.warn("Error extracting temperature:", e);
      return "N/A";
    }
  };
  
  const extractHumidity = (reading) => {
    try {
      const hum = reading?.readings?.humidity;
  
      if (typeof hum === "string") return hum; // new format
      if (typeof hum === "number") return `${hum.toFixed(2)} %`;
      if (hum?.value && typeof hum.value === "number") return `${hum.value.toFixed(2)} %`;
  
      if (typeof reading?.humidity === "number") return `${reading.humidity.toFixed(2)} %`;
      if (reading?.humidity?.value && typeof reading.humidity.value === "number")
        return `${reading.humidity.value.toFixed(2)} %`;
  
      return "N/A";
    } catch (e) {
      console.warn("Error extracting humidity:", e);
      return "N/A";
    }
  };
  
  // Calculate analytics from readings
  // ✅ Updated: parse "29.08 °C" and handle all valid string/unit formats
const calculateAnalytics = (data) => {
  if (!data || data.length === 0) return null;

  const sensorKeys = ["temperature", "humidity", "bpm", "spo2", "x", "y", "z"];
  const analyticsResult = {};

  const extractNumeric = (val) => {
    if (typeof val === "number") return val;
    if (typeof val === "string") {
      const num = parseFloat(val);
      return isNaN(num) ? null : num;
    }
    if (val?.value && typeof val.value === "number") return val.value;
    return null;
  };

  sensorKeys.forEach((key) => {
    const values = data
      .map((r) => extractNumeric(r.readings?.[key]))
      .filter((v) => typeof v === "number");

    if (values.length > 0) {
      analyticsResult[key] = {
        min: Math.min(...values),
        max: Math.max(...values),
        avg: values.reduce((a, b) => a + b, 0) / values.length,
        count: values.length
      };
    }
  });

  return {
    ...analyticsResult,
    totalReadings: data.length,
    dateRange: {
      start: data[data.length - 1]?.timestamp,
      end: data[0]?.timestamp
    }
  };
};

  
  // Helper: Wrapped fetchAnalyticsData for stable reference
// ✅ Wrap without readings to avoid infinite re-renders
const fetchAnalyticsData = useCallback(
  async (id = sensorId, start = startDate, end = endDate) => {
    try {
      let url = `http://localhost:5000/api/readings/${id}?page_size=10000`;
      const params = [];
      if (start) params.push(`start=${start}`);
      if (end) params.push(`end=${end}`);
      if (params.length) url += "&" + params.join("&");

      const response = await fetch(url);
      const allData = await response.json();

      const validAnalyticsData = Array.isArray(allData)
        ? allData.filter((r) => r.timestamp)
        : [];

      setAnalyticsData(validAnalyticsData);
      const analyticsResults = calculateAnalytics(validAnalyticsData);
      setAnalytics(analyticsResults);
    } catch (err) {
      console.error("Failed to fetch analytics data:", err);
      setAnalyticsData([]);
      setAnalytics(null);
    }
  },
  [sensorId, startDate, endDate]
);


const fetchData = useCallback(
  async (id = sensorId, start = startDate, end = endDate) => {
    if (!id) return;

    setLoading(true);
    setError(null);

    try {
      let url = `http://localhost:5000/api/readings/${id}`;
      const params = [];
      if (start) params.push(`start=${start}`);
      if (end) params.push(`end=${end}`);
      if (params.length > 0) url += "?" + params.join("&");

      console.log("📡 Fetching from URL:", url);

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }

      const data = await response.json();
      console.log("📥 Raw API response:", data);

      const validReadings = Array.isArray(data)
        ? data.filter((reading) => {
            const temp = extractTemperature(reading);
            const hum = extractHumidity(reading);
            const hasValidData = temp !== null || hum !== null;

            const hasValidTimestamp =
              typeof reading.timestamp === "string" || reading.timestamp instanceof Date;

            if (!hasValidData || !hasValidTimestamp) {
              console.warn("⚠️ Filtering out invalid reading:", reading);
              return false;
            }

            return true;
          })
        : [];

      console.log("✅ Valid readings after filtering:", validReadings);

      setReadings(validReadings);
      setLastFetchTime(new Date());

      // ✅ Fetch analytics after readings update
      if (typeof fetchAnalyticsData === "function") {
        await fetchAnalyticsData(id, start, end);
      }
    } catch (err) {
      console.error("❌ Fetch error:", err);
      setError(err.message || "Unknown error occurred");
    } finally {
      setLoading(false);
    }
  },
  [sensorId, startDate, endDate] // ✅ Removed fetchAnalyticsData to avoid render loop
);
  
  const fetchSensorOptions = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:5000/api/sensors");
      const data = await res.json();
      console.log("Sensor options:", data);
      setSensorOptions(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error("Failed to fetch sensor list", e);
      setSensorOptions([]);
    }
  }, []);

  // Polling function to check for new data
  const startPolling = () => {
    if (pollingInterval.current) {
      clearInterval(pollingInterval.current);
    }
    
    pollingInterval.current = setInterval(async () => {
      if (sensorId) {
        try {
          // Check if there's new data by comparing timestamps
          const url = `http://localhost:5000/api/readings/${sensorId}?page_size=1`;
          const response = await fetch(url);
          if (response.ok) {
            const latestData = await response.json();
            if (latestData.length > 0) {
              const latestTimestamp = new Date(latestData[0].timestamp);
              if (!lastFetchTime || latestTimestamp > lastFetchTime) {
                console.log("New data detected, refreshing dashboard");
                fetchData(sensorId, startDate, endDate);
              }
            }
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      }
    }, 5000); // Poll every 5 seconds
  };

  const stopPolling = () => {
    if (pollingInterval.current) {
      clearInterval(pollingInterval.current);
      pollingInterval.current = null;
    }
  };

  // Export functions
  const exportToCSV = () => {
    const dataToExport = analyticsData.length > 0 ? analyticsData : readings;
    if (dataToExport.length === 0) {
      alert("No data to export");
      return;
    }
  
    const csvData = dataToExport.map((reading) => {
      return {
        Timestamp: reading.timestamp,
        "Sensor ID": reading.sensor_id || sensorId,
        "Temperature": extractTemperature(reading),
        "Humidity": extractHumidity(reading),
      };
    });
  
    const csvContent = [
      Object.keys(csvData[0]).join(","),
      ...csvData.map((row) => Object.values(row).join(",")),
    ].join("\n");
  
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `sensor_data_${sensorId}_${new Date().toISOString().split("T")[0]}.csv`);
    link.style.visibility = "hidden";
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
  
    const excelData = dataToExport.map((reading) => {
      return {
        Timestamp: reading.timestamp,
        "Sensor ID": reading.sensor_id || sensorId,
        "Temperature": extractTemperature(reading),
        "Humidity": extractHumidity(reading),
      };
    });
  
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(excelData);
    XLSX.utils.book_append_sheet(wb, ws, "Sensor Data");
  
    // Optional: Analytics Sheet
    if (analytics) {
      const sensorStats = Object.entries(analytics)
        .filter(([key]) => key !== "totalReadings" && key !== "dateRange");
  
      const analyticsSheetData = [
        ["Metric", ...sensorStats.map(([key]) => key.toUpperCase())],
        ["Minimum", ...sensorStats.map(([_, stats]) => stats.min?.toFixed(2) || "N/A")],
        ["Maximum", ...sensorStats.map(([_, stats]) => stats.max?.toFixed(2) || "N/A")],
        ["Average", ...sensorStats.map(([_, stats]) => stats.avg?.toFixed(2) || "N/A")],
        ["Count", ...sensorStats.map(([_, stats]) => stats.count || "N/A")],
        ["", "", ""],
        ["Total Readings", analytics.totalReadings, ""],
        ["Date Range", `${analytics.dateRange.start} to ${analytics.dateRange.end}`, ""],
        ["", "", ""],
        ["Period Selected", startDate && endDate ? `${startDate} to ${endDate}` : "All Data", ""],
      ];
  
      const analyticsWs = XLSX.utils.aoa_to_sheet(analyticsSheetData);
      XLSX.utils.book_append_sheet(wb, analyticsWs, "Analytics");
    }
  
    XLSX.writeFile(wb, `sensor_data_${sensorId}_${new Date().toISOString().split("T")[0]}.xlsx`);
  };
  

  // Effect hooks
 // 1️⃣ Load sensor list once on mount
 useEffect(() => {
  fetchSensorOptions(); // Only once on mount
}, []);

// 2️⃣ Fetch sensor data when sensorId or date range changes
useEffect(() => {
  if (sensorId && startDate && endDate) {
    fetchData(sensorId, startDate, endDate);
  }
}, [sensorId, startDate, endDate, fetchData]); // ✅ now correct


// 3️⃣ Clean up MQTT and polling when component unmounts
useEffect(() => {
  const client = mqttClient.current;

  return () => {
    stopPolling();
    if (client) client.end();
  };
}, []);

const sensorKeys = ["temperature", "humidity", "bpm", "spo2", "x", "y", "z"];

const datasets = sensorKeys.map((key, i) => {
  const colorList = [
    "rgb(75,192,192)",
    "rgb(255,99,132)",
    "rgb(255,206,86)",
    "rgb(153,102,255)",
    "rgb(54,162,235)",
    "rgb(255,159,64)",
    "rgb(201,203,207)"
  ];
  const color = colorList[i % colorList.length];

  return {
    label: key.toUpperCase(),
    data: readings.map((r) => {
      const raw = r.readings?.[key];
      if (typeof raw === "number") return raw;
      if (typeof raw === "string") {
        const parsed = parseFloat(raw); // handles "28.62 °C"
        return isNaN(parsed) ? null : parsed;
      }
      if (typeof raw === "object" && typeof raw.value === "number") {
        return raw.value;
      }
      return null;
    }).reverse(),
    fill: false,
    borderColor: color,
    backgroundColor: color,
    tension: 0.1
  };
});
  
const filteredDatasets = datasets.filter(ds =>
  ds.data.some(val => typeof val === "number")
);



// Prepare chart labels and temp/humidity data
const labels = readings.map((r) => r.timestamp);
const tempData = readings.map((r) => {
  const val = r.readings?.temperature;
  return typeof val === "string" ? parseFloat(val) || null : null;
});
const humidityData = readings.map((r) => {
  const val = r.readings?.humidity;
  return typeof val === "string" ? parseFloat(val) || null : null;
});

const data = {
  labels: labels.slice().reverse(),
  datasets: filteredDatasets
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
      beginAtZero: false, // allow full dynamic range
      min: 0,              // optional: prevent negative
      suggestedMax: 100,   // upper limit guess (used for autoscale)
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
        .hover:bg-gray-700:hover {
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
  <select
  value={sensorId}
  onChange={(e) => setSensorId(e.target.value)}
  className="min-w-[180px] bg-[#e5e7eb] text-[#1e3a8a] border border-gray-500 rounded px-2 py-1
             dark:bg-gray-800 dark:text-gray-100 dark:border-gray-600
             focus:outline-none focus:ring-2 focus:ring-blue-500"
>
  {sensorOptions.length === 0 ? (
    <option value="" disabled>Loading...</option>
  ) : (
    sensorOptions.map((id) => (
      <option
        key={id}
        value={id}
        className="text-[#1e3a8a] dark:text-white"
      >
        {id}
      </option>
    ))
  )}
</select>

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
                  onClick={handleResetDashboard}
                  className="border-gray-600 text-gray-200 hover:bg-gray-700"
                >
                  Reset Dashboard
                </Button>
                <Button
                  variant="outline"
                  onClick={() => fetchData(sensorId, startDate, endDate, true)}
                  className="border-gray-600 text-gray-200 hover:bg-gray-700"
                  disabled={!sensorId || loading}
                >
                  {loading ? "Loading..." : "Refresh Data"}
                </Button>
              </div>
            </div>
          </div>
          {lastFetchTime && (
            <div className="text-sm text-gray-400">
              Last updated: {lastFetchTime.toLocaleString()}
            </div>
          )}
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
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-4">
  {Object.entries(analytics).map(([key, stats]) => {
    if (key === "totalReadings" || key === "dateRange") return null;
    return (
      <div key={key} className="p-4 rounded-lg bg-[#354066] text-[#1e3a8a] dark:bg-[#354066] dark:text-white transition-colors duration-300">
        <h4 className="font-semibold mb-2 capitalize">{key} Stats</h4>
        <p className="text-sm">Min: <span className="font-bold">{stats.min?.toFixed(2) || "N/A"}</span></p>
        <p className="text-sm">Max: <span className="font-bold">{stats.max?.toFixed(2) || "N/A"}</span></p>
        <p className="text-sm">Avg: <span className="font-bold">{stats.avg?.toFixed(2) || "N/A"}</span></p>
        <p className="text-sm">Count: <span className="font-bold">{stats.count}</span></p>
      </div>
    );
  })}

  {/* Date Range + Total Readings Card */}
  <div className="p-4 rounded-lg bg-[#354066] text-[#1e3a8a] dark:bg-[#354066] dark:text-white transition-colors duration-300">
    <h4 className="font-semibold mb-2">General Info</h4>
    <p className="text-sm">Readings: <span className="font-bold">{analytics.totalReadings}</span></p>
    <p className="text-sm">From: <span className="font-bold">{analytics.dateRange.start}</span></p>
    <p className="text-sm">To: <span className="font-bold">{analytics.dateRange.end}</span></p>
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
            <div className="text-center text-yellow-400 font-semibold text-sm">
            No data found in the selected date range or for this sensor.
            </div>

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
    {["temperature", "humidity", "bpm", "spo2", "x", "y", "z"].map((key) => (
      readings.some(r => r.readings?.[key]) && (
        <th key={key} className="text-left px-4 py-2">
          {key.charAt(0).toUpperCase() + key.slice(1)}{" "}
          {["x", "y", "z"].includes(key)
            ? "(g)"
            : key === "spo2"
            ? "(%)"
            : key === "bpm"
            ? "(bpm)"
            : key === "humidity"
            ? "(%)"
            : " (°C)"}
        </th>
      )
    ))}
  </tr>
</thead>


<tbody>
  {readings.map((row, idx) => (
    <tr
      key={idx}
      className={`${
        idx % 2 === 0 ? "bg-gray-800" : "bg-gray-900"
      } hover:bg-gray-600 text-gray-100`}
    >
      <td className="px-4 py-2">{row.timestamp}</td>
      {["temperature", "humidity", "bpm", "spo2", "x", "y", "z"].map((key) => {
        const reading = row.readings?.[key];
        return (
          <td key={key} className="px-4 py-2">
            {typeof reading === "string"
              ? reading
              : typeof reading?.value === "number"
              ? `${reading.value.toFixed(2)} ${reading.unit || ""}`
              : "N/A"}
          </td>
        );
      })}
    </tr>
  ))}
</tbody>




          </table>
        </CardContent>
      </Card>
    </div>
  );
}
    