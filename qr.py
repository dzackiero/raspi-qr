import json
import sys
import cv2
import paho.mqtt.client as mqtt
from pyzbar import pyzbar
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QStackedWidget,
    QLineEdit,
    QSpacerItem,
    QSizePolicy,
)


class QRScannerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.initMQTT()

    def initUI(self):
        self.setWindowTitle("QR Code Scanner")
        self.setGeometry(100, 100, 800, 800)
        self.setStyleSheet("background-color: #ffffff;")

        # Main Layout
        main_layout = QVBoxLayout()

        # Title
        title_label = QLabel(
            "Welcome to LockIt, press 'Start Scanning' or 'Enter' to scan your QR Code"
        )
        title_label.setFont(QFont("Helvetica", 18))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #333333;")
        main_layout.addWidget(title_label)

        # Spacer
        main_layout.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # Start Scanning Button
        self.start_button = QPushButton("Start Scanning")
        self.start_button.setFont(QFont("Helvetica", 16))
        self.start_button.setFixedHeight(60)
        self.start_button.setStyleSheet(
            """
            QPushButton {
                background-color: #ff8c00;
                color: white;
                border-radius: 10px;
            }
            QPushButton:pressed {
                background-color: #e67600;
            }
        """
        )
        self.start_button.clicked.connect(self.show_scanner)
        main_layout.addWidget(self.start_button)

        # Input Code Button
        self.input_code_button = QPushButton("Input Your Code")
        self.input_code_button.setFont(QFont("Helvetica", 16))
        self.input_code_button.setFixedHeight(60)
        self.input_code_button.setStyleSheet(
            """
            QPushButton {
                background-color: #00796b;
                color: white;
                border-radius: 10px;
            }
            QPushButton:pressed {
                background-color: #004d40;
            }
        """
        )
        self.input_code_button.clicked.connect(self.show_input_form)
        main_layout.addWidget(self.input_code_button)

        # Spacer
        main_layout.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        )

        # Set Main Layout
        self.main_widget = QWidget()
        self.main_widget.setLayout(main_layout)

        # Scanner Layout
        scanner_layout = QVBoxLayout()

        self.camera_frame = QLabel()
        self.camera_frame.setFixedSize(640, 640)  # Fixed square size
        self.camera_frame.setAlignment(Qt.AlignCenter)
        self.camera_frame.setStyleSheet(
            "background-color: #e0e0e0; border-radius: 10px;"
        )
        scanner_layout.addWidget(self.camera_frame, alignment=Qt.AlignCenter)

        self.text_label = QLabel("")
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setFont(QFont("Helvetica", 16))
        self.text_label.setStyleSheet("color: #ff8c00;")
        scanner_layout.addWidget(self.text_label)

        self.back_button = QPushButton("Back")
        self.back_button.setFont(QFont("Helvetica", 16))
        self.back_button.setFixedHeight(60)
        self.back_button.setStyleSheet(
            """
            QPushButton {
                background-color: #00796b;
                color: white;
                border-radius: 10px;
            }
            QPushButton:pressed {
                background-color: #004d40;
            }
        """
        )
        self.back_button.clicked.connect(self.show_main)
        scanner_layout.addWidget(self.back_button)

        self.scanner_widget = QWidget()
        self.scanner_widget.setLayout(scanner_layout)

        # Input Form Layout
        form_layout = QVBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setFont(QFont("Helvetica", 16))
        self.code_input.setPlaceholderText("Enter your code here")
        form_layout.addWidget(self.code_input)

        self.submit_button = QPushButton("Submit")
        self.submit_button.setFont(QFont("Helvetica", 16))
        self.submit_button.setFixedHeight(60)
        self.submit_button.setStyleSheet(
            """
            QPushButton {
                background-color: #ff8c00;
                color: white;
                border-radius: 10px;
            }
            QPushButton:pressed {
                background-color: #e67600;
            }
        """
        )
        self.submit_button.clicked.connect(self.submit_code)
        form_layout.addWidget(self.submit_button)

        self.back_button_form = QPushButton("Back")
        self.back_button_form.setFont(QFont("Helvetica", 16))
        self.back_button_form.setFixedHeight(60)
        self.back_button_form.setStyleSheet(
            """
            QPushButton {
                background-color: #00796b;
                color: white;
                border-radius: 10px;
            }
            QPushButton:pressed {
                background-color: #004d40;
            }
        """
        )
        self.back_button_form.clicked.connect(self.show_main)
        form_layout.addWidget(self.back_button_form)

        self.form_widget = QWidget()
        self.form_widget.setLayout(form_layout)

        # Stacked Widget
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.main_widget)
        self.stacked_widget.addWidget(self.scanner_widget)
        self.stacked_widget.addWidget(self.form_widget)

        # Set Main Layout
        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

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
        self.stacked_widget.setCurrentWidget(self.main_widget)

    def show_scanner(self):
        self.stacked_widget.setCurrentWidget(self.scanner_widget)
        self.start_button.setEnabled(False)
        self.text_label.setText("")
        self.cap = cv2.VideoCapture(0)
        self.timer.start(20)

    def show_input_form(self):
        self.stacked_widget.setCurrentWidget(self.form_widget)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            self.stop_scanning()
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = frame_rgb.shape
        step = channel * width
        q_img = QImage(frame_rgb.data, width, height, step, QImage.Format_RGB888)
        self.camera_frame.setPixmap(QPixmap.fromImage(q_img))

        decoded_objects = pyzbar.decode(frame)
        for obj in decoded_objects:
            qr_data = obj.data.decode("utf-8")
            try:
                parsed_data = self.parse_qr_code(qr_data)
                self.text_label.setText(qr_data)
                self.timer.stop()
                self.cap.release()
                self.start_button.setEnabled(True)
                self.publish_message(parsed_data)  # Publish parsed QR code data
                return
            except ValueError as e:
                print(f"Error parsing QR code: {e}")
                self.text_label.setText("Error parsing QR code.")
                self.stop_scanning()
                return

    def submit_code(self):
        code = self.code_input.text()
        try:
            parsed_data = self.parse_qr_code(code)
            self.publish_message(parsed_data)  # Publish parsed input code
            self.show_main()
        except ValueError as e:
            print(f"Error parsing input code: {e}")
            self.text_label.setText("Error parsing input code.")

    def stop_scanning(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
        self.camera_frame.clear()
        self.start_button.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QRScannerApp()
    window.show()
    sys.exit(app.exec_())
