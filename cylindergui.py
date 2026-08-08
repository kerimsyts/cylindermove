import sys 
import paho.mqtt.client as mqtt 
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLineEdit, QHBoxLayout

class DroneControlGUI(QMainWindow):
    def __init__(self):
        super().__init__() 
        
        self.setWindowTitle("Drone Kontrol Arayüzü (Swarm Command)")
        self.setGeometry(100, 100, 300, 450) 
        
        # MQTT AYARLARI (İKİ FARKLI KANAL TANIMLADIK)
        self.broker_address = "broker.hivemq.com" 
        self.topic_drone1 = "cezeri/drone1/komut" # 1. Drone'un dinlediği kanal
        self.topic_drone2 = "cezeri/drone2/komut" # 2. Drone'un dinlediği kanal
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2) 
        self.client.connect(self.broker_address, 1883) 
        
        self.client.loop_start() 

        central_widget = QWidget() 
        self.setCentralWidget(central_widget) 
        layout = QVBoxLayout() 

        self.btn_arm = QPushButton("ARM") 
        layout.addWidget(self.btn_arm) 
        
        self.btn_takeoff = QPushButton("TAKEOFF")
        layout.addWidget(self.btn_takeoff)
        
        # MESAFE GİRİŞ KUTUCUKLARI
        input_layout = QHBoxLayout() 
        
        self.input_x = QLineEdit("0") 
        self.input_x.setPlaceholderText("X (m)")
        self.input_y = QLineEdit("0")
        self.input_y.setPlaceholderText("Y (m)")
        self.input_z = QLineEdit("0")
        self.input_z.setPlaceholderText("Z (m)")
        
        input_layout.addWidget(self.input_x)
        input_layout.addWidget(self.input_y)
        input_layout.addWidget(self.input_z)
        
        layout.addLayout(input_layout) 

        # MOVE butonu sadece Drone 1'i etkileyecek
        self.btn_move = QPushButton("MOVE (SADECE DRONE 1)")
        layout.addWidget(self.btn_move)

        self.btn_cylinder = QPushButton("CYLINDER")
        layout.addWidget(self.btn_cylinder)
        
        self.btn_land = QPushButton("LAND")
        layout.addWidget(self.btn_land)
        
        self.btn_disarm = QPushButton("DISARM")
        layout.addWidget(self.btn_disarm)

        self.btn_force_disarm = QPushButton("FORCE DISARM")
        self.btn_force_disarm.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        layout.addWidget(self.btn_force_disarm)

        central_widget.setLayout(layout) 

        # BUTONLARI FONKSİYONLARA BAĞLAMA 
        self.btn_arm.clicked.connect(self.send_arm)
        self.btn_takeoff.clicked.connect(self.send_takeoff)
        self.btn_move.clicked.connect(self.send_move)
        self.btn_cylinder.clicked.connect(self.send_cylinder)
        self.btn_land.clicked.connect(self.send_land)
        self.btn_disarm.clicked.connect(self.send_disarm)
        self.btn_force_disarm.clicked.connect(self.send_force_disarm)

    # --- MQTT PUBLISH METOTLARI ---

    def send_arm(self):
        # Sürü Komutu: İkisine de gönderilir
        self.client.publish(self.topic_drone1, "ARM") 
        self.client.publish(self.topic_drone2, "ARM") 
        print("Sisteme gönderildi: ARM (Drone 1 ve Drone 2)")

    def send_takeoff(self):
        self.client.publish(self.topic_drone1, "TAKEOFF")
        self.client.publish(self.topic_drone2, "TAKEOFF")
        print("Sisteme gönderildi: TAKEOFF (Drone 1 ve Drone 2)")

    def send_move(self):
        x = self.input_x.text().strip()
        y = self.input_y.text().strip()
        z = self.input_z.text().strip()
        
        if not x: x = "0"
        if not y: y = "0"
        if not z: z = "0"
        
        mesaj = f"MOVE:{x},{y},{z}"
        
        # HİZALAMA KOMUTU: SADECE DRONE 1'E GÖNDERİLİR
        self.client.publish(self.topic_drone1, mesaj)
        print(f"Gonderilen: {mesaj} (SADECE DRONE 1)")

    def send_cylinder(self):
        self.client.publish(self.topic_drone1, "CYLINDER")
        self.client.publish(self.topic_drone2, "CYLINDER")
        print("Sisteme gönderildi: CYLINDER (Drone 1 ve Drone 2)")

    def send_land(self):
        self.client.publish(self.topic_drone1, "LAND")
        self.client.publish(self.topic_drone2, "LAND")
        print("Sisteme gönderildi: LAND (Drone 1 ve Drone 2)")

    def send_disarm(self):
        self.client.publish(self.topic_drone1, "DISARM")
        self.client.publish(self.topic_drone2, "DISARM")
        print("Sisteme gönderildi: DISARM (Drone 1 ve Drone 2)")

    def send_force_disarm(self):
        self.client.publish(self.topic_drone1, "FORCE_DISARM")
        self.client.publish(self.topic_drone2, "FORCE_DISARM")
        print("Sisteme gönderildi: FORCE DISARM (Drone 1 ve Drone 2)")    
    
if __name__ == "__main__":
    app = QApplication(sys.argv) 
    window = DroneControlGUI() 
    window.show() 
    sys.exit(app.exec())