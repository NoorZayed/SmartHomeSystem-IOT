
class MQTTClient:
   
    def __init__(self, client_id):
        """Initialize the MQTT client with a unique identifier"""
        self.client_id = client_id
        self.connected = False
        self.subscribed_topics = []
        
    def connect(self):
        """
        Establish connection to the MQTT broker (simulated)
        In a real implementation, would connect to an actual MQTT broker
        """
        # Simulate successful connection in test environment
        self.connected = True
        print(f"MQTT Client '{self.client_id}' connected successfully (simulation)")
        return True
        
    def disconnect(self):
        """
        Disconnect from the MQTT broker
        Properly closes the connection to free resources
        """
        if self.connected:
            self.connected = False
            print(f"MQTT Client '{self.client_id}' disconnected")
        
    def subscribe(self, topic):
        """
        Subscribe to an MQTT topic to receive messages
        Topics use hierarchical structure like 'home/livingroom/temperature'
        """
        if self.connected:
            self.subscribed_topics.append(topic)
            print(f"Subscribed to topic: {topic}")
            return True
        return False
        
    def publish(self, topic, payload):
        """
        Publish a message to an MQTT topic
        Messages are distributed to all clients subscribed to that topic
        """
        if self.connected:
            print(f"Published to topic: {topic}")
            return True
        return False