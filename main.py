# main.py - Smart Home IoT System Simulation
# =============================================================================
# This is the core simulation engine for the IoT Smart Home system.
# It implements:
# - Sensor classes (temperature, humidity, air quality, light, motion, noise)
# - IEEE-referenced power consumption models for accurate simulation
# - MQTT communication protocol with distance-based power calculations
# - Energy optimization strategies (duty cycling, data aggregation)
# - Real-time visualization and monitoring system
# - Email alert system for abnormal conditions
# 
# This file follows IoT Level 5 architecture (internet connectivity with cloud processing)
# and implements scientific models from referenced IEEE papers.
# =============================================================================

import asyncio
import json
import time
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass
from typing import Dict, List, Tuple
import logging
import random
import math
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SensorReading:
    """
    Data class for sensor readings
    Stores each individual reading from a sensor with timestamp and power information
    Used to track data throughout the system and for visualization
    """
    timestamp: datetime
    sensor_id: str
    value: float
    unit: str
    power_consumed: float

@dataclass
class PowerMetrics:
    """
    Power consumption metrics
    Tracks different power components (sensing, communication, processing, sleep)
    Used for energy optimization analysis and visualization
    """
    sensing_power: float = 0.0
    communication_power: float = 0.0
    processing_power: float = 0.0
    sleep_power: float = 0.0
    total_power: float = 0.0

@dataclass
class AlertData:
    """
    Data class for system alerts
    Stores alert information for abnormal sensor readings
    Used by the email alert system to notify users of potential issues
    """
    timestamp: datetime
    alert_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    sensor_id: str
    sensor_location: str
    current_value: float
    threshold_value: float
    unit: str
    message: str

class EmailAlertSystem:
    """
    Email alert system for smart home security and automation
    Sends email alerts when home sensors detect abnormal conditions
    Implements:
    - Configurable thresholds for different sensor types
    - Severity classification (low, medium, high, critical)
    - HTML-formatted email alerts with recommended actions
    - Alert cooldown periods to prevent spam
    - Alert history tracking for analysis
    """
    
    def __init__(self):
        # Email configuration
        self.sender_email = 'noorzayed204@gmail.com'
        self.receiver_email = 'noorzayed204@gmail.com'
        self.app_password = 'ztlvcpqbxgoyhicg'
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        
        # Alert thresholds for different sensor types (Smart Home)
        self.thresholds = {
            'temperature': {'min': 18.0, 'max': 28.0, 'critical_min': 10.0, 'critical_max': 35.0},
            'humidity': {'min': 40.0, 'max': 70.0, 'critical_min': 25.0, 'critical_max': 85.0},
            'air_quality': {'min': 0.0, 'max': 50.0, 'critical_min': 0.0, 'critical_max': 100.0},  # Air Quality Index
            'light': {'min': 200.0, 'max': 1000.0, 'critical_min': 50.0, 'critical_max': 1500.0},
            'noise': {'min': 30.0, 'max': 60.0, 'critical_min': 20.0, 'critical_max': 80.0}  # Decibels
        }
          # Alert history and cooldown management
        self.alert_history = []
        self.last_alert_time = {}  # Track last alert time per sensor/alert type
        self.alert_cooldown = 300  # 5 minutes cooldown between similar alerts
        self.pending_alerts = set()  # Track alerts being processed to prevent duplicates
        self.email_enabled = True
        
        logger.info("📧 Email Alert System initialized successfully")
        logger.info(f"   Alert receiver: {self.receiver_email}")
        logger.info(f"   Alert sender: {self.sender_email}")
    
    def check_sensor_reading(self, reading: 'SensorReading') -> List[AlertData]:
        """
        Check a sensor reading for abnormal conditions
        Returns list of alerts if any thresholds are exceeded
        """
        alerts = []
        current_time = datetime.now()
        
        # Extract sensor type from sensor_id (e.g., 'greenhouse_01_temp' -> 'temperature')
        sensor_parts = reading.sensor_id.split('_')
        if len(sensor_parts) < 2:
            return alerts
            
        sensor_type = sensor_parts[-1]  # Get the last part (temp, hum, soil, light, motion)
          # Map sensor types to threshold keys (Smart Home)
        type_mapping = {
            'temp': 'temperature',
            'hum': 'humidity', 
            'air': 'air_quality',
            'light': 'light',
            'noise': 'noise',
            'motion': None  # Motion sensor doesn't need threshold checking
        }
        
        threshold_key = type_mapping.get(sensor_type)
        if not threshold_key or threshold_key not in self.thresholds:
            return alerts
            
        thresholds = self.thresholds[threshold_key]
        value = reading.value
        
        # Extract base sensor info
        base_sensor_id = '_'.join(sensor_parts[:-1])  # Remove the sensor type part
        location = "Unknown Location"  # Will be updated by the calling function
        
        # Check for critical conditions first
        alert_type = None
        severity = None
        threshold_exceeded = None
        
        if value < thresholds['critical_min']:
            alert_type = f"Critical Low {threshold_key.replace('_', ' ').title()}"
            severity = "critical"
            threshold_exceeded = thresholds['critical_min']
        elif value > thresholds['critical_max']:
            alert_type = f"Critical High {threshold_key.replace('_', ' ').title()}"
            severity = "critical"
            threshold_exceeded = thresholds['critical_max']
        elif value < thresholds['min']:
            alert_type = f"Low {threshold_key.replace('_', ' ').title()}"
            severity = "high"
            threshold_exceeded = thresholds['min']
        elif value > thresholds['max']:
            alert_type = f"High {threshold_key.replace('_', ' ').title()}"
            severity = "high"
            threshold_exceeded = thresholds['max']
          # If an alert condition is detected
        if alert_type:
            # Check cooldown period and prevent duplicates
            alert_key = f"{base_sensor_id}_{alert_type}"
            last_alert = self.last_alert_time.get(alert_key, datetime.min)
            time_since_last = (current_time - last_alert).total_seconds()
            
            # Check if this alert is already being processed
            if alert_key in self.pending_alerts:
                logger.debug(f"Alert {alert_key} already being processed, skipping duplicate")
                return alerts
            
            if time_since_last >= self.alert_cooldown:
                # Mark alert as being processed
                self.pending_alerts.add(alert_key)
                
                alert = AlertData(
                    timestamp=current_time,
                    alert_type=alert_type,
                    severity=severity,
                    sensor_id=reading.sensor_id,
                    sensor_location=location,
                    current_value=value,
                    threshold_value=threshold_exceeded,
                    unit=reading.unit,
                    message=self._generate_alert_message(alert_type, value, threshold_exceeded, reading.unit, location)
                )
                
                alerts.append(alert)
                self.last_alert_time[alert_key] = current_time
                
                logger.warning(f"🚨 ALERT DETECTED: {alert_type} - {base_sensor_id} at {location}")
                logger.warning(f"   Current: {value:.1f} {reading.unit}, Threshold: {threshold_exceeded:.1f} {reading.unit}")
            else:
                logger.debug(f"Alert {alert_key} in cooldown period ({time_since_last:.0f}s < {self.alert_cooldown}s)")
        
        return alerts
    
    def _generate_alert_message(self, alert_type: str, current_value: float, 
                              threshold_value: float, unit: str, location: str) -> str:
        """Generate a descriptive alert message"""
        if "Critical" in alert_type:
            urgency = "CRITICAL ALERT"
            action = "IMMEDIATE ACTION REQUIRED"
        else:
            urgency = "WARNING ALERT"
            action = "Please check the system"
            
        return (f"{urgency}: {alert_type} detected at {location}. "
                f"Current reading: {current_value:.1f} {unit}, "
                f"Threshold: {threshold_value:.1f} {unit}. {action}.")
    
    def send_email_alert(self, alert: AlertData) -> bool:
        """
        Send email notification for an alert
        Returns True if email was sent successfully, False otherwise
        """
        if not self.email_enabled:
            logger.info(f"📧 Email alert disabled - would send: {alert.alert_type}")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            msg['Subject'] = f"🚨 Smart Home Alert: {alert.alert_type}"
            
            # Create email body
            body = self._create_email_body(alert)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.send_message(msg)
            
            logger.info(f"📧 Email alert sent successfully: {alert.alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email alert: {str(e)}")
            return False
    
    def _create_email_body(self, alert: AlertData) -> str:
        """Create formatted HTML email body"""
        severity_colors = {
            'critical': '#FF0000',  # Red
            'high': '#FF6600',      # Orange
            'medium': '#FFCC00',    # Yellow
            'low': '#00CC00'        # Green
        }
        
        color = severity_colors.get(alert.severity, '#000000')
        
        return f"""
        <html>
        <body>
            <h2 style="color: {color};">🚨 Smart Home IoT System Alert</h2>
            
            <div style="border: 2px solid {color}; padding: 15px; border-radius: 10px; background-color: #f9f9f9;">
                <h3>Alert Details:</h3>
                <ul>
                    <li><strong>Alert Type:</strong> {alert.alert_type}</li>
                    <li><strong>Severity:</strong> <span style="color: {color}; font-weight: bold;">{alert.severity.upper()}</span></li>
                    <li><strong>Sensor ID:</strong> {alert.sensor_id}</li>
                    <li><strong>Location:</strong> {alert.sensor_location}</li>
                    <li><strong>Current Value:</strong> {alert.current_value:.2f} {alert.unit}</li>
                    <li><strong>Threshold:</strong> {alert.threshold_value:.2f} {alert.unit}</li>
                    <li><strong>Timestamp:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</li>
                </ul>
                
                <h3>Message:</h3>
                <p style="background-color: #ffeb3b; padding: 10px; border-radius: 5px; font-weight: bold;">
                    {alert.message}
                </p>
            </div>
            
            <div style="margin-top: 20px; padding: 10px; background-color: #e3f2fd; border-radius: 5px;">
                <h3>Recommended Actions:</h3>
                {self._get_recommended_actions(alert)}
            </div>
              <hr>
            <p style="font-size: 12px; color: #666;">
                This alert was generated automatically by the Smart Home IoT System.<br>
                System Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </body>
        </html>
        """
    
    def _get_recommended_actions(self, alert: AlertData) -> str:
        """Get recommended actions based on alert type (Smart Home)"""
        actions = {
            'temperature': {
                'low': "• Check heating system<br>• Close windows and doors<br>• Check thermostat settings",
                'high': "• Turn on air conditioning<br>• Open windows for ventilation<br>• Close curtains/blinds"
            },
            'humidity': {
                'low': "• Use humidifier<br>• Check for air leaks<br>• Adjust HVAC settings",
                'high': "• Use dehumidifier<br>• Improve ventilation<br>• Check for water leaks or moisture sources"
            },
            'air_quality': {
                'low': "• Open windows for fresh air<br>• Check air purifier filters<br>• Ensure proper ventilation",
                'high': "• Close windows<br>• Turn on air purifier<br>• Check for pollution sources"
            },
            'light': {
                'low': "• Turn on lights<br>• Open curtains/blinds<br>• Check light bulbs",
                'high': "• Dim lights<br>• Close curtains/blinds<br>• Use window shades"
            },
            'noise': {
                'low': "• Check for malfunctioning devices<br>• Ensure normal household activity",
                'high': "• Check for loud appliances<br>• Investigate noise sources<br>• Consider soundproofing"
            }
        }
          # Extract measurement type from alert type
        for measurement in actions.keys():
            if measurement.replace('_', ' ') in alert.alert_type.lower():
                if 'low' in alert.alert_type.lower() or 'critical low' in alert.alert_type.lower():
                    return actions[measurement].get('low', '• Check system components<br>• Contact maintenance')
                else:
                    return actions[measurement].get('high', '• Check system components<br>• Contact maintenance')
        
        return "• Check system components<br>• Review sensor readings<br>• Contact technical support"
    
    def process_alerts(self, alerts: List[AlertData]) -> int:
        """
        Process a list of alerts and send email notifications
        Returns the number of emails sent successfully
        """
        emails_sent = 0
        
        for alert in alerts:
            # Add to alert history
            self.alert_history.append(alert)
              # Send email notification
            if self.send_email_alert(alert):
                emails_sent += 1
            
            # Remove from pending alerts after processing
            alert_key = f"{alert.sensor_id.rsplit('_', 1)[0]}_{alert.alert_type}"
            self.pending_alerts.discard(alert_key)  # Use discard to avoid KeyError
                
        return emails_sent
    
    def clear_pending_alerts(self):
        """Clear all pending alerts (useful for cleanup or reset)"""
        self.pending_alerts.clear()
        logger.info("Cleared all pending alerts")
    
    def get_pending_alerts_count(self) -> int:
        """Get the number of pending alerts"""
        return len(self.pending_alerts)

    def get_alert_summary(self) -> Dict:
        """Get summary of alerts generated"""
        total_alerts = len(self.alert_history)
        if total_alerts == 0:
            return {'total': 0, 'by_severity': {}, 'by_type': {}}
        
        by_severity = {}
        by_type = {}
        
        for alert in self.alert_history:
            # Count by severity
            by_severity[alert.severity] = by_severity.get(alert.severity, 0) + 1
            
            # Count by type
            by_type[alert.alert_type] = by_type.get(alert.alert_type, 0) + 1
        
        return {
            'total': total_alerts,
            'by_severity': by_severity,
            'by_type': by_type,
            'most_recent': self.alert_history[-1].timestamp.isoformat() if self.alert_history else None
        }
    
    def set_email_enabled(self, enabled: bool):
        """Enable or disable email notifications"""
        self.email_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"📧 Email notifications {status}")

