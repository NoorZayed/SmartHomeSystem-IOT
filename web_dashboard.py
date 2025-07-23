#!/usr/bin/env python3
# web_dashboard.py - Flask Web Dashboard for Smart Home IoT System
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import json
import threading
import time
from datetime import datetime, timedelta
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for web
import matplotlib.pyplot as plt
import io
import base64
from main import IoTSystem
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart_home_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global variables for the IoT system
iot_system = None
simulation_thread = None
simulation_running = False
simulation_data = {
    'timestamps': [],
    'power_consumption': [],
    'sensor_readings': {},  # Dictionary to store sensor readings by type
    'communication_power': [],
    'optimization_savings': [],
    'alerts': []
}

class WebDashboardManager:
    """
    Manager class for the web dashboard
    Handles simulation control, data collection, and real-time updates
    Acts as the bridge between the IoT system and the web interface
    """
    def __init__(self):
        """Initialize the dashboard manager with default settings"""
        self.iot_system = IoTSystem()
        self.running = False
        self.update_interval = 2  # seconds
        self.max_data_points = 50  # Keep last 50 data points for real-time display
        self.simulation_thread = None
        
    def start_simulation(self, optimization_enabled=False):
        """
        Start the IoT simulation for web dashboard
        Begins collecting sensor data and updating the dashboard
        Enables optimization features if requested
        """
        global simulation_running, simulation_data
        
        if self.running:
            return False
            
        logger.info("Starting IoT simulation for web dashboard")
        self.running = True
        simulation_running = True
        
        # Clear previous data
        simulation_data = {
            'timestamps': [],
            'power_consumption': [],
            'sensor_readings': {},
            'communication_power': [],
            'optimization_savings': [],
            'alerts': []
        }
        
        # Configure optimization
        self.iot_system.optimizer.optimization_enabled = optimization_enabled
        if optimization_enabled:
            self.iot_system.optimizer.enable_duty_cycling(self.iot_system.sensors, 0.8)
        
        # Start simulation thread
        if self.simulation_thread is None or not self.simulation_thread.is_alive():
            self.simulation_thread = threading.Thread(target=self._run_simulation)
            self.simulation_thread.daemon = True
            self.simulation_thread.start()
            logger.info(f"Simulation thread started: {self.simulation_thread.name}")
        else:
            logger.warning("Simulation thread already running")
        
        return True
    
    def stop_simulation(self):
        """Stop the IoT simulation"""
        global simulation_running
        
        logger.info("Stopping IoT simulation")
        self.running = False
        simulation_running = False
        
        # Wait for the thread to finish if it's running
        if self.simulation_thread and self.simulation_thread.is_alive():
            logger.info("Waiting for simulation thread to terminate...")
            self.simulation_thread.join(timeout=5.0)
            logger.info("Simulation thread terminated")
            
    def _run_simulation(self):
        """Main simulation loop for web dashboard"""
        global simulation_data, simulation_running
        
        cycle_count = 0
        baseline_power = None
        
        logger.info("Simulation loop started")
        
        while self.running:
            try:
                cycle_start = datetime.now()
                
                # Collect sensor data
                readings = self.iot_system.collect_sensor_data()
                
                # Store baseline power if not set
                if baseline_power is None:
                    baseline_power = sum(r.power_consumed for r in readings)
                
                # Apply optimization if enabled
                if self.iot_system.optimizer.optimization_enabled:
                    readings = self.iot_system.optimizer.aggregate_data(readings)
                
                # Simulate communication
                comm_power_cycle = 0.0
                for reading in readings:
                    base_sensor_id = reading.sensor_id.split('_')[0]
                    matching_sensor = next((s for s in self.iot_system.sensors if s.sensor_id == base_sensor_id), None)
                    
                    payload = {
                        'sensor_id': reading.sensor_id,
                        'value': reading.value,
                        'unit': reading.unit,
                        'timestamp': reading.timestamp.isoformat(),
                        'location': matching_sensor.location if matching_sensor else "Unknown"
                    }
                    
                    sensor_location = matching_sensor.location if matching_sensor else None
                    success, power = self.iot_system.communication.publish_message(
                        f"sensors/{reading.sensor_id}", 
                        payload, 
                        sensor_location=sensor_location
                    )
                    comm_power_cycle += power
                
                # Calculate power metrics
                try:
                    power_metrics = self.iot_system.calculate_system_power(readings, comm_power_cycle)
                except Exception as e:
                    logger.error(f"Error calculating power metrics: {e}")
                    # Use default values to continue simulation
                    power_metrics = type('PowerMetrics', (), {
                        'total_power': 100.0,
                        'sensing_power': 50.0,
                        'communication_power': comm_power_cycle,
                        'processing_power': 10.0,
                        'sleep_power': 5.0
                    })()
                
                # Calculate optimization savings
                optimization_savings = 0
                if self.iot_system.optimizer.optimization_enabled and baseline_power and baseline_power > 0:
                    optimization_savings = max(0, baseline_power - power_metrics.total_power)
                
                # Update simulation data (keep only recent data for performance)
                simulation_data['timestamps'].append(cycle_start.isoformat())
                simulation_data['power_consumption'].append(round(power_metrics.total_power, 2))
                simulation_data['communication_power'].append(round(comm_power_cycle, 2))
                simulation_data['optimization_savings'].append(round(optimization_savings, 2))
                
                # Process sensor readings for web display
                sensor_data = {}
                for reading in readings:
                    sensor_type = reading.sensor_id.split('_')[-1]
                    sensor_location = next((s.location for s in self.iot_system.sensors 
                                          if s.sensor_id == reading.sensor_id.split('_')[0]), "Unknown")
                    
                    if sensor_type not in sensor_data:
                        sensor_data[sensor_type] = []
                    
                    sensor_data[sensor_type].append({
                        'sensor_id': reading.sensor_id,
                        'value': round(reading.value, 2),
                        'unit': reading.unit,
                        'location': sensor_location,
                        'timestamp': reading.timestamp.isoformat() if hasattr(reading.timestamp, 'isoformat') else str(reading.timestamp)
                    })
                
                simulation_data['sensor_readings'] = sensor_data
                
                # Get alert summary
                alert_summary = self.iot_system.email_alert_system.get_alert_summary()
                simulation_data['alerts'] = alert_summary
                
                # Keep only recent data points
                for key in ['timestamps', 'power_consumption', 'communication_power', 'optimization_savings']:
                    if len(simulation_data[key]) > self.max_data_points:
                        simulation_data[key] = simulation_data[key][-self.max_data_points:]
                
                # Emit data to web clients
                try:
                    data_packet = {
                        'power_metrics': {
                            'total_power': round(power_metrics.total_power, 2),
                            'sensing_power': round(power_metrics.sensing_power, 2),
                            'communication_power': round(power_metrics.communication_power, 2),
                            'processing_power': round(power_metrics.processing_power, 2),
                            'sleep_power': round(power_metrics.sleep_power, 2)
                        },
                        'sensor_data': sensor_data,
                        'optimization_savings': round(optimization_savings, 2),
                        'timestamp': cycle_start.isoformat() if hasattr(cycle_start, 'isoformat') else str(cycle_start),
                        'cycle': cycle_count,
                        'alert_summary': alert_summary
                    }
                    socketio.emit('sensor_update', data_packet, namespace='/')
                    logger.info(f"Emitted data packet cycle {cycle_count} with {len(data_packet['sensor_data'])} sensor types")
                    # Debug the emitted data
                    for sensor_type, readings in data_packet['sensor_data'].items():
                        logger.info(f"  - {sensor_type}: {len(readings)} readings")
                except Exception as e:
                    logger.error(f"Failed to emit data: {e}")
                
                cycle_count += 1
                
                # Wait for next cycle
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in simulation cycle: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                time.sleep(1)  # Brief pause before retrying

