# utils_parser.py

import json
import logging

logger = logging.getLogger(__name__)

def parse_sensor_data(message: str) -> dict | None:
    """Parse sensor payload into flat readings with unit strings."""
    try:
        if not (message.startswith("{") and message.endswith("}")):
            return None

        data = json.loads(message)
        normalized = {k.lower().strip(): v for k, v in data.items()}
        readings = {}

        # Temperature keys: "temp", "t", "temperature"
        for key in ["temp", "t", "temperature"]:
            if key in normalized:
                val = normalized[key]
                if isinstance(val, str) and " " in val:
                    val = val.split()[0]
                readings["temperature"] = f"{float(val):.2f} °C"
                break  # Stop after first match

        # Humidity keys: "hum", "h", "humidity"
        for key in ["hum", "h", "humidity"]:
            if key in normalized:
                val = normalized[key]
                if isinstance(val, str) and " " in val:
                    val = val.split()[0]
                readings["humidity"] = f"{float(val):.2f} %"
                break

        # BPM
        if "bpm" in normalized:
            readings["bpm"] = f"{float(normalized['bpm']):.2f} bpm"

        # SPO2
        if "spo2" in normalized:
            readings["spo2"] = f"{float(normalized['spo2']):.2f} %"

        # Accelerometer (flat or nested in 'vibration')
        for axis in ["x", "y", "z"]:
            if axis in normalized:
                readings[axis] = f"{float(normalized[axis]):.2f} g"
            elif "vibration" in normalized:
                vib = normalized["vibration"]
                if isinstance(vib, dict) and axis in vib:
                    readings[axis] = f"{float(vib[axis]):.2f} g"

        return readings if readings else None

    except Exception as e:
        logger.warning(f"parse_sensor_data failed: {e}")
        return None