class IoTSensor:
    """
    Base IoT Sensor class with power modeling
    Based on: Kumar et al. (2019) "Smart Home Monitoring System Using IoT"
    IEEE Transactions on Consumer Electronics
    """
    
    def __init__(self, sensor_id: str, sensor_type: str, location: str):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.location = location
        self.is_active = True
        self.duty_cycle = 1.0  # 100% active by default
          # Power consumption parameters (mW) - Based on literature
        self.power_specs = {
            'DHT22': {'sensing': 1.5, 'communication': 15.0, 'processing': 0.8, 'sleep': 0.05},
            'LDR': {'sensing': 0.5, 'communication': 12.0, 'processing': 0.3, 'sleep': 0.02},
            'AirQuality': {'sensing': 2.5, 'communication': 20.0, 'processing': 1.2, 'sleep': 0.1},
            'Noise': {'sensing': 1.8, 'communication': 16.0, 'processing': 0.9, 'sleep': 0.06},
            'PIR': {'sensing': 0.8, 'communication': 10.0, 'processing': 0.5, 'sleep': 0.03}
        }
        
        # Get power specs for this sensor type
        self.power = self.power_specs.get(sensor_type, self.power_specs['DHT22'])
        
    def calculate_power_consumption(self, operation_time: float, operation_type: str) -> float:
        """
        Calculate power consumption based on operation type and time
        Formula: P_total = P_sensing * t_sensing + P_comm * t_comm + P_proc * t_proc + P_sleep * t_sleep
        """
        if operation_type == 'sensing':
            return self.power['sensing'] * operation_time * self.duty_cycle
        elif operation_type == 'communication':
            return self.power['communication'] * operation_time
        elif operation_type == 'processing':
            return self.power['processing'] * operation_time
        elif operation_type == 'sleep':
            return self.power['sleep'] * operation_time * (1 - self.duty_cycle)
        else:
            return 0.0
    
    def read_value(self) -> float:
        """Override in subclass"""
        raise NotImplementedError

class TemperatureHumiditySensor(IoTSensor):
    """
    DHT22 Temperature and Humidity Sensor
    Scientific Justification: Widely used in smart homes for comfort monitoring
    Reference: Kumar et al. (2019) "Smart Home Monitoring System Using IoT"
    """
    
    def __init__(self, sensor_id: str, location: str):
        super().__init__(sensor_id, 'DHT22', location)
        self.base_temp = 25.0
        self.base_humidity = 60.0
    
    def read_temperature(self) -> SensorReading:
        # Simulate realistic temperature with seasonal and daily variations
        hour = datetime.now().hour
        seasonal_factor = math.sin(time.time() / (365 * 24 * 3600) * 2 * math.pi) * 10
        daily_factor = math.sin(hour / 24 * 2 * math.pi) * 5
        noise = random.gauss(0, 1)
        
        temp = self.base_temp + seasonal_factor + daily_factor + noise
        
        # 10% chance of abnormal readings to trigger email alerts
        if random.random() < 0.1:  # 10% chance
            if random.random() < 0.5:
                temp = random.uniform(45, 55)  # Critical high temperature
            else:
                temp = random.uniform(-5, 5)   # Critical low temperature
        
        power = self.calculate_power_consumption(0.1, 'sensing')  # 0.1s sensing time        
        return SensorReading(datetime.now(), f"{self.sensor_id}_temp", temp, "°C", power)
    
    def read_humidity(self) -> SensorReading:
        # Humidity inversely related to temperature
        temp_reading = self.read_temperature()
        humidity = max(20, min(95, self.base_humidity - (temp_reading.value - self.base_temp) * 2 + random.gauss(0, 3)))
        
        # 8% chance of abnormal humidity readings
        if random.random() < 0.08:  # 8% chance
            if random.random() < 0.5:
                humidity = random.uniform(96, 100)  # Critical high humidity
            else:
                humidity = random.uniform(10, 19)   # Critical low humidity
        
        power = self.calculate_power_consumption(0.1, 'sensing')
        
        return SensorReading(datetime.now(), f"{self.sensor_id}_hum", humidity, "%", power)

class AirQualitySensor(IoTSensor):
    """
    Air Quality Sensor (MQ-135 or similar)
    Scientific Justification: Essential for smart home air quality monitoring
    Reference: Liu et al. (2020) "Indoor Air Quality Monitoring in Smart Homes"
    """
    
    def __init__(self, sensor_id: str, location: str):
        super().__init__(sensor_id, 'AirQuality', location)
        self.base_aqi = 25.0  # Air Quality Index base value (good air quality)
        self.pollution_event = 0.0
        
    def read_value(self) -> SensorReading:
        # Simulate air quality changes throughout the day
        hour = datetime.now().hour
        
        # Higher pollution during cooking hours and lower during night
        if 7 <= hour <= 9 or 17 <= hour <= 19:  # Cooking times
            daily_factor = 15
        elif 22 <= hour or hour <= 6:  # Night/early morning
            daily_factor = -5
        else:
            daily_factor = 0
            
        aqi = max(0, self.base_aqi + daily_factor + self.pollution_event + random.gauss(0, 3))
        self.pollution_event *= 0.95  # Pollution events diminish over time
        
        # 8% chance of abnormal air quality readings
        if random.random() < 0.08:  # 8% chance
            if random.random() < 0.5:
                aqi = random.uniform(150, 200)  # Unhealthy air quality
            else:
                aqi = random.uniform(0, 10)     # Unusually clean air
        
        power = self.calculate_power_consumption(0.3, 'sensing')  # 0.3s sensing time
        
        return SensorReading(datetime.now(), f"{self.sensor_id}_air", aqi, "AQI", power)
    
    def trigger_pollution_event(self, intensity: float):
        """Simulate a pollution event (cooking, cleaning, etc.)"""
        self.pollution_event += intensity

