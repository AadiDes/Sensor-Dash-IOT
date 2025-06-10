import React, { useEffect, useState } from "react";
import { Card, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Line } from "react-chartjs-2";
import Chart from "chart.js/auto";

export default function IOTDashboard() {
  const [readings, setReadings] = useState([]);
  const [sensorId, setSensorId] = useState("device1");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  
  // Helper to set preset ranges
  const setPreset = (days) => {
    // Set end date to tomorrow to include today's readings
    const end = new Date();
    end.setDate(end.getDate() + 1);
    const start = new Date();
    start.setDate(end.getDate() - days);
    const startStr = start.toISOString().slice(0, 10);
    const endStr = end.toISOString().slice(0, 10);
    setStartDate(startStr);
    setEndDate(endStr);
    fetchData(sensorId, startStr, endStr);
  };

  const fetchData = async (id = sensorId, start = startDate, end = endDate) => {
    setLoading(true);
    setError(null);
    try {
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
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
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
    <div className="w-full min-h-screen h-full p-6 grid gap-8 bg-gray-900 text-gray-100">
      <h1 className="text-3xl font-bold flex items-center gap-2 mb-2">🌡️ IoT Sensor Dashboard</h1>
      <Card className="mb-4 bg-gray-800 border-gray-700 w-full">
        <CardContent className="p-6 flex flex-col gap-4">
          <div className="flex flex-col md:flex-row md:items-end gap-4 flex-wrap">
            <div className="flex flex-col">
              <label className="font-semibold mb-1 text-gray-200">Sensor ID</label>
              <form
                onSubmit={e => {
                  e.preventDefault();
                  fetchData(sensorId, startDate, endDate);
                }}
              >
                <Input
                  placeholder="Enter Sensor ID"
                  value={sensorId}
                  onChange={(e) => setSensorId(e.target.value)}
                  className="min-w-[180px] bg-gray-700 border-gray-600 text-gray-100"
                />
              </form>
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

      {error && (
        <div className="bg-red-900 border border-red-700 text-red-200 px-4 py-3 rounded">
          Error: {error}
        </div>
      )}

      <Card className="mb-4 bg-gray-800 border-gray-700 w-full">
        <CardContent className="p-4">
          <h2 className="text-xl font-semibold mb-2 text-gray-200">Sensor Data Chart</h2>
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

      <Card className="bg-gray-800 border-gray-700 w-full">
        <CardContent className="overflow-x-auto">
          <h2 className="text-xl font-semibold mb-2 text-gray-100">Raw Data Table</h2>
          <table className="w-full text-sm border border-gray-700 rounded overflow-hidden">
            <thead>
              <tr>
                <th className="text-left text-gray-100 bg-gray-700 px-3 py-2">Timestamp</th>
                <th className="text-gray-100 bg-gray-700 px-3 py-2">Temp (°C)</th>
                <th className="text-gray-100 bg-gray-700 px-3 py-2">Humidity (%)</th>
              </tr>
            </thead>
            <tbody>
              {readings.map((row, idx) => (
                <tr key={idx} className={
                  `text-gray-100 ${idx % 2 === 0 ? 'bg-gray-800' : 'bg-gray-900'} hover:bg-gray-700`
                }>
                  <td className="px-3 py-2">{row.timestamp}</td>
                  <td className="px-3 py-2">{row.readings?.temperature?.value?.toFixed(2) || 'N/A'}</td>
                  <td className="px-3 py-2">{row.readings?.humidity?.value?.toFixed(2) || 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
