import paho.mqtt.client as mqtt
import json
import socket
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MQTT configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC = "job/create"
PAYLOAD = json.dumps({
    "ticket": "18593058373-3434",
    "file": "test.jsonld"
})

try:
    # Create and connect client
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Start network loop (non-blocking)
    client.loop_start()

    # Publish the message
    result = client.publish(TOPIC, PAYLOAD)
    status = result[0]

    if status == mqtt.MQTT_ERR_SUCCESS:
        logger.info(f"✅ Message sent to topic `{TOPIC}`")
    else:
        logger.error(f"❌ Failed to send message (status {status})")

    # Stop loop and disconnect
    client.loop_stop()
    client.disconnect()

except ConnectionRefusedError:
    logger.error("Connection refused – is the MQTT broker running?")
except socket.gaierror:
    logger.error("Invalid MQTT broker address.")
except Exception as e:
    logger.exception(f"Unexpected error occurred: {e}")