# Initialize dashboard manager
dashboard_manager = WebDashboardManager()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/start_simulation', methods=['POST'])
def start_simulation():
    """Start the IoT simulation"""
    data = request.get_json()
    optimization_enabled = data.get('optimization_enabled', False)
    
    success = dashboard_manager.start_simulation(optimization_enabled)
    
    return jsonify({
        'success': success,
        'message': 'Simulation started successfully' if success else 'Simulation already running'
    })

@app.route('/api/stop_simulation', methods=['POST'])
def stop_simulation():
    """Stop the IoT simulation"""
    dashboard_manager.stop_simulation()
    
    return jsonify({
        'success': True,
        'message': 'Simulation stopped'
    })

@app.route('/api/simulation_status')
def simulation_status():
    """Get current simulation status"""
    return jsonify({
        'running': simulation_running,
        'data_points': len(simulation_data.get('timestamps', [])),
        'optimization_enabled': dashboard_manager.iot_system.optimizer.optimization_enabled if dashboard_manager.iot_system else False
    })

@app.route('/api/sensor_data')
def get_sensor_data():
    """Get current sensor data"""
    # Transform simulation_data to the format expected by the dashboard
    power_data = simulation_data.get('power_consumption', [])
    comm_data = simulation_data.get('communication_power', [])
    
    # Calculate power metrics from the latest data
    if power_data and comm_data:
        latest_total = power_data[-1] if power_data else 0
        latest_comm = comm_data[-1] if comm_data else 0
        
        # Estimate other power components based on typical IoT distributions
        sensing_power = latest_total * 0.4
        processing_power = latest_total * 0.1
        sleep_power = latest_total * 0.1
        
        power_metrics = {
            'total_power': latest_total,
            'sensing_power': sensing_power,
            'communication_power': latest_comm,
            'processing_power': processing_power,
            'sleep_power': sleep_power
        }
    else:
        power_metrics = {
            'total_power': 0,
            'sensing_power': 0,
            'communication_power': 0,
            'processing_power': 0,
            'sleep_power': 0
        }
    
    # Transform sensor_readings to sensor_data format
    sensor_readings = simulation_data.get('sensor_readings', {})
    sensor_data = {}
    for sensor_type, readings in sensor_readings.items():
        if readings:
            sensor_data[sensor_type] = readings
    
    # Get alert summary
    alerts = simulation_data.get('alerts', [])
    alert_summary = {}
    if isinstance(alerts, dict):
        alert_summary = alerts
    elif isinstance(alerts, list):
        # Count alerts by severity if it's a list
        alert_summary = {
            'total': len(alerts),
            'by_severity': {},
            'most_recent': alerts[-1].get('timestamp') if alerts else None
        }
    
    response_data = {
        'power_metrics': power_metrics,
        'sensor_data': sensor_data,
        'alert_summary': alert_summary,
        'cycle': len(simulation_data.get('timestamps', []))
    }
    
    return jsonify(response_data)
