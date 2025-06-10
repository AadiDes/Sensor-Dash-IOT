# IoT Dashboard Backend

## Features
- MQTT to MongoDB pipeline with retry logic and data validation
- Flask API with pagination and logging
- Docker support for easy deployment

## Running with Docker
```
docker build -t iot-backend .
docker run -d -p 5000:5000 --env-file .env iot-backend
```

## API Pagination
- Use `?page=1&page_size=50` on `/api/readings` and `/api/readings/<sensor_id>`

## Logging
- Logs are written to console and log files with structured messages

## Data Validation
- Sensor readings are validated and sanitized before being stored 