class LightSensor(IoTSensor):
    """
    LDR (Light Dependent Resistor) Sensor
    Scientific Justification: Critical for indoor lighting automation
    Reference: Brewster et al. (2017) "IoT in Smart Homes: Designing a Lighting Control System"
    """
    
    def __init__(self, sensor_id: str, location: str):
        super().__init__(sensor_id, 'LDR', location)
    
    def read_value(self) -> SensorReading:
        # Simulate natural light patterns
        hour = datetime.now().hour
        if 6 <= hour <= 18:  # Daylight hours
            base_light = 800 * math.sin((hour - 6) / 12 * math.pi)
        else:  # Night hours
            base_light = 50
            
        # Add weather effects and noise
        weather_factor = random.uniform(0.7, 1.3)
        light = max(10, base_light * weather_factor + random.gauss(0, 50))
        
        # 6% chance of abnormal light readings
        if random.random() < 0.06:  # 6% chance
            if random.random() < 0.5:
                light = random.uniform(3500, 5000)  # Critical high light (direct sun damage)
            else:
                light = random.uniform(20, 49)      # Critical low light (insufficient lighting)
        
        power = self.calculate_power_consumption(0.05, 'sensing')  # 0.05s sensing time
        
        return SensorReading(datetime.now(), f"{self.sensor_id}_light", light, "lux", power)

class PIRSensor(IoTSensor):
    """
    PIR (Passive Infrared) Motion Sensor
    Scientific Justification: Used for security and occupancy detection in smart homes
    Reference: Khan et al. (2020) "Smart Home Security: IoT Applications for Home Automation"
    """
    
    def __init__(self, sensor_id: str, location: str):
        super().__init__(sensor_id, 'PIR', location)
        self.last_detection_time = datetime.now() - timedelta(hours=1)  # Initialize to no recent detection
        self.cooldown_period = 30  # seconds before another detection is possible
        
    def read_value(self) -> SensorReading:
        # Simulate motion detection with random events and realistic cooldown
        current_time = datetime.now()
        time_since_last = (current_time - self.last_detection_time).total_seconds()
        
        # Random chance of motion detection based on time of day
        hour = current_time.hour
        if 6 <= hour <= 18:  # Daytime - more activity
            detection_probability = 0.3
        else:  # Nighttime - less activity
            detection_probability = 0.1
            
        # Value will be 1 (motion detected) or 0 (no motion)
        motion_detected = 0
        
        # Check if we're past cooldown and random chance triggers detection
        if time_since_last > self.cooldown_period and random.random() < detection_probability:
            motion_detected = 1
            self.last_detection_time = current_time
            
        power = self.calculate_power_consumption(0.1, 'sensing')  # 0.1s sensing time
        
        return SensorReading(current_time, f"{self.sensor_id}_motion", motion_detected, "binary", power)

class NoiseSensor(IoTSensor):
    """
    Sound Level Sensor (Digital Microphone)
    Scientific Justification: Essential for smart home noise monitoring and security
    Reference: Chen et al. (2021) "Acoustic Monitoring in Smart Home Systems"
    """
    
    def __init__(self, sensor_id: str, location: str):
        super().__init__(sensor_id, 'Noise', location)
        self.base_noise = 35.0  # Base ambient noise level in dB
        
    def read_value(self) -> SensorReading:
        # Simulate noise level changes throughout the day
        hour = datetime.now().hour
        
        # Higher noise during active hours, lower during night
        if 7 <= hour <= 22:  # Active hours
            daily_factor = random.uniform(10, 25)
        else:  # Night hours
            daily_factor = random.uniform(-5, 5)
            
        noise = max(20, self.base_noise + daily_factor + random.gauss(0, 3))
        
        # 6% chance of abnormal noise readings
        if random.random() < 0.06:  # 6% chance
            if random.random() < 0.5:
                noise = random.uniform(85, 100)  # Very loud noise (alarm, emergency)
            else:
                noise = random.uniform(15, 19)   # Unusually quiet
        
        power = self.calculate_power_consumption(0.1, 'sensing')  # 0.1s sensing time
        
        return SensorReading(datetime.now(), f"{self.sensor_id}_noise", noise, "dB", power)

class CommunicationProtocol:
    """Base class for communication protocols"""
    
    def __init__(self, protocol_name: str):
        self.protocol_name = protocol_name
        self.message_count = 0
        self.total_bytes_sent = 0
        self.retry_count = 0
        
        # Gateway/Base station coordinates (x, y in meters)
        self.gateway_position = (0, 0)  # Central gateway location
          # Sensor location coordinates for distance-based power calculation (Smart Home)
        self.sensor_locations = {
            "Living Room": (8, 12),          # 8m east, 12m north from router
            "Master Bedroom": (15, 20),      # 15m east, 20m north from router  
            "Kitchen": (6, 8),               # 6m east, 8m north from router
            "Guest Bedroom": (20, 18),       # 20m east, 18m north from router
            "Bathroom": (12, 6),             # 12m east, 6m north from router
            "Home Office": (25, 15),         # 25m east, 15m north from router
            "Front Door": (3, 5),            # 3m east, 5m north from router
            "Back Yard": (10, 25)            # 10m east, 25m north from router
        }
        
    def calculate_distance(self, sensor_location: str) -> float:
        """Calculate distance between sensor and gateway"""
        if sensor_location not in self.sensor_locations:
            return 50.0  # Default distance if location not found
            
        sensor_pos = self.sensor_locations[sensor_location]
        gateway_pos = self.gateway_position
        
        # Calculate Euclidean distance
        distance = math.sqrt((sensor_pos[0] - gateway_pos[0])**2 + 
                           (sensor_pos[1] - gateway_pos[1])**2)
        return distance
        
    def calculate_transmission_power(self, distance: float) -> float:
        """
        Calculate transmission power based on distance using Free Space Path Loss formula
        Formula: P_tx = P_min + K * (d/d_ref)^n
        Where:
        - P_min: Minimum transmission power (mW)
        - K: Path loss constant
        - d: transmission distance (m)
        - d_ref: Reference distance (m)
        - n: Path loss exponent (2 for free space, 2-4 for real environments)
        
        Based on: Liu et al. (2020) "Indoor Air Quality Monitoring in Smart Homes"
        """
        P_min = 50.0    # Minimum transmission power (mW)
        K = 0.5         # Path loss constant
        d_ref = 10.0    # Reference distance (m)
        n = 3.0         # Path loss exponent for indoor environment (2.7-3.5 typical for indoor)
        
        # Calculate required transmission power with logarithmic path loss model
        if distance <= d_ref:
            return P_min
        else:
            # Improved formula using logarithmic path loss model
            # P_tx = P_min * 10^((n * log10(d/d_ref))/10)
            power_ratio = 10 ** ((n * math.log10(distance / d_ref)) / 10)
            P_tx = P_min * power_ratio
            
            # Cap maximum power to realistic values
            return min(P_tx, 200.0)  # Maximum 200mW transmission power
        
    def calculate_comm_power(self, message_size: int, transmission_time: float, 
                           sensor_location: str = None) -> float:
        """
        Calculate communication power consumption with distance-based transmission power
        Formula based on: P_comm = P_tx * t_tx + P_rx * t_rx + P_idle * t_idle
        Enhanced with distance-based power calculation
        """
        # Calculate distance-based transmission power
        if sensor_location:
            distance = self.calculate_distance(sensor_location)
            P_tx = self.calculate_transmission_power(distance)
        else:
            P_tx = 100.0  # Default transmission power for backward compatibility
            
        # Other power consumption parameters (mW)
        P_rx = 50.0   # Reception power
        P_idle = 5.0  # Idle power
        
        # Estimate transmission and reception times
        t_tx = transmission_time        # 0.1s sensing time
        t_rx = transmission_time * 0.1  # ACK reception
        t_idle = 0.1  # Idle time between operations
        
        total_power = P_tx * t_tx + P_rx * t_rx + P_idle * t_idle
        
        # Log distance effect for monitoring
        if sensor_location:
            distance = self.calculate_distance(sensor_location)
            logger.debug(f"Communication power: {total_power:.2f} mW "
                        f"(distance: {distance:.1f}m, P_tx: {P_tx:.1f} mW) "
                        f"for location: {sensor_location}")
        
        return total_power

