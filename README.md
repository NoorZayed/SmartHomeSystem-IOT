# Smart Home IoT System - Web Dashboard

A comprehensive Smart Home IoT monitoring system with real-time web dashboard and advanced analytics.

## 🚀 Quick Start (30 seconds!)

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Start dashboard**: `python web_dashboard.py`
3. **Open browser**: Go to `http://localhost:5001`
4. **Start simulation**: Click the "Start Simulation" button in the dashboard

**Alternative**: Run `python start_dashboard.py` for automated setup!

## 🌟 Features

### 🌐 Web Dashboard (NEW!)
- **Modern Web Interface**: Responsive, mobile-friendly design
- **Real-time Monitoring**: Live sensor data streaming via WebSockets
- **Interactive Charts**: Dynamic visualization for each sensor type
- **Power Analytics**: Comprehensive power consumption analysis
- **Alert System**: Real-time notifications for abnormal conditions
- **Control Panel**: Start/stop simulation and adjust optimization parameters
- **Historical Analysis**: Detailed charts and trend analysis
- **Multi-device Access**: Access from any browser on any device

### 📈 Original Simulation
- **Scientific Visualization**: IEEE-compliant matplotlib plots
- **Energy Optimization**: Real-time duty cycling and data aggregation
- **Statistical Analysis**: Comprehensive correlation and trend analysis
- **Email Alerts**: Automated notifications for critical conditions
- **Export Capabilities**: Save reports and charts

## 🚀 Quick Start

### Option 1: Use the Launcher (Recommended)
```bash
python launcher.py
```
Then select:
- **Option 1**: Web Dashboard (modern web interface)
- **Option 2**: Original Simulation (matplotlib-based)

### Option 2: Direct Launch

#### Web Dashboard
```bash
python web_dashboard.py
```
Then open http://localhost:5000 in your browser

#### Original Simulation
```bash
python main.py
```

## 📦 Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Required Packages**:
   - `numpy` - Numerical computations
   - `matplotlib` - Scientific plotting
   - `paho-mqtt` - MQTT communication
   - `flask` - Web framework
   - `flask-socketio` - Real-time communication

## 🖥️ Web Dashboard Usage

### Starting the System
1. Run `python launcher.py` or `python web_dashboard.py`
2. Open http://localhost:5000 in your browser
3. Click "Start Simulation" to begin monitoring
4. Toggle "Energy Optimization" for power-saving features

### Dashboard Components

#### 📊 Real-time Monitoring
- **Power Consumption**: Live power usage graphs
- **Sensor Readings**: Individual charts for each sensor type:
  - 🌡️ Temperature (°C)
  - 💧 Humidity (%)
  - 🌬️ Air Quality (AQI)
  - 💡 Light Level (lux)
  - 🚶 Motion Detection
  - 🔊 Sound Level (dB)

#### ⚙️ Control Panel
- **Start/Stop**: Control simulation state
- **Optimization Toggle**: Enable/disable energy saving
- **Real-time Controls**: Adjust duty cycle and aggregation factors
- **System Status**: Monitor connection and simulation state

#### 🚨 Alert System
- **Real-time Alerts**: Instant notifications for threshold violations
- **Alert History**: Track all system alerts
- **Severity Levels**: Critical, high, medium, and low alerts
- **Email Integration**: Automated email notifications (when configured)

#### 📈 Analytics
- **Historical Charts**: Detailed trend analysis for each sensor
- **Power Analysis**: Comprehensive power consumption breakdown
- **Optimization Metrics**: Energy savings visualization
- **System Statistics**: Performance and efficiency metrics

### Energy Optimization Features
- **Duty Cycling**: Control sensor active time (10-100%)
- **Data Aggregation**: Reduce communication overhead (10-90%)
- **Real-time Adjustment**: Modify parameters during simulation
- **Savings Tracking**: Monitor energy efficiency improvements

## 🏠 Smart Home Sensors

### Sensor Types and Locations
- **Living Room**: Temperature, Humidity, Air Quality, Light, Motion, Sound
- **Master Bedroom**: Temperature, Humidity, Light, Sound
- **Kitchen**: Temperature, Humidity, Air Quality
- **Home Office**: Light sensor
- **Front Door**: Motion detection
- **Back Yard**: Motion detection

### Threshold-based Alerting
- **Temperature**: 18-28°C (normal), 10-35°C (critical)
- **Humidity**: 40-70% (normal), 25-85% (critical)
- **Air Quality**: 0-50 AQI (good), 100+ (unhealthy)
- **Light**: 200-1000 lux (adequate), 50-1500 (acceptable)
- **Sound**: 30-60 dB (quiet), 80+ dB (loud)

## 🔧 Configuration

### Email Alerts (Optional)
Edit `main.py` to configure email notifications:
```python
self.sender_email = 'your-email@gmail.com'
self.receiver_email = 'alert-recipient@gmail.com'
self.app_password = 'your-app-password'
```

### MQTT Settings
Configure MQTT broker in `mqtt_client.py`:
```python
broker = "broker.hivemq.com"  # Default public broker
port = 1883
```

### Optimization Parameters
Default settings in `web_dashboard.py`:
```python
duty_cycle = 0.8  # 80% active time
aggregation_factor = 0.7  # 30% power reduction
```

## 📱 Mobile Access

The web dashboard is fully responsive and works on:
- 📱 Smartphones (iOS/Android)
- 📟 Tablets
- 💻 Desktop computers
- 🖥️ Large displays

## 🛠️ Troubleshooting

### Common Issues

1. **Port 5000 already in use**:
   ```bash
   # Change port in web_dashboard.py
   socketio.run(app, port=5001)
   ```

2. **Dependencies missing**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Charts not loading**:
   - Refresh the browser
   - Check browser console for errors
   - Ensure JavaScript is enabled

4. **Simulation not starting**:
   - Check that all sensors are initialized
   - Verify MQTT connectivity
   - Review console logs for errors

### Browser Compatibility
- ✅ Chrome/Chromium (recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ⚠️ Internet Explorer (not recommended)

## 📊 Data Export

### Web Dashboard
- Right-click charts to save as images
- Use browser print function for reports
- Screenshots for presentation purposes

### Original Simulation
- Automatic PNG export with timestamps
- Comprehensive PDF reports
- CSV data export capabilities

## 🔮 Advanced Features

### Real-time WebSocket Communication
- Bi-directional data streaming
- Low-latency updates (< 100ms)
- Automatic reconnection handling
- Concurrent user support

### Performance Optimization
- Data point limiting for smooth performance
- Efficient chart updates
- Memory management
- Responsive design patterns

### Extensibility
- Modular sensor architecture
- Easy addition of new sensor types
- Configurable alert thresholds
- Customizable dashboard layouts

## 📚 Technical Details

### Architecture
- **Backend**: Flask + SocketIO
- **Frontend**: Bootstrap 5 + Chart.js
- **Real-time**: WebSocket communication
- **Data**: NumPy arrays and JSON
- **Visualization**: Chart.js and Matplotlib

### Communication Protocols
- **HTTP/HTTPS**: REST API endpoints
- **WebSocket**: Real-time data streaming
- **MQTT**: IoT device communication
- **JSON**: Data serialization format

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and enhancement requests.

## 📄 License

This project is based on IEEE research papers and industry standards for IoT systems and smart home automation.

## 🆘 Support

For support and questions:
1. Check the troubleshooting section
2. Review console logs for errors
3. Ensure all dependencies are installed
4. Test with the original simulation first

---

**Enjoy monitoring your Smart Home IoT system! 🏠✨**
