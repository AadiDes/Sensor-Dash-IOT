# 📘 Cloud-Based IoT Data Analytics Dashboard

## 📸 Live Screenshots

<table align="center">
  <tr>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/c306ad57-5ab3-4652-ade8-ed34e609e4bb" alt="Screenshot 1" width="350"/>
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/476e2d34-f7e6-4818-9271-463b1481c539" alt="Screenshot 2" width="350"/>
    </td>
  </tr>
  <tr>
    <td colspan="2" align="center">
      <img src="https://github.com/user-attachments/assets/1dc116a2-973b-4544-b339-f1e4a02dc272" alt="Screenshot 3" width="350"/>
    </td>
  </tr>
</table>

### Document Number

SCD/DOC/IOT/CSE-PS1/20250619-01

### Document Version

1.0

### Document Type

Techno-Functional Report

### Document Title

Cloud-Based IoT Data Analytics Dashboard

### Document Author

Aadi Deshmukh

---

## 📜 Revision History

| Date       | Version | Description                         | Author        |
| ---------- | ------- | ----------------------------------- | ------------- |
| 19/06/2025 | 1.0     | Initial project documentation draft | Aadi Deshmukh |

---

## 📌 Disclaimer

This project was developed during the PS-1 internship at **Shalaka Connected Devices LLP** by Aadi Deshmukh (B.E. CSE, BITS Pilani Goa Campus) for educational and research purposes. The software and design patterns used herein represent a simulated IoT data analytics platform and are not directly linked to any commercial or production-grade IoT hardware.

This document may be reused and modified with proper attribution. All technologies, protocols, and software tools used are open-source or community-supported unless otherwise noted.

---

## 📖 Table of Contents

1. Introduction
2. Objective
3. System Overview
4. Architecture Diagram
5. Modules

   * Sensor Simulation & MQTT Pipeline
   * MongoDB Data Storage
   * RESTful Flask API
   * React Dashboard UI
6. Key Features
7. Future Scope
8. Deployment Notes
9. Contacts

---

## 🔍 1. Introduction

With the increasing adoption of IoT in industrial and smart environments, the need for robust, scalable, and intuitive dashboards is paramount. This project demonstrates a **full-stack implementation** of an IoT pipeline where sensor data is simulated, streamed, stored in the cloud, and visualized in real-time.

---

## 🎯 2. Objective

* To simulate multiple virtual sensors publishing to an MQTT broker.
* To receive, validate, and store sensor data in a **cloud MongoDB database**.
* To expose the sensor data using a **Flask REST API**.
* To visualize and analyze the data on a **React-based dashboard**.

---

## 🧩 3. System Overview

This project is a four-layered system:

1. **Sensor Layer** (Python simulation using `paho-mqtt`)
2. **Ingestion Layer** (`mqtt_to_mongo.py`, `mqtt_manager.py`)
3. **Database Layer** (MongoDB Atlas Cloud with validation/indexing)
4. **Visualization Layer** (React + Chart.js UI)

---

## 🗺️ 4. Architecture Diagram

```plaintext
[Sensors Simulated]
        |
        | MQTT Publish
        v
[broker.emqx.io MQTT Broker]
        |
        | MQTT Subscribe
        v
[Python MQTT Handler (mqtt_manager.py)]
        |
        | Validated Document
        v
[MongoDB Atlas - iot_database.sensor_readings]
        |
        | HTTP GET /api/readings/<sensor_id>
        v
[Flask API (flask_api.py)]
        |
        | JSON Response
        v
[React Dashboard UI (IOTDashboard.jsx)]
```

---

## 🧱 5. Modules

### ✅ Sensor Simulation

* Simulates temperature, humidity, BPM, SPO2, accelerometer data.
* Publishes JSON payloads every 10–30 seconds.
* Uses MQTT protocol (QoS 1) via `broker.emqx.io`.

### ✅ MQTT Subscriber + Parser (`mqtt_manager.py`)

* Subscribes to `TEMP/SUB/#` topics.
* Parses raw payloads into structured sensor data.
* Validates keys and sensor\_id from topic.

### ✅ MongoDB Data Store

* Uses `iot_database.sensor_readings` collection.
* Each document has:

  ```json
  {
    "sensor_id": "sensor_01",
    "readings": {
      "temperature": "29.42 °C",
      "humidity": "72.94 %"
    },
    "timestamp": "2025-06-17T12:53:00Z",
    "topic": "TEMP/SUB/sensor_01",
    "raw": "{...}"
  }
  ```
* Indexes:

  * `sensor_id + timestamp` for fast time-range queries.

### ✅ Flask REST API

* `/api/sensors` → all available sensors.
* `/api/readings/<sensor_id>?start=...&end=...&limit=...`
* `/api/readings/latest/<sensor_id>` → latest entry.

### ✅ React Dashboard UI

* Sensor selector, time filter, and data table.
* Real-time chart with temperature, humidity, BPM, SPO2, and XYZ axis data.
* Summary analytics like min/max/avg for selected time period.
* Responsive layout with Tailwind CSS and Chart.js.

---

## ✨ 6. Key Features

* 🌐 **Hybrid Data Filter**: Dropdown-based pagination and full-time range querying.
* ⚡ **Real-Time MQTT**: Handles multiple sensor streams asynchronously.
* ☁️ **MongoDB Cloud Sync**: Optimized schema and index-based storage.
* 📊 **Charts & Analytics**: Auto-detects sensor fields and generates per-field insights.
* 🔄 **Dynamic Parser**: Automatically parses known fields like temperature, humidity, bpm, x, y, z.
* 🧠 **Validation**: Skips malformed or incomplete sensor data.

---

## 🚀 7. Future Scope

* Add authentication layer (JWT) for protected APIs.
* Implement role-based access for sensor management.
* Migrate frontend to **Flutter** with minimal backend changes.
* Integrate **WebSocket** for true real-time updates.
* Extend dashboard for industrial clients (CSV export, alerts).

---

## ⚙️ 8. Deployment Notes

* **Python Version**: 3.11 or later
* **Frontend**: React 18 with Vite
* **Cloud DB**: MongoDB Atlas
* **Broker**: `broker.emqx.io` (public test broker)
* **Hosting Options**:

  * Backend (Flask): [Render](https://render.com)
  * Frontend (React): [Netlify](https://netlify.com)

---

9. Contact

**Shalaka Connected Devices LLP**
D-101, Silver Crest, Balwantpuram, Kothrud, Pune – 411038
📧 [info@shalaka.com]

For project-related queries:
👨‍💻 Aadi Deshmukh – [aadi.deshmukh@example.com](aadi14des@gmail.com)

