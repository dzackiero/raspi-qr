import json
import sys
import cv2
import paho.mqtt.client as mqtt
from pyzbar import pyzbar


def init_mqtt():
    mqtt_host = "ae1e003b.ala.asia-southeast1.emqxsl.com"
    mqtt_port = 8883
    mqtt_username = "react-web"
    mqtt_password = "react-web"
    mqtt_topic = "lockit"

    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(mqtt_username, mqtt_password)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.tls_set(ca_certs="cert.crt")
    mqtt_client.tls_insecure_set(False)

    try:
        mqtt_client.connect(mqtt_host, mqtt_port, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")

    return mqtt_client


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))


def on_message(client, userdata, msg):
    print(f"Message received: {msg.payload.decode()}")


def publish_message(client, message, topic):
    client.publish(topic, message)


def parse_qr_code(input):
    parts = input.split("-")

    if len(parts) != 3:
        raise ValueError('Invalid input format. Expected format is "userId-BoxId-pin"')

    user_id = parts[0]
    id = parts[1]
    pin = parts[2]

    parsed_data = {"user_id": user_id, "id": id, "pin": pin, "state": True}

    json_string = json.dumps(parsed_data)
    return json_string


def scan_qr_code():
    cap = cv2.VideoCapture(0)
    mqtt_client = init_mqtt()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        decoded_objects = pyzbar.decode(frame)
        for obj in decoded_objects:
            qr_data = obj.data.decode("utf-8")
            try:
                parsed_data = parse_qr_code(qr_data)
                print("QR Code detected:", qr_data)
                publish_message(mqtt_client, parsed_data, "lockit")
                return
            except ValueError as e:
                print(f"Error parsing QR code: {e}")

        cv2.imshow("QR Code Scanner", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    scan_qr_code()