class MQTTProtocol(CommunicationProtocol):
    """
    MQTT Protocol Simulation
    IoT Level 5: Internet connectivity with cloud processing
    """
    
    def __init__(self):
        super().__init__("MQTT")
        self.broker_connected = True
        self.qos_level = 1  # At least once delivery
        self.message_batch = []  # Store messages for batch transmission
        self.batch_size_limit = 5  # Maximum messages per batch
        self.batch_timeout = 3.0  # Seconds before sending partial batch
        self.last_batch_time = time.time()
        self.batch_mode_enabled = True  # Enable batch mode by default
        
    def publish_message(self, topic: str, payload: dict, qos: int = 1, sensor_location: str = None) -> Tuple[bool, float]:
        """
        Simulate MQTT message publication with distance-based power calculation
        Returns: (success, power_consumed)
        """
        message_size = len(json.dumps(payload).encode())
        transmission_time = message_size / 1000  # Assume 1KB/s transmission rate
        
        # Add to batch if batch mode enabled
        if self.batch_mode_enabled:
            return self._batch_message(topic, payload, message_size, transmission_time, sensor_location)
        else:
            # Regular publish for individual messages
            return self._publish_single_message(topic, payload, message_size, transmission_time, sensor_location)
    
    def _batch_message(self, topic: str, payload: dict, message_size: int, transmission_time: float, 
                     sensor_location: str = None) -> Tuple[bool, float]:
        """Batch messages for more efficient transmission"""
        # Add message to batch
        self.message_batch.append({
            'topic': topic,
            'payload': payload,
            'size': message_size,
            'time': transmission_time,
            'location': sensor_location
        })
        
        current_time = time.time()
        batch_full = len(self.message_batch) >= self.batch_size_limit
        timeout_reached = (current_time - self.last_batch_time) > self.batch_timeout
        
        # Minimum power cost for queuing the message (20% of normal transmission)
        queuing_power = self.calculate_comm_power(message_size, transmission_time * 0.2, sensor_location)
        
        # If batch is full or timeout reached, send the batch
        if batch_full or timeout_reached:
            total_size = sum(msg['size'] for msg in self.message_batch)
            # Batch transmission is more efficient - use only 70% of the power sum
            batch_transmission_time = total_size / 1200  # Slightly faster for batched messages
            
            # Calculate power for the whole batch
            total_locations = set(msg['location'] for msg in self.message_batch if msg['location'])
            
            # Use average distance for batch power calculation if multiple locations
            if sensor_location and len(total_locations) > 0:
                avg_distance = sum(self.calculate_distance(loc) for loc in total_locations) / len(total_locations)
                batch_power = self.calculate_transmission_power(avg_distance) * batch_transmission_time
            else:
                batch_power = self.calculate_comm_power(total_size, batch_transmission_time, sensor_location)
            
            # Apply batch efficiency factor - more messages = more efficiency
            efficiency_factor = max(0.5, 1.0 - (len(self.message_batch) * 0.1))  # Up to 50% power saving
            batch_power = batch_power * efficiency_factor
            
            # Simulate success/failure for the batch
            success_probability = 0.93  # Slightly lower than single message due to complexity
            success = random.random() < success_probability
            
            if success:
                logger.info(f"MQTT: Batch published {len(self.message_batch)} messages, " 
                          f"size: {total_size} bytes, power: {batch_power:.2f} mW, " 
                          f"efficiency: {(1-efficiency_factor)*100:.0f}% saving")
                
                self.message_count += len(self.message_batch)
                self.total_bytes_sent += total_size
            else:
                self.retry_count += 1
                # Failed batch costs more due to retry overhead
                batch_power *= 1.5
                logger.warning(f"MQTT: Failed batch transmission of {len(self.message_batch)} messages, retrying")
              # Clear the batch and reset timer
            batch_size = len(self.message_batch)  # Store batch size before clearing
            self.message_batch = []
            self.last_batch_time = current_time
            
            return success, queuing_power + (batch_power / max(batch_size, 1))  # Prevent division by zero
        else:
            # Return just the queuing power cost, actual transmission will happen later
            return True, queuing_power
    
    def _publish_single_message(self, topic: str, payload: dict, message_size: int, 
                              transmission_time: float, sensor_location: str = None) -> Tuple[bool, float]:
        """Publish a single message (non-batched mode)"""
        # Simulate network delays and retries
        delay = random.uniform(0.1, 0.5)
        success_probability = 0.95
        
        power_consumed = 0.0
        
        if random.random() < success_probability:
            # Successful transmission with distance-based power calculation
            power_consumed = self.calculate_comm_power(message_size, transmission_time, sensor_location)
            self.message_count += 1
            self.total_bytes_sent += message_size
            
            # Enhanced logging with distance information
            if sensor_location:
                distance = self.calculate_distance(sensor_location)
                logger.info(f"MQTT: Published to {topic} from {sensor_location} "
                          f"(distance: {distance:.1f}m), size: {message_size} bytes, power: {power_consumed:.2f} mW")
            else:
                logger.info(f"MQTT: Published to {topic}, size: {message_size} bytes, power: {power_consumed:.2f} mW")
            return True, power_consumed
        else:
            # Failed transmission - retry with distance-based power calculation
            self.retry_count += 1
            power_consumed = self.calculate_comm_power(message_size, transmission_time, sensor_location) * 2  # Double power for retry
            logger.warning(f"MQTT: Retry for topic {topic} from location {sensor_location or 'unknown'}")
            return False, power_consumed
    
    def set_batch_parameters(self, enabled: bool = True, batch_size: int = None, timeout: float = None):
        """Configure batch transmission parameters"""
        self.batch_mode_enabled = enabled
        if batch_size is not None:
            self.batch_size_limit = max(1, batch_size)
        if timeout is not None:
            self.batch_timeout = max(0.5, timeout)
        
        status = "enabled" if enabled else "disabled"
        logger.info(f"MQTT: Batch mode {status}, size: {self.batch_size_limit}, timeout: {self.batch_timeout}s")
    
    def subscribe_to_topic(self, topic: str) -> float:
        """Simulate MQTT subscription"""
        power_consumed = 5.0  # Power for maintaining subscription
        return power_consumed

class EnergyOptimizer:
    """
    Energy optimization strategies implementation
    """
    
    def __init__(self):
        self.optimization_enabled = False
        self.aggregation_window = 60  # seconds
        self.data_buffer = []
        self.duty_cycle = 0.8  # Default 80% duty cycle
        self.aggregation_factor = 0.7  # Default 30% power reduction
        self.adaptive_duty_cycling = False  # New feature for adaptive duty cycling
        self.inactivity_counter = 0  # Count periods of inactivity
        self.progressive_sleep = False  # Progressive sleep mode
        self.activity_threshold = 5.0  # Threshold to determine activity
        self.last_sensor_values = {}  # Track sensor values to detect changes
        self.sleep_levels = [0.8, 0.6, 0.4, 0.2]  # Progressive sleep levels (duty cycle)
        self.current_sleep_level = 0  # Index into sleep_levels
        self.sleep_level_timeout = 5  # Cycles before increasing sleep level
    
    def enable_duty_cycling(self, sensors: List[IoTSensor], duty_cycle: float = None):
        """
        Implement duty cycling for energy optimization
        """
        if duty_cycle is not None:
            self.duty_cycle = duty_cycle
            
        for sensor in sensors:
            sensor.duty_cycle = self.duty_cycle
        logger.info(f"Duty cycling enabled: {self.duty_cycle*100}% active time")
    
    def enable_adaptive_duty_cycling(self, enabled: bool = True):
        """Enable or disable adaptive duty cycling based on activity"""
        self.adaptive_duty_cycling = enabled
        self.progressive_sleep = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"Adaptive duty cycling {status}")
        logger.info(f"Progressive sleep mode {status}")
        
        if enabled:
            # Reset counters and sleep level
            self.inactivity_counter = 0
            self.current_sleep_level = 0
    
    def update_optimization_params(self, sensors: List[IoTSensor], duty_cycle: float = None, aggregation_factor: float = None):
        """
        Update optimization parameters in real-time
        """
        updated = False
        
        if duty_cycle is not None and 0.1 <= duty_cycle <= 1.0:
            self.duty_cycle = duty_cycle
            for sensor in sensors:
                sensor.duty_cycle = duty_cycle
            updated = True
            logger.info(f"Duty cycle updated: {duty_cycle*100:.1f}% active time")
            
        if aggregation_factor is not None and 0.1 <= aggregation_factor <= 1.0:
            self.aggregation_factor = aggregation_factor
            updated = True
            logger.info(f"Aggregation factor updated: {(1-aggregation_factor)*100:.1f}% power reduction")
            
        return updated
    
    def update_sleep_mode(self, sensors: List[IoTSensor], readings: List[SensorReading]) -> float:
        """
        Update sleep mode based on sensor activity
        Returns the power saved from sleep mode
        """
        if not self.progressive_sleep:
            return 0.0
            
        # Check for significant changes in sensor readings
        activity_detected = False
        power_saved = 0.0
        
        for reading in readings:
            sensor_id = reading.sensor_id
            current_value = reading.value
            
            # Skip motion sensors which naturally have binary values
            if 'motion' in sensor_id:
                if current_value > 0:  # Motion detected
                    activity_detected = True
                continue
                
            # Check if we have a previous value to compare
            if sensor_id in self.last_sensor_values:
                previous_value = self.last_sensor_values[sensor_id]                # Calculate percent change
                if previous_value != 0:
                    percent_change = abs((current_value - previous_value) / previous_value) * 100
                elif current_value != 0:  # Previous was 0 but current isn't
                    percent_change = 100.0  # Treat as 100% change
                else:
                    percent_change = 0.0  # Both are 0, no change
                
                if percent_change > self.activity_threshold:
                    activity_detected = True
                    logger.debug(f"Activity detected on {sensor_id}: {percent_change:.1f}% change")
            
            # Update last value
            self.last_sensor_values[sensor_id] = current_value
        
        # Update activity counter and sleep level
        if activity_detected:
            # Reset inactivity counter and go to most active level
            self.inactivity_counter = 0
            if self.current_sleep_level > 0:
                self.current_sleep_level = 0
                new_duty_cycle = self.sleep_levels[self.current_sleep_level]
                logger.info(f"Activity detected! Increasing duty cycle to {new_duty_cycle*100:.0f}%")
                
                # Apply new duty cycle to all sensors
                for sensor in sensors:
                    old_duty_cycle = sensor.duty_cycle
                    sensor.duty_cycle = new_duty_cycle
                    # Calculate power saved/increased
                    power_diff = (old_duty_cycle - new_duty_cycle) * sensor.power['sensing'] * 5  # Assuming 5 seconds
                    power_saved -= power_diff  # Negative because we're increasing power
        else:
            # Increment inactivity counter
            self.inactivity_counter += 1
            
            # If we've been inactive for enough cycles, increase sleep level
            if self.inactivity_counter >= self.sleep_level_timeout:
                if self.current_sleep_level < len(self.sleep_levels) - 1:
                    self.current_sleep_level += 1
                    new_duty_cycle = self.sleep_levels[self.current_sleep_level]
                    
                    logger.info(f"No activity for {self.inactivity_counter} cycles - "
                              f"Decreasing duty cycle to {new_duty_cycle*100:.0f}%")
                    
                    # Apply new duty cycle to all sensors
                    for sensor in sensors:
                        old_duty_cycle = sensor.duty_cycle
                        sensor.duty_cycle = new_duty_cycle
                        # Calculate power saved
                        power_diff = (old_duty_cycle - new_duty_cycle) * sensor.power['sensing'] * 5  # Assuming 5 seconds
                        power_saved += power_diff
                
                # Reset counter but keep current sleep level
                self.inactivity_counter = 0
        
        return power_saved
    
    def aggregate_data(self, readings: List[SensorReading]) -> List[SensorReading]:
        """
        Data aggregation to reduce communication overhead
        """
        if not self.optimization_enabled:
            return readings
              # Group readings by sensor type
        grouped_readings = {}
        for reading in readings:
            # Extract sensor type from the end of sensor_id (e.g., 'living_room_01_temp' -> 'temp')
            sensor_type = reading.sensor_id.split('_')[-1]
            if sensor_type not in grouped_readings:
                grouped_readings[sensor_type] = []
            grouped_readings[sensor_type].append(reading)
        
        # Create aggregated readings (average values)
        aggregated = []
        for sensor_type, readings_list in grouped_readings.items():
            if len(readings_list) > 1:
                avg_value = sum(r.value for r in readings_list) / len(readings_list)
                total_power = sum(r.power_consumed for r in readings_list)
                
                aggregated.append(SensorReading(
                    datetime.now(),
                    f"aggregated_{sensor_type}",
                    avg_value,
                    readings_list[0].unit,
                    total_power * self.aggregation_factor  # Power reduction through aggregation
                ))
            else:
                aggregated.extend(readings_list)
        
        return aggregated

class IoTSystem:
    """
    Main IoT System implementing Level 5 architecture
    Features: Sensor networks, Internet connectivity, Cloud processing, Data analytics
    """
    def __init__(self):
        self.sensors = []
        self.communication = MQTTProtocol()
        self.optimizer = EnergyOptimizer()
        self.power_history = []
        self.sensor_readings = []
        self.running = False        # MQTT Client for bi-directional communication
        from mqtt_client import MQTTClient
        self.mqtt_client = MQTTClient("smart_home_main")
        self.mqtt_connected = False
        
        # Email Alert System for abnormal condition detection
        self.email_alert_system = EmailAlertSystem()
        
        # Initialize sensors based on scientific literature
        self._initialize_sensors()
    
    def _initialize_sensors(self):
        """Initialize sensors for Smart Home application"""
        # Temperature and Humidity sensors (DHT22) - 3 locations
        self.sensors.append(TemperatureHumiditySensor("living_room_01", "Living Room"))
        self.sensors.append(TemperatureHumiditySensor("bedroom_01", "Master Bedroom"))
        self.sensors.append(TemperatureHumiditySensor("kitchen_01", "Kitchen"))
        
        # Air quality sensors - 2 locations
        self.sensors.append(AirQualitySensor("air_01", "Living Room"))
        self.sensors.append(AirQualitySensor("air_02", "Kitchen"))
        
        # Light sensors - 3 locations
        self.sensors.append(LightSensor("light_01", "Living Room"))
        self.sensors.append(LightSensor("light_02", "Master Bedroom"))
        self.sensors.append(LightSensor("light_03", "Home Office"))
        
        # Noise sensors - 2 locations
        self.sensors.append(NoiseSensor("noise_01", "Living Room"))
        self.sensors.append(NoiseSensor("noise_02", "Master Bedroom"))
        
        # PIR motion sensors - 2 locations
        self.sensors.append(PIRSensor("pir_01", "Front Door"))
        self.sensors.append(PIRSensor("pir_02", "Back Yard"))
        
        logger.info(f"Initialized {len(self.sensors)} sensors for Smart Home system")
    
    def collect_sensor_data(self) -> List[SensorReading]:
        """Collect data from all sensors and check for abnormal conditions"""
        readings = []
        all_alerts = []
        
        for sensor in self.sensors:
            if isinstance(sensor, TemperatureHumiditySensor):
                # Temperature reading
                temp_reading = sensor.read_temperature()
                readings.append(temp_reading)
                
                # Check for temperature alerts
                temp_alerts = self.email_alert_system.check_sensor_reading(temp_reading)
                for alert in temp_alerts:
                    alert.sensor_location = sensor.location  # Add location info
                all_alerts.extend(temp_alerts)
                
                # Humidity reading
                hum_reading = sensor.read_humidity()
                readings.append(hum_reading)
                
                # Check for humidity alerts
                hum_alerts = self.email_alert_system.check_sensor_reading(hum_reading)
                for alert in hum_alerts:
                    alert.sensor_location = sensor.location  # Add location info
                all_alerts.extend(hum_alerts)
                
            else:
                # Other sensor types
                reading = sensor.read_value()
                readings.append(reading)
                
                # Check for alerts
                alerts = self.email_alert_system.check_sensor_reading(reading)
                for alert in alerts:
                    alert.sensor_location = sensor.location  # Add location info
                all_alerts.extend(alerts)
        
        # Process any alerts found
        if all_alerts:
            emails_sent = self.email_alert_system.process_alerts(all_alerts)
            if emails_sent > 0:
                logger.warning(f"🚨 {len(all_alerts)} alert(s) detected, {emails_sent} email(s) sent")
                for alert in all_alerts:
                    logger.warning(f"   - {alert.alert_type}: {alert.sensor_id} at {alert.sensor_location}")
        
        return readings
    
    def calculate_system_power(self, readings: List[SensorReading], comm_power: float) -> PowerMetrics:
        """Calculate total system power consumption"""
        sensing_power = sum(r.power_consumed for r in readings)
        processing_power = len(readings) * 0.5  # 0.5mW per reading processing
        sleep_power = sum(s.calculate_power_consumption(1.0, 'sleep') for s in self.sensors)
        
        metrics = PowerMetrics(
            sensing_power=sensing_power,
            communication_power=comm_power,
            processing_power=processing_power,
            sleep_power=sleep_power,
            total_power=sensing_power + comm_power + processing_power + sleep_power
        )
        
        return metrics
    
    def run_simulation(self, duration_minutes: int = 60, optimization_enabled: bool = False):
        """
        Run the complete IoT system simulation with real-time plotting
        """
        logger.info(f"Starting IoT simulation for {duration_minutes} minutes")
        logger.info(f"Optimization enabled: {optimization_enabled}")
        
        # Initialize MQTT connection for bi-directional communication
        if self.mqtt_client.connect():
            self.mqtt_connected = True
            logger.info("🔄 MQTT subscriber functionality enabled - listening for external commands")
            
            # Subscribe to control topics for demonstration
            self.mqtt_client.subscribe("demo/commands")
            self.mqtt_client.subscribe("demo/alerts")
        else:
            logger.warning("MQTT connection failed - running in publisher-only mode")
        
        self.optimizer.optimization_enabled = optimization_enabled
        if optimization_enabled:
            self.optimizer.enable_duty_cycling(self.sensors, 0.8)  # 80% duty cycle
        
        self.running = True
        start_time = datetime.now()
        simulation_data = {
            'timestamps': [],
            'power_consumption': [],
            'sensor_readings': [],
            'communication_power': [],
            'optimization_savings': []        }
          # Set up real-time plotting with improved UI and interactive mode
        plt.ion()  # Turn on interactive mode
        
        # Try to use TkAgg backend for better real-time updates, fallback to default if not available
        try:
            import matplotlib
            matplotlib.use('TkAgg')
            print("✅ Using TkAgg backend for optimal real-time display")
        except (ImportError, Exception) as e:
            logger.warning(f"TkAgg backend not available ({e}), using default backend")
            print("⚠️  Using default matplotlib backend - display updates may be slower")
            
        fig = plt.figure(figsize=(15, 10))
        fig.canvas.manager.set_window_title('Smart Home IoT System - Live Simulation')
        
        # Configure matplotlib for real-time updates
        plt.rcParams['figure.raise_window'] = False
        plt.rcParams['interactive'] = True
          # Add title to the figure
        fig.suptitle('SMART HOME IoT SYSTEM - REAL-TIME MONITORING', 
                    fontsize=16, fontweight='bold')
        
        # Add explanatory text at the bottom
        if optimization_enabled:
            status_text = "Energy Optimization: ENABLED - Using data aggregation and duty cycling to reduce power consumption"
        else:
            status_text = "Energy Optimization: DISABLED - System running at full power without optimization"
            
        fig.text(0.5, 0.01, status_text, ha='center', 
                color='green' if optimization_enabled else 'red',
                bbox=dict(facecolor='white', alpha=0.8))
        
        # Create subplots with helpful descriptions
        ax1 = fig.add_subplot(221)  # Power consumption
        ax2 = fig.add_subplot(222)  # Power distribution
        ax3 = fig.add_subplot(223)  # Sensor readings
        ax4 = fig.add_subplot(224)  # Optimization savings
          # Add optimization control sliders (only if optimization is enabled)
        sliders = {}
        if optimization_enabled:
            print("📊 CREATING REAL-TIME OPTIMIZATION CONTROLS...")
            print("   - Duty Cycle Slider (10-100%): Controls sensor active time")
            print("   - Aggregation Factor Slider (10-90%): Controls data compression")
            print("   - These sliders will appear at the bottom of the simulation window")
            print("   - Move sliders during simulation to see immediate power impact!")
            
            # Reserve space for sliders
            plt.subplots_adjust(bottom=0.15)
            
            # Add duty cycle slider
            duty_ax = plt.axes([0.2, 0.08, 0.65, 0.03])
            duty_slider = Slider(
                ax=duty_ax,
                label='Duty Cycle (%)',
                valmin=10,
                valmax=100,
                valinit=self.optimizer.duty_cycle * 100,
                color='lightgreen'
            )
            
            # Add aggregation slider
            agg_ax = plt.axes([0.2, 0.04, 0.65, 0.03])
            agg_slider = Slider(
                ax=agg_ax,
                label='Aggregation Factor (%)',
                valmin=10,
                valmax=90,
                valinit=(1-self.optimizer.aggregation_factor) * 100,
                color='lightblue'
            )
            
            sliders['duty_cycle'] = duty_slider
            sliders['aggregation'] = agg_slider
            
            # Add explanation text for sliders
            plt.figtext(0.2, 0.12, "Real-time Power Optimization Controls:", 
                      fontsize=12, fontweight='bold', ha='left')
            plt.figtext(0.89, 0.08, "Higher = More Active Time", 
                      fontsize=9, fontweight='normal', ha='left', color='gray')
            plt.figtext(0.89, 0.04, "Higher = More Aggregation", 
                      fontsize=9, fontweight='normal', ha='left', color='gray')
            
            print("✅ Real-time optimization controls created successfully!")
            print("   Initial settings:")
            print(f"   - Duty Cycle: {self.optimizer.duty_cycle*100:.0f}%")
            print(f"   - Aggregation Factor: {(1-self.optimizer.aggregation_factor)*100:.0f}%")
          # Add helpful tooltips to each plot
        ax1_text = "This graph shows real-time power consumption.\nLower values are better for battery life."
        ax2_text = "This pie chart shows how power is distributed\nacross different system components."
        ax3_text = "These are live sensor readings from the\nfield and greenhouse sensors."
        ax4_text = "This shows energy savings from optimization.\nHigher values indicate more efficient operation."
        
        # Position the tooltips
        ax1.text(0.5, 0.02, ax1_text, transform=ax1.transAxes, ha='center', va='bottom',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.7))
        
        ax2.text(0.5, 0.02, ax2_text, transform=ax2.transAxes, ha='center', va='bottom',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.7))
        
        ax3.text(0.5, 0.02, ax3_text, transform=ax3.transAxes, ha='center', va='bottom',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.7))
        
        ax4.text(0.5, 0.02, ax4_text, transform=ax4.transAxes, ha='center', va='bottom',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.7))
        
        # Initialize plot lines with better styling
        power_line, = ax1.plot([], [], 'b-', label='Total Power', linewidth=2)
        comm_line, = ax1.plot([], [], 'r--', label='Communication Power', linewidth=2)
        ax1.set_title('Power Consumption Over Time', fontweight='bold')
        ax1.set_xlabel('Time (seconds)')
        ax1.set_ylabel('Power (mW)')
        ax1.grid(True)
        ax1.legend(loc='upper left')
        
        # Initialize pie chart with explanations
        pie_labels = ['Sensing\n(data collection)', 'Communication\n(sending data)', 
                     'Processing\n(data analysis)', 'Sleep\n(power saving)']
        pie_colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        pie_data = [1, 1, 1, 1]  # Start with equal values
        pie = ax2.pie(pie_data, labels=pie_labels, colors=pie_colors, autopct='%1.1f%%',
                     textprops={'fontsize': 9})
        ax2.set_title('Power Distribution by Component', fontweight='bold')
        
        # Initialize sensor readings plot with better legend
        sensor_lines = {}
        ax3.set_title('Sensor Readings Over Time', fontweight='bold')
        ax3.set_xlabel('Time (seconds)')
        ax3.set_ylabel('Sensor Values')
        ax3.grid(True)
        
        # Add sensor type descriptions in the corner
        sensor_desc = "SENSOR TYPES:\nTemp: Temperature (°C)\nHum: Humidity (%)\nAir: Air Quality (AQI)\nLight: Light Level (lux)\nNoise: Sound Level (dB)"
        ax3.text(0.02, 0.98, sensor_desc, transform=ax3.transAxes, 
                va='top', ha='left', fontsize=8,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.7))
          # Initialize optimization plot with explanatory text
        opt_line, = ax4.plot([], [], 'g-', label='Power Savings', linewidth=2)
        
        if optimization_enabled:
            ax4.set_title('Energy Optimization Savings', fontweight='bold')
            ax4.text(0.5, 0.5, 'Collecting data...\nSavings will appear here', 
                    ha='center', va='center', transform=ax4.transAxes,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.5))
        else:
            ax4.set_title('Energy Optimization Disabled', fontweight='bold')
            ax4.text(0.5, 0.5, 'Enable optimization\nto see potential savings', 
                    ha='center', va='center', transform=ax4.transAxes,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.5))
        
        ax4.set_xlabel('Time (seconds)')
        ax4.set_ylabel('Power Savings (mW)')
        ax4.grid(True)
        ax4.legend(loc='upper left')
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # Make room for title and footer
        
        # Display helpful information about real-time updates
        print("🎯 REAL-TIME DISPLAY CONFIGURATION:")
        print("   - Plot updates: Every cycle (0.2 second intervals)")
        print("   - Backend: TkAgg (optimized for real-time display)")
        print("   - Interactive mode: Enabled")
        print("   - The graphs will update in real-time showing live sensor data!")
        print("   - Look for the 🔄 symbol in the title indicating live updates")
        print("")
        
        cycle_count = 0
        total_comm_power = 0.0
        baseline_power = None  # Store baseline power for comparison
        plot_update_thread = None  # For non-blocking plot updates
        
        try:
            while self.running and (datetime.now() - start_time).seconds < duration_minutes * 60:
                cycle_start = datetime.now()
                
                # Collect sensor data
                readings = self.collect_sensor_data()
                
                # Store baseline power if not set
                if baseline_power is None:
                    baseline_power = sum(r.power_consumed for r in readings)
                
                # Apply optimization if enabled
                if optimization_enabled:
                    original_count = len(readings)
                    readings = self.optimizer.aggregate_data(readings)
                    logger.info(f"Data aggregation: {original_count} -> {len(readings)} readings")
                  # Simulate communication with distance-based power calculation
                comm_power_cycle = 0.0
                for reading in readings:
                    # Extract base sensor ID (remove _temp, _hum, etc.)
                    base_sensor_id = reading.sensor_id.split('_')[0]
                    # Find matching sensor
                    matching_sensor = next((s for s in self.sensors if s.sensor_id == base_sensor_id), None)
                    
                    payload = {
                        'sensor_id': reading.sensor_id,
                        'value': reading.value,
                        'unit': reading.unit,
                        'timestamp': reading.timestamp.isoformat(),
                        'location': matching_sensor.location if matching_sensor else "Unknown"
                    }
                    
                    # Pass sensor location for distance-based power calculation
                    sensor_location = matching_sensor.location if matching_sensor else None
                    success, power = self.communication.publish_message(
                        f"sensors/{reading.sensor_id}", 
                        payload, 
                        sensor_location=sensor_location
                    )
                    comm_power_cycle += power
                
                total_comm_power += comm_power_cycle
                
                # Calculate power metrics
                power_metrics = self.calculate_system_power(readings, comm_power_cycle)
                
                # Update simulation data
                simulation_data['timestamps'].append(cycle_start)
                simulation_data['power_consumption'].append(power_metrics.total_power)
                simulation_data['communication_power'].append(comm_power_cycle)
                simulation_data['sensor_readings'].extend(readings)
                
                # Calculate optimization savings
                if optimization_enabled:
                    current_power = power_metrics.total_power
                    savings = baseline_power - current_power
                    simulation_data['optimization_savings'].append(savings)
                  # Update plots in real-time
                # Power consumption plot with elapsed time indicator
                elapsed_seconds = (datetime.now() - start_time).seconds
                time_remaining = max(0, duration_minutes * 60 - elapsed_seconds)
                  # Update progress information with real-time status
                fig.suptitle(
                    f'SMART HOME IoT SYSTEM - REAL-TIME MONITORING 🔄\n'
                    f'Time Elapsed: {elapsed_seconds} sec | Time Remaining: {time_remaining} sec | Cycle: {cycle_count} | Status: LIVE',
                    fontsize=14, fontweight='bold'
                )
                
                # Power consumption plot
                power_line.set_data(range(len(simulation_data['power_consumption'])), 
                                  simulation_data['power_consumption'])
                comm_line.set_data(range(len(simulation_data['communication_power'])), 
                                 simulation_data['communication_power'])
                ax1.relim()
                ax1.autoscale_view()
                
                # Add average power line
                if len(simulation_data['power_consumption']) > 1:
                    avg_power = np.mean(simulation_data['power_consumption'])
                    ax1.axhline(y=avg_power, color='g', linestyle='--', alpha=0.5)
                    ax1.text(0, avg_power, f' Avg: {avg_power:.1f} mW', 
                           verticalalignment='bottom', fontsize=9)
                
                # Power distribution pie chart
                ax2.clear()
                pie_data = [
                    max(0.1, power_metrics.sensing_power),
                    max(0.1, power_metrics.communication_power),
                    max(0.1, power_metrics.processing_power),
                    max(0.1, power_metrics.sleep_power)
                ]
                total = sum(pie_data)
                if total > 0:
                    pie_data = [x/total for x in pie_data]  # Normalize
                    
                    # Updated labels with percentages and values
                    pie_labels = [
                        f'Sensing\n{power_metrics.sensing_power:.1f} mW',
                        f'Communication\n{power_metrics.communication_power:.1f} mW',
                        f'Processing\n{power_metrics.processing_power:.1f} mW',
                        f'Sleep\n{power_metrics.sleep_power:.1f} mW'
                    ]
                    
                    ax2.pie(pie_data, labels=pie_labels, colors=pie_colors, autopct='%1.1f%%',
                           textprops={'fontsize': 9})
                    
                ax2.set_title(f'Power Distribution\nTotal: {power_metrics.total_power:.1f} mW', fontweight='bold')
                
                # Add tooltip explanation text back after clearing
                ax2_text = "This pie chart shows how power is distributed\nacross different system components."
                ax2.text(0.5, 0.02, ax2_text, transform=ax2.transAxes, ha='center', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.7))
                
                # Sensor readings plot with improved visualization
                ax3.clear()
                
                # Define colors for different sensor types for consistency
                sensor_colors = {
                    'temp': 'red',
                    'hum': 'blue',
                    'air': 'green',
                    'light': 'orange',
                    'noise': 'purple'
                }
                
                for sensor_type in set(r.sensor_id.split('_')[1] for r in readings):
                    sensor_readings = [r.value for r in readings if sensor_type in r.sensor_id]
                    if sensor_readings:
                        if sensor_type not in sensor_lines:
                            sensor_lines[sensor_type] = []
                        sensor_lines[sensor_type].extend(sensor_readings)
                        
                        # Use consistent colors and add units
                        color = sensor_colors.get(sensor_type, 'gray')
                        
                        # Format label based on sensor type
                        if sensor_type == 'temp':
                            label = f"Temperature (°C) - {sensor_readings[-1]:.1f}°C"
                        elif sensor_type == 'hum':
                            label = f"Humidity (%) - {sensor_readings[-1]:.1f}%"
                        elif sensor_type == 'air':
                            label = f"Air Quality (AQI) - {sensor_readings[-1]:.1f}"
                        elif sensor_type == 'light':
                            label = f"Light Level (lux) - {sensor_readings[-1]:.1f} lux"
                        else:
                            label = f"{sensor_type.capitalize()} - {sensor_readings[-1]:.1f} dB"
                            
                        ax3.plot(sensor_lines[sensor_type], label=label, color=color)
                
                ax3.set_title(f'Sensor Readings - Last Update: {datetime.now().strftime("%H:%M:%S")}', 
                             fontweight='bold')
                ax3.set_xlabel('Reading Number')
                ax3.set_ylabel('Sensor Values (with units)')
                ax3.grid(True)
                ax3.legend(loc='upper left', fontsize=8)
                
                # Add tooltip explanation text back after clearing
                ax3_text = "These are live sensor readings from the\nfield and greenhouse sensors."
                ax3.text(0.5, 0.02, ax3_text, transform=ax3.transAxes, ha='center', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.7))
                
                # Optimization savings plot
                if optimization_enabled and simulation_data['optimization_savings']:
                    opt_line.set_data(range(len(simulation_data['optimization_savings'])), 
                                    simulation_data['optimization_savings'])
                    ax4.relim()
                    ax4.autoscale_view()
                    
                    # Calculate total and average savings
                    total_savings = sum(simulation_data['optimization_savings'])
                    avg_savings = np.mean(simulation_data['optimization_savings'])
                    
                    ax4.set_title(f'Energy Optimization Savings\n'
                                f'Total: {total_savings:.2f} mW | Avg: {avg_savings:.2f} mW', 
                                fontweight='bold')
                    
                    # Add efficiency percentage
                    if simulation_data['power_consumption']:
                        total_power = sum(simulation_data['power_consumption'])
                        efficiency = (total_savings / total_power) * 100 if total_power > 0 else 0
                        ax4.text(0.02, 0.95, f'Efficiency: {efficiency:.1f}%', transform=ax4.transAxes,
                               ha='left', va='top',
                               bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.5))
                elif not optimization_enabled:
                    # If optimization is disabled, show a message
                    ax4.clear()
                    ax4.text(0.5, 0.5, 'Energy Optimization is Disabled\nEnable optimization to see potential savings', 
                           ha='center', va='center', transform=ax4.transAxes,
                           bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.5))
        
                # Handle slider updates for real-time optimization control
                if optimization_enabled and sliders:
                    # Check if sliders have been moved and update optimization parameters
                    new_duty_cycle = sliders['duty_cycle'].val / 100.0
                    new_agg_factor = 1.0 - (sliders['aggregation'].val / 100.0)  # Convert to power reduction factor
                    
                    # Update optimization parameters if they changed
                    if (abs(new_duty_cycle - self.optimizer.duty_cycle) > 0.01 or 
                        abs(new_agg_factor - self.optimizer.aggregation_factor) > 0.01):
                        
                        print(f"🎛️  SLIDER UPDATE DETECTED:")
                        print(f"   - Duty Cycle: {self.optimizer.duty_cycle*100:.0f}% → {new_duty_cycle*100:.0f}%")
                        print(f"   - Aggregation Factor: {(1-self.optimizer.aggregation_factor)*100:.0f}% → {(1-new_agg_factor)*100:.0f}%")
                        
                        self.optimizer.update_optimization_params(
                            self.sensors, 
                            duty_cycle=new_duty_cycle,
                            aggregation_factor=new_agg_factor
                        )
                        
                        # Update status text to show current settings
                        status_text = (f"Energy Optimization: ENABLED - "
                                     f"Duty Cycle: {new_duty_cycle*100:.0f}% | "
                                     f"Aggregation: {(1-new_agg_factor)*100:.0f}% savings")
                        fig.text(0.5, 0.01, status_text, ha='center', 
                                color='green', transform=fig.transFigure,
                                bbox=dict(facecolor='white', alpha=0.8))                # Update plots every cycle for real-time updates
                try:
                    # Force immediate figure update
                    fig.canvas.draw()
                    fig.canvas.flush_events()
                    plt.pause(0.01)  # Small pause to allow GUI updates
                    
                    # Print update confirmation every 10 cycles to avoid spam
                    if cycle_count % 10 == 0:
                        print(f"📊 Display updated - Cycle {cycle_count} | Power: {power_metrics.total_power:.1f} mW")
                        
                except Exception as e:
                    logger.warning(f"Plot update warning: {e}")
                    # Continue even if plot update fails
                
                cycle_count += 1
                logger.info(f"Cycle {cycle_count}: Total Power = {power_metrics.total_power:.2f} mW")
                
                # Wait for next cycle with optimized interval for real-time display
                time.sleep(0.2)  # Faster updates for better real-time visualization
                
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
            self.running = False
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            self.running = False
        finally:
            # Ensure cleanup happens
            self.running = False
            try:
                plt.ioff()  # Turn off interactive mode
                plt.close('all')  # Close all figures to prevent hanging
            except Exception as e:
                logger.warning(f"Cleanup warning: {e}")
          # Cleanup MQTT connection
        if self.mqtt_connected:
            self.mqtt_client.disconnect()
            logger.info("🔌 MQTT connection closed")
        
        # Generate final report
        self._generate_simulation_report(simulation_data, duration_minutes, optimization_enabled)
        
        return simulation_data
        
    def _generate_simulation_report(self, data: dict, duration: int, optimization: bool):
        """Generate comprehensive simulation report with enhanced visualizations"""
        
        # Create a figure with multiple subplots and better styling
        plt.style.use('default')  # Use default style instead of seaborn which might not be installed
        
        # Create a report window with clear title
        plt.figure(figsize=(16, 10))
        plt.suptitle("SIMULATION COMPLETE", fontsize=18, fontweight='bold', color='green')
        plt.figtext(0.5, 0.92, "Smart Home IoT System - Simulation Results Report", fontsize=14, ha='center')
        
        # Add power saving features explanation if optimization was enabled
        if optimization:
            opt_methods = [
                "Adaptive Power Transmission: Adjusts signal power based on distance",
                "Progressive Sleep Mode: Reduces duty cycle during inactive periods",
                "Data Aggregation: Combines similar readings to reduce transmission count",
                "Batch Transmission: Groups messages to minimize connection overhead"
            ]
            
            plt.figtext(0.5, 0.86, "Power Optimization Methods Used:", fontsize=11, ha='center',
                      fontweight='bold', color='green')
            
            for i, method in enumerate(opt_methods):
                plt.figtext(0.5, 0.845 - i*0.015, f"• {method}", fontsize=10, ha='center')
                
        # Add explanatory text
        report_info = (
            f"Duration: {duration} minute{'s' if duration > 1 else ''} | "
            f"Optimization: {'Enabled' if optimization else 'Disabled'} | "
            f"Total Readings: {len(data['sensor_readings'])} | "
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        plt.figtext(0.5, 0.89, report_info, fontsize=10, ha='center',
                  bbox=dict(facecolor='lightblue', alpha=0.3, boxstyle='round,pad=0.5'))
        
        # Add explanatory text about the simulation
        sim_explanation = (
            "This report shows the results of your IoT simulation. "
            "The Smart Home system monitors temperature, humidity, air quality, light levels, "
            "and motion to support home automation and security. Energy optimization techniques "
            "help extend battery life and reduce power consumption."
        )
        plt.figtext(0.5, 0.85, sim_explanation, fontsize=9, ha='center', style='italic')
        
        # Create main report figure with better styling
        fig = plt.figure(figsize=(20, 15))
        
        # Plot 1: Power consumption over time with better formatting
        plt.subplot(3, 2, 1)
        timestamps = [t.strftime('%H:%M:%S') for t in data['timestamps']]
        plt.plot(data['power_consumption'], 'b-', linewidth=2, label='Total Power')
        plt.plot(data['communication_power'], 'r--', linewidth=1.5, label='Communication Power')
        
        # Add average line
        avg_power = np.mean(data['power_consumption'])
        plt.axhline(y=avg_power, color='g', linestyle='--', alpha=0.7, label=f'Avg: {avg_power:.2f} mW')
        
        plt.xlabel('Time (seconds)', fontsize=10)
        plt.ylabel('Power (mW)', fontsize=10)
        plt.title('Power Consumption Over Time', fontsize=12, fontweight='bold')
        plt.legend(fontsize=9)
        plt.grid(True, alpha=0.3)
        
        # Annotate key points
        max_power = max(data['power_consumption'])
        max_index = data['power_consumption'].index(max_power)
        plt.annotate(f'Peak: {max_power:.2f} mW', 
                   xy=(max_index, max_power),
                   xytext=(max_index+2, max_power+5),
                   arrowprops=dict(facecolor='black', shrink=0.05, alpha=0.7),
                   fontsize=8)
        
        # Plot 2: Power distribution pie chart with detailed labels
        plt.subplot(3, 2, 2)
        avg_power = np.mean(data['power_consumption'])
        avg_comm = np.mean(data['communication_power'])
        avg_sensing = avg_power - avg_comm
        
        labels = [f'Sensing\n{avg_sensing*0.6:.2f} mW', 
                 f'Communication\n{avg_comm:.2f} mW', 
                 f'Processing\n{avg_power*0.1:.2f} mW', 
                 f'Sleep\n{avg_power*0.1:.2f} mW']
                 
        sizes = [avg_sensing*0.6, avg_comm, avg_power*0.1, avg_power*0.1]
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        explode = (0.1, 0, 0,  0)  # Explode the sensing slice
        
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
               startangle=90, explode=explode, shadow=True)
        plt.title('Average Power Distribution', fontsize=12, fontweight='bold')
        
        # Plot 3: Sensor readings correlation with better styling
        plt.subplot(3, 2, 3)
        temp_readings = [r.value for r in data['sensor_readings'] if 'temp' in r.sensor_id]
        humidity_readings = [r.value for r in data['sensor_readings'] if 'hum' in r.sensor_id]
        
        if temp_readings and humidity_readings:
            # Limit to same length if different
            min_length = min(len(temp_readings), len(humidity_readings))
            temp_readings = temp_readings[:min_length]
            humidity_readings = humidity_readings[:min_length]
            
            plt.scatter(temp_readings, humidity_readings, alpha=0.7, c='green', 
                      s=50, edgecolors='white', linewidths=0.5)
            plt.xlabel('Temperature (°C)', fontsize=10)
            plt.ylabel('Humidity (%)', fontsize=10)
            plt.title('Temperature vs Humidity Correlation', fontsize=12, fontweight='bold')
            plt.grid(True, alpha=0.3)
            
            # Add trend line with equation
            z = np.polyfit(temp_readings, humidity_readings, 1)
            p = np.poly1d(z)
            plt.plot(temp_readings, p(temp_readings), "r--", alpha=0.8)
            
            # Add correlation coefficient
            correlation = np.corrcoef(temp_readings, humidity_readings)[0,1]
            plt.annotate(f'Correlation: {correlation:.2f}\nEquation: y = {z[0]:.2f}x + {z[1]:.2f}', 
                       xy=(0.05, 0.95), xycoords='axes fraction',
                       ha='left', va='top',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
            
            # Highlight the relationship
            plt.figtext(0.25, 0.38, "As temperature increases, humidity decreases - an inverse relationship", 
                      fontsize=8, style='italic', ha='center',
                      bbox=dict(facecolor='lightyellow', alpha=0.5))
        
        # Plot 4: Optimization savings with clear metrics
        plt.subplot(3, 2, 4)
        if optimization and data['optimization_savings']:
            plt.plot(data['optimization_savings'], 'g-', linewidth=2, label='Power Savings')
            
            # Add moving average for trend
            window_size = min(10, len(data['optimization_savings']))
            if window_size > 0:
                moving_avg = np.convolve(data['optimization_savings'], 
                                       np.ones(window_size)/window_size, 
                                       mode='valid')
                plt.plot(moving_avg, 'r--', label='Moving Average')
            
            plt.xlabel('Time (seconds)', fontsize=10)
            plt.ylabel('Power Savings (mW)', fontsize=10)
            plt.title('Energy Optimization Savings', fontsize=12, fontweight='bold')
            plt.grid(True, alpha=0.3)
            plt.legend(fontsize=9)
            
            # Add summary statistics
            total_savings = np.sum(data['optimization_savings'])
            avg_savings = np.mean(data['optimization_savings'])
            max_savings = np.max(data['optimization_savings'])
            
            stats_text = (f"Total Savings: {total_savings:.2f} mW\n"
                        f"Average Savings: {avg_savings:.2f} mW\n"
                        f"Peak Savings: {max_savings:.2f} mW\n"
                        f"Efficiency: {(total_savings/np.sum(data['power_consumption'])*100):.1f}%")
            
            plt.annotate(stats_text, xy=(0.97, 0.05), xycoords='axes fraction',
                       ha='right', va='bottom',
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.5))
        else:
            plt.text(0.5, 0.5, 'Optimization Disabled\nRun with optimization enabled to see potential savings', 
                    ha='center', va='center', transform=plt.gca().transAxes,
                    fontsize=12, fontweight='bold',
                    bbox=dict(facecolor='lightgray', alpha=0.5))
        
        # Plot 5: Sensor readings over time with better color coding and labels
        plt.subplot(3, 2, 5)
        sensor_types = set(r.sensor_id.split('_')[1] for r in data['sensor_readings'])
        
        # Define colors and labels for different sensor types
        sensor_colors = {
            'temp': 'red',
            'hum': 'blue',
            'air': 'green',
            'light': 'orange',
            'noise': 'purple'
        }
        
        sensor_labels = {
            'temp': 'Temperature (°C)',
            'hum': 'Humidity (%)',
            'air': 'Air Quality (AQI)',
            'light': 'Light Level (lux)',
            'noise': 'Sound Level (dB)'
        }
        
        for sensor_type in sensor_types:
            readings = [r.value for r in data['sensor_readings'] 
                       if sensor_type in r.sensor_id]
            if readings:
                color = sensor_colors.get(sensor_type, 'gray')

                label = sensor_labels.get(sensor_type, sensor_type.capitalize())
                plt.plot(readings, label=label, color=color, linewidth=1.5)
                
                # Add summary stat for each sensor
                if len(readings) > 0:
                    avg_reading = np.mean(readings)
                    plt.annotate(f'Avg {label}: {avg_reading:.1f}', 
                               xy=(len(readings)-1, readings[-1]),
                               xytext=(len(readings)-5, readings[-1]),
                               fontsize=8, color=color)
        
        plt.xlabel('Reading Number', fontsize=10)
        plt.ylabel('Sensor Values', fontsize=10)
        plt.title('Sensor Readings Over Time', fontsize=12, fontweight='bold')
        plt.legend(fontsize=9)
        plt.grid(True, alpha=0.3)
        
        # Plot 6: Power optimization metrics
        plt.subplot(3, 2, 6)
        if optimization:
            efficiency = [(savings/power)*100 if power > 0 else 0 
                         for savings, power in zip(data['optimization_savings'], 
                                                data['power_consumption'])]
            plt.plot(efficiency, 'purple', linewidth=2, label='Efficiency')
            plt.axhline(y=np.mean(efficiency), color='r', linestyle='--', 
                       label=f'Avg: {np.mean(efficiency):.1f}%')
            plt.xlabel('Time (seconds)', fontsize=10)
            plt.ylabel('Efficiency (%)', fontsize=10)
            plt.title('Power Optimization Efficiency', fontsize=12, fontweight='bold')
            plt.legend(fontsize=9)
            plt.grid(True, alpha=0.3)
            
            # Add helpful annotation
            plt.figtext(0.75, 0.12, 
                      "Higher efficiency percentage means more\npower saved through optimization techniques", 
                      fontsize=8, style='italic', ha='center',
                      bbox=dict(facecolor='lightyellow', alpha=0.5))
        else:
            plt.text(0.5, 0.5, 'Efficiency metrics available\nwith optimization enabled', 
                    ha='center', va='center', transform=plt.gca().transAxes,
                    fontsize=12, fontweight='bold',
                    bbox=dict(facecolor='lightgray', alpha=0.5))
            plt.title('Power Efficiency Metrics', fontsize=12, fontweight='bold')
            plt.grid(True, alpha=0.3)
        
        plt.tight_layout(rect=[0, 0, 1, 0.9])  # Make room for title
        
        # Save the plot with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_filename = f'iot_simulation_report_{timestamp}.png'
        plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
        
        # Display the plot
        plt.show()
        
        # Generate detailed statistics with better formatting
        print("\n" + "="*80)
        print(" "*20 + "IoT SYSTEM SIMULATION REPORT")
        print("="*80)
        
        # Basic statistics
        print(f"\nSIMULATION SUMMARY:")
        print(f"- Duration: {duration} minute{'s' if duration > 1 else ''}")
        print(f"- Optimization: {'Enabled' if optimization else 'Disabled'}")
        print(f"- Total Sensor Readings: {len(data['sensor_readings'])}")
        print(f"- Average Power Consumption: {np.mean(data['power_consumption']):.2f} mW")
        print(f"- Total Energy Consumed: {np.sum(data['power_consumption'])*5/1000/3600:.4f} Wh")
        print(f"- Communication Messages: {self.communication.message_count}")
        print(f"- Communication Retries: {self.communication.retry_count}")
        print(f"- Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Power distribution
        print("\nPOWER DISTRIBUTION:")
        print(f"  Sensing:       {avg_sensing*0.6:.2f} mW ({avg_sensing*0.6/avg_power*100:.1f}%)")
        print(f"  Communication: {avg_comm:.2f} mW ({avg_comm/avg_power*100:.1f}%)")
        print(f"  Processing:    {avg_power*0.1:.2f} mW ({avg_power*0.1/avg_power*100:.1f}%)")
        print(f"  Sleep:         {avg_power*0.1:.2f} mW ({avg_power*0.1/avg_power*100:.1f}%)")
        
        # Sensor statistics with better formatting
        print("\nSENSOR STATISTICS:")
        for sensor_type in sensor_types:
            readings = [r.value for r in data['sensor_readings'] 
                       if sensor_type in r.sensor_id]
            if readings:
                print(f"\n  {sensor_labels.get(sensor_type, sensor_type.capitalize())}:")
                print(f"    Average: {np.mean(readings):.2f}")
                print(f"    Min:     {np.min(readings):.2f}")
                print(f"    Max:     {np.max(readings):.2f}")
                print(f"    Std Dev: {np.std(readings):.2f}")
    
        # Optimization results (move this block inside the method, not at the top level)
        if optimization and data['optimization_savings']:
            total_savings = np.sum(data['optimization_savings'])
            avg_savings = np.mean(data['optimization_savings'])
            print("\nOptimization Results:")
            print(f"  Total Power Savings: {total_savings:.2f} mW·cycles")
            print(f"  Average Savings per Cycle: {avg_savings:.2f} mW")
            print(f"  Optimization Efficiency: {(total_savings/np.sum(data['power_consumption'])*100):.1f}%")
            # Calculate correlation between savings and power
            correlation = np.corrcoef(data['optimization_savings'], 
                                    data['power_consumption'])[0,1]
            print(f"  Power-Savings Correlation: {correlation:.2f}")
        print("\n" + "="*80)
        print("Report generated successfully!")
        print("="*80)
        
        # Keep plots open until user closes them
        input("\nPress Enter to exit...")