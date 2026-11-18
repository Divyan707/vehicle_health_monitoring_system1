# 🚗 Vehicle Health Monitoring System Using CAN

## 📌 Project Overview

The **Vehicle Health Monitoring System Using CAN** is a real-time vehicle monitoring project designed to monitor important vehicle parameters and identify potential faults.

The system uses an STM32 microcontroller to collect vehicle sensor data and communicate through the Controller Area Network (CAN) protocol. The collected information is transferred using MQTT and processed using Python. A Streamlit-based dashboard displays vehicle health information in an easy-to-understand format.

The main objective is to improve vehicle safety, reliability, and monitoring through real-time data analysis.

## 🎯 Objectives

- Monitor vehicle parameters in real time.
- Establish communication using the CAN protocol.
- Collect and process vehicle data using STM32.
- Transfer data using the MQTT protocol.
- Detect abnormal vehicle conditions.
- Display vehicle information through an interactive dashboard.
- Support deployment using Docker.

## ⚙️ Technologies Used

| Technology | Purpose |
|---|---|
| STM32 | Microcontroller |
| CAN Protocol | Vehicle communication |
| CAN Transceiver | CAN bus interface |
| Python | Backend processing |
| Python-CAN | CAN communication interface |
| MQTT | Message communication |
| Mosquitto | MQTT Broker |
| Streamlit | Web Dashboard |
| Pandas | Data processing |
| SQLite | Data storage |
| Docker | Application deployment |

## 🏗️ System Architecture

The project follows the following data flow:

```text
      Vehicle Sensors / ECU
               |
               v
          STM32 Board
               |
               v
           CAN Bus
               |
               v
       Python CAN Gateway
               |
               v
          MQTT Broker
          (Mosquitto)
               |
               v
       Python MQTT Subscriber
               |
               v
          SQLite Database
               |
               v
       Streamlit Dashboard
               |
               v
       Real-Time Monitoring
```

## ✨ Key Features

1. **Real-Time Monitoring:** Collects and displays vehicle information.
2. **CAN Communication:** Uses CAN protocol for communication between vehicle components.
3. **MQTT Integration:** Transfers vehicle data through an MQTT broker.
4. **Fault Detection:** Identifies abnormal vehicle parameter values.
5. **Interactive Dashboard:** Displays vehicle health information using Streamlit.
6. **Database Storage:** Stores collected vehicle data using SQLite.
7. **Docker Support:** Provides containerized application deployment.

## 📊 Parameters Monitored

The system is designed to monitor the following vehicle parameters:

- Engine Temperature
- Battery Voltage
- Vehicle Speed

These parameters help identify abnormal operating conditions and provide useful information about vehicle health.

## 📁 Project Structure

```text
Vehicle-Health-Monitoring-System/
│
├── app.py
├── common.py
├── gateway.py
│
├── requirements.txt
│
├── Dockerfile
├── docker-compose.yml
├── mosquitto.conf
│
├── vehicle_health.db
│
└── static/
```

## 💻 Installation and Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
```

```bash
cd Vehicle-Health-Monitoring-System
```

### 2. Create a Virtual Environment

```bash
py -3.14 -m venv venv
```

### 3. Activate Virtual Environment

For Windows:

```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
py -m pip install -r requirements.txt
```

### 5. Start MQTT Broker

Make sure the Mosquitto MQTT broker is running and configured correctly.

Default MQTT port:

```text
1883
```

MQTT topic:

```text
vehicle/health
```

### 6. Run the Application

Start the Python gateway and MQTT communication components as configured in the project.

Launch the Streamlit dashboard:

```bash
streamlit run app.py
```

The dashboard can generally be accessed at:

```text
http://localhost:8501
```

## 🐳 Docker Deployment

The project includes Docker support for easier application deployment.

Build and start the containers:

```bash
docker compose up --build
```

To stop the containers:

```bash
docker compose down
```

Docker helps package the application and its software dependencies. Access to physical CAN hardware may require additional host configuration.

## 🔍 Working Principle

1. Vehicle sensors collect information about different vehicle parameters.
2. STM32 processes the collected sensor information.
3. CAN communication transfers the data.
4. The Python gateway receives and processes the CAN messages.
5. MQTT transfers the processed information to the subscriber.
6. The received data is stored in the SQLite database.
7. Streamlit displays the information on the dashboard.

## 🚀 Future Scope

- Integration with GPS for vehicle location tracking.
- Cloud-based vehicle monitoring.
- Mobile application for remote monitoring.
- Advanced fault prediction using machine learning.
- Improved vehicle diagnostics and maintenance alerts.
- Support for additional vehicle sensors.

## 👨‍💻 Project Information

**Project Name:** Vehicle Health Monitoring System Using CAN

**Domain:** Embedded Systems and IoT

**Hardware:** STM32 Microcontroller, CAN Interface and Vehicle Sensors

**Software:** Python, MQTT, Streamlit and Docker

## 📌 Conclusion

The Vehicle Health Monitoring System provides an approach to monitoring vehicle parameters using embedded systems and communication technologies. By integrating STM32, CAN, MQTT, Python, and Streamlit, the project provides a platform for collecting, processing, storing, and displaying vehicle health information in real time.

The system can be further developed into a more advanced vehicle diagnostic and predictive maintenance solution.
