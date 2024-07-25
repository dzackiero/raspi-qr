import json
import sys
import cv2
import paho.mqtt.client as mqtt
from pyzbar import pyzbar
import tkinter as tk
from tkinter import messagebox


class QRScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QR Code Scanner")
        self.root.geometry("800x800")
        self.root.configure(bg="#ffffff")

        self.initUI()
        self.initMQTT()

    def initUI(self):
        # Title
        title_label = tk.Label(
            self.root,
            text="Welcome to LockIt, press 'Start Scanning' or 'Enter' to scan your QR Code",
            font=("Helvetica", 18),
            bg="#ffffff",
            fg="#333333",
        )
        title_label.pack(pady=20)

        # Start Scanning Button
        self.start_button = tk.Button(
            self.root,
            text="Start Scanning",
            font=("Helvetica", 16),
            bg="#ff8c00",
            fg="white",
            height=2,
            command=self.show_scanner,
        )
        self.start_button.pack(pady=20)

        # Input Code Button
        self.input_code_button = tk.Button(
            self.root,
            text="Input Your Code",
            font=("Helvetica", 16),
            bg="#00796b",
            fg="white",
            height=2,
            command=self.show_input_form,
        )
        self.input_code_button.pack(pady=20)

        # Scanner Frame
        self.scanner_frame = tk.Label(self.root, bg="#e0e0e0", width=640, height=640)
        self.scanner_frame.pack(pady=20)
        self.scanner_frame.pack_forget()

        # Input Form
        self.code_input = tk.Entry(self.root, font=("Helvetica", 16))
        self.code_input.pack(pady=20)
        self.code_input.pack_forget()

        self.submit_button = tk.Button(
            self.root,
            text="Submit",
            font=("Helvetica", 16),
            bg="#ff8c00",
            fg="white",
            height=2,
            command=self.submit_code,
        )
        self.submit_button.pack(pady=20)
        self.submit_button.pack_forget()

        # Back Button
        self.back_button = tk.Button(
            self.root,
            text="Back",
            font=("Helvetica", 16),
            bg="#00796b",
            fg="white",
            height=2,
            command=self.show_main,
        )
        self.back_button.pack(pady=20)
        self.back_button.pack_forget()

        self.timer = None
        self.cap = None

    def initMQTT(self):
        # Hardcoded MQTT settings
        self.mqtt_host = "ae1e003b.ala.asia-southeast1.emqxsl.com"
        self.mqtt_port = 8883  # Standard port for MQTT over SSL/TLS
        self.mqtt_username = "react-web"
        self.mqtt_password = "react-web"
        self.mqtt_topic = "lockit"

        # MQTT Client Initialization
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        # Set TLS/SSL options
        self.mqtt_client.tls_set(ca_certs="cert.crt")
        self.mqtt_client.tls_insecure_set(
            False
        )  # Set to True if you want to disable certificate verification

        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

    def on_message(self, client, userdata, msg):
        print(f"Message received: {msg.payload.decode()}")

    def publish_message(self, message):
        self.mqtt_client.publish(self.mqtt_topic, message)

    def parse_qr_code(self, input):
        parts = input.split("-")

        if len(parts) != 3:
            raise ValueError(
                'Invalid input format. Expected format is "userId-BoxId-pin"'
            )

        user_id = parts[0]
        id = parts[1]
        pin = parts[2]

        # Create a dictionary with the parsed data
        parsed_data = {"user_id": user_id, "id": id, "pin": pin}

        # Convert the dictionary to a JSON-formatted string
        json_string = json.dumps(parsed_data)

        return json_string

    def show_main(self):
        self.start_button.pack(pady=20)
        self.input_code_button.pack(pady=20)
        self.scanner_frame.pack_forget()
        self.code_input.pack_forget()
        self.submit_button.pack_forget()
        self.back_button.pack_forget()
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.timer:
            self.root.after_cancel(self.timer)

    def show_scanner(self):
        self.start_button.pack_forget()
        self.input_code_button.pack_forget()
        self.scanner_frame.pack(pady=20)
        self.back_button.pack(pady=20)
        self.cap = cv2.VideoCapture(0)
        self.update_frame()

    def show_input_form(self):
        self.start_button.pack_forget()
        self.input_code_button.pack_forget()
        self.code_input.pack(pady=20)
        self.submit_button.pack(pady=20)
        self.back_button.pack(pady=20)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.stop_scanning()
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = frame_rgb.shape
        q_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        q_img = cv2.resize(q_img, (640, 640))
        photo = tk.PhotoImage(master=self.scanner_frame, width=640, height=640)
        self.scanner_frame.configure(image=photo)
        self.scanner_frame.image = photo

        decoded_objects = pyzbar.decode(frame)
        for obj in decoded_objects:
            qr_data = obj.data.decode("utf-8")
            try:
                parsed_data = self.parse_qr_code(qr_data)
                self.publish_message(parsed_data)  # Publish parsed QR code data
                self.stop_scanning()
                messagebox.showinfo("QR Code Scanned", qr_data)
                return
            except ValueError as e:
                print(f"Error parsing QR code: {e}")
                messagebox.showerror("Error", "Error parsing QR code.")
                self.stop_scanning()
                return

        self.timer = self.root.after(20, self.update_frame)

    def submit_code(self):
        code = self.code_input.get()
        try:
            parsed_data = self.parse_qr_code(code)
            self.publish_message(parsed_data)  # Publish parsed input code
            messagebox.showinfo("Code Submitted", "Code has been submitted.")
            self.show_main()
        except ValueError as e:
            print(f"Error parsing input code: {e}")
            messagebox.showerror("Error", "Error parsing input code.")

    def stop_scanning(self):
        if self.cap:
            self.cap.release()
        self.scanner_frame.configure(image="")
        if self.timer:
            self.root.after_cancel(self.timer)
        self.show_main()


if __name__ == "__main__":
    root = tk.Tk()
    app = QRScannerApp(root)
    root.mainloop()