# charts 

@app.route('/api/historical_chart/<sensor_type>')
def get_historical_chart(sensor_type):
    """Generate historical chart for specific sensor type"""
    try:
        # Create matplotlib figure
        plt.style.use('default')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Get sensor data for the specified type
        sensor_readings = simulation_data.get('sensor_readings', {}).get(sensor_type, [])
        
        if not sensor_readings:
            ax.text(0.5, 0.5, f'No data available for {sensor_type} sensor', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{sensor_type.title()} Sensor - No Data')
        else:
            # Extract values and timestamps
            values = [reading['value'] for reading in sensor_readings]
            timestamps = simulation_data.get('timestamps', [])[:len(values)]
            
            # Plot the data
            ax.plot(timestamps, values, 'b-', linewidth=2, label=f'{sensor_type.title()}')
            ax.set_title(f'{sensor_type.title()} Sensor Historical Data')
            ax.set_xlabel('Time')
            ax.set_ylabel(f'Value ({sensor_readings[0]["unit"] if sensor_readings else ""})')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Rotate x-axis labels for better readability
            plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Convert plot to base64 string
        img = io.BytesIO()
        plt.savefig(img, format='png', dpi=150, bbox_inches='tight')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()
        
        return jsonify({
            'success': True,
            'chart': plot_url
        })
        
    except Exception as e:
        logger.error(f"Error generating chart for {sensor_type}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/power_analysis')
def get_power_analysis():
    """Generate power consumption analysis chart"""
    try:
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Power consumption over time
        power_data = simulation_data.get('power_consumption', [])
        comm_data = simulation_data.get('communication_power', [])
        timestamps = simulation_data.get('timestamps', [])[:len(power_data)]
        
        if power_data:
            ax1.plot(timestamps, power_data, 'b-', linewidth=2, label='Total Power')
            ax1.plot(timestamps, comm_data, 'r--', linewidth=1, label='Communication Power')
            ax1.set_title('Power Consumption Over Time')
            ax1.set_ylabel('Power (mW)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis='x', rotation=45)
        
        # Power distribution pie chart
        if power_data:
            avg_total = np.mean(power_data)
            avg_comm = np.mean(comm_data)
            avg_sensing = avg_total * 0.4
            avg_processing = avg_total * 0.1
            avg_sleep = avg_total * 0.1
            
            sizes = [avg_sensing, avg_comm, avg_processing, avg_sleep]
            labels = ['Sensing', 'Communication', 'Processing', 'Sleep']
            colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
            
            ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax2.set_title('Power Distribution')
        
        # Optimization savings
        opt_data = simulation_data.get('optimization_savings', [])
        if opt_data and any(val > 0 for val in opt_data):
            ax3.plot(timestamps[:len(opt_data)], opt_data, 'g-', linewidth=2)
            ax3.set_title('Energy Optimization Savings')
            ax3.set_ylabel('Power Savings (mW)')
            ax3.grid(True, alpha=0.3)
            ax3.tick_params(axis='x', rotation=45)
        else:
            ax3.text(0.5, 0.5, 'No optimization savings data', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('Energy Optimization Savings')
        
        # System statistics
        if power_data:
            stats_text = f"""System Statistics:
            
Average Power: {np.mean(power_data):.2f} mW
Max Power: {np.max(power_data):.2f} mW
Min Power: {np.min(power_data):.2f} mW
Total Energy: {np.sum(power_data)*2/1000/3600:.4f} Wh

Communication Stats:
Avg Comm Power: {np.mean(comm_data):.2f} mW
Comm Efficiency: {(np.mean(comm_data)/max(np.mean(power_data), 0.001)*100):.1f}%

Data Points: {len(power_data)}
Duration: {len(power_data)*2/60:.1f} minutes"""
            
            ax4.text(0.1, 0.9, stats_text, ha='left', va='top', transform=ax4.transAxes,
                    fontsize=10, bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.5))
            ax4.set_title('System Statistics')
            ax4.axis('off')
        
        plt.tight_layout()
        
        # Convert to base64
        img = io.BytesIO()
        plt.savefig(img, format='png', dpi=150, bbox_inches='tight')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()
        
        return jsonify({
            'success': True,
            'chart': plot_url
        })
        
    except Exception as e:
        logger.error(f"Error generating power analysis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/update_optimization', methods=['POST'])
def update_optimization():
    """Update optimization parameters"""
    try:
        data = request.get_json()
        duty_cycle = data.get('duty_cycle', 80) / 100.0
        aggregation_factor = 1.0 - (data.get('aggregation_factor', 30) / 100.0)
        
        if dashboard_manager.iot_system:
            dashboard_manager.iot_system.optimizer.update_optimization_params(
                dashboard_manager.iot_system.sensors,
                duty_cycle=duty_cycle,
                aggregation_factor=aggregation_factor
            )
            
            return jsonify({
                'success': True,
                'message': 'Optimization parameters updated',
                'duty_cycle': duty_cycle * 100,
                'aggregation_factor': (1 - aggregation_factor) * 100
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No active simulation'
            })
            
    except Exception as e:
        logger.error(f"Error updating optimization: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected to dashboard')
    emit('connected', {'message': 'Connected to Smart Home IoT Dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected from dashboard')

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("=" * 60)
    print("SMART HOME IOT WEB DASHBOARD")
    print("=" * 60)
    print("Starting Flask web server...")
    print("Dashboard will be available at: http://localhost:5001")
    print("=" * 60)
    
    # Run the Flask app
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
