import sys #Python'un windowsla iletişimi için
import paho.mqtt.client as mqtt #MQTT haberleşme kütüphanesi 
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLineEdit, QHBoxLayout
#Sekmede tıklamaları vs işletim sistemine iletir(motor), sekmenin dış hattı için, butonları oluşturmamızı sağlar,YAZI KUTUSU
#Butonları otomatik alt alta dizme, (boş kanvas) butonları kutucuk içine yerleştirmemizi sağlar, YAN YANA DİZME

# Arayüzümüzü OOP standartlarına uygun olarak bir Class olarak tasarlıyoruz.

class DroneControlGUI(QMainWindow): #DroneControlGUI adında bir şablon ve QMainWindows sayesinde hazır bir pencere oluşturuyoruz
    def __init__(self): #Object'i kullanıma hazır hale getirmek için class özelliklerini object'in kendisine aktarır. constructor
        super().__init__() #Miras alınan üst sınıftan(super onu temsil eder) yani QMainWindow ile bir taslak pencere hazırla.
        
        # 1. Pencerenin temel özellikleri
        self.setWindowTitle("Drone Kontrol Arayüzü")
        self.setGeometry(100, 100, 300, 450) #(ekranın solundan x kadar boşluk bırak, y ,genişlik,yükseklik)
        
        # MQTT AYARLARI VE THREADING
        self.broker_address = "broker.hivemq.com" # Test için ücretsiz genel MQTT sunucusu
        self.topic = "cezeri/drone/komut" # Mesajlarımızı bırakacağımız özel başlık (Hangi odaya/kanala mesaj atacağımız)
        
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2) # Kendimize bir postacı nesnesi üretiyoruz. (Parantezin içi, terminalde latest API version uyarısı çıkmaması için)
        self.client.connect(self.broker_address, 1883) # İstemciyi broker'a  bağlıyoruz. 1883 dünya standart portudur.
        
        self.client.loop_start() # THREADING: MQTT dinleme/gönderme işini ana arayüzden ayırıp ayrı thread'de çalıştırır.Arayüzün donmasını engelleme işini tek başına yapar.

        # 2. Ana widget ve Layout (Düzen) oluşturma
        central_widget = QWidget() #central_widget adında boş bir kanvas(QWidget) oluştur
        self.setCentralWidget(central_widget) #merkezine bu kanvası koy. kanvasın üzerine butonlar koyulur.
        
        layout = QVBoxLayout() 
        

        # 3. İstenen temel komut butonlarını oluşturma ve düzene ekleme
        self.btn_arm = QPushButton("ARM") #self. şeklinde butonu tanımladığımız için init fonksiyonunun içinde sıkışıp kalmaz. başka fonksiyonlarda da butona erişebileceğiz.
        layout.addWidget(self.btn_arm) #butonu dikey düzene geçiriyoruz.
        
        self.btn_takeoff = QPushButton("TAKEOFF")
        layout.addWidget(self.btn_takeoff)
        
         # MESAFE GİRİŞ KUTUCUKLARI
        input_layout = QHBoxLayout() # X, Y, Z kutucuklarını yan yana koymak için
        
        self.input_x = QLineEdit("0") # Varsayılan değer 0
        self.input_x.setPlaceholderText("X (m)")
        self.input_y = QLineEdit("0")
        self.input_y.setPlaceholderText("Y (m)")
        self.input_z = QLineEdit("0")
        self.input_z.setPlaceholderText("Z (m)")
        
        input_layout.addWidget(self.input_x)
        input_layout.addWidget(self.input_y)
        input_layout.addWidget(self.input_z)
        
        layout.addLayout(input_layout) # Kutucukları ana düzene ekle

        self.btn_move = QPushButton("MOVE")
        layout.addWidget(self.btn_move)

        self.btn_cylinder = QPushButton("CYLINDER")
        layout.addWidget(self.btn_cylinder)
        
        self.btn_land = QPushButton("LAND")
        layout.addWidget(self.btn_land)
        
        self.btn_disarm = QPushButton("DISARM")
        layout.addWidget(self.btn_disarm)

        self.btn_force_disarm = QPushButton("FORCE DISARM")
        # Butonu kırmızı arka plan, beyaz ve kalın yazı yapıyoruz
        self.btn_force_disarm.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        layout.addWidget(self.btn_force_disarm)

        # 4. Hazırladığımız bu yukarıdan aşağı düzeni ana pencereye yerleştiriyoruz.
        central_widget.setLayout(layout) 

        # BUTONLARI FONKSİYONLARA BAĞLAMA 
        # .clicked.connect() komutu, butona tıklandığı an içindeki sinyali alıp, aşağıda bizim yazdığımız fonksiyonlara bağlar.
        self.btn_arm.clicked.connect(self.send_arm)
        self.btn_takeoff.clicked.connect(self.send_takeoff)
        self.btn_move.clicked.connect(self.send_move)
        self.btn_cylinder.clicked.connect(self.send_cylinder)
        self.btn_land.clicked.connect(self.send_land)
        self.btn_disarm.clicked.connect(self.send_disarm)
        self.btn_force_disarm.clicked.connect(self.send_force_disarm)

    # MQTT PUBLISH METOTLARI
    # Yukarıda butonlara bağladığımız bu metotlar, butona basıldığı an çalışır.
    def send_arm(self):
        self.client.publish(self.topic, "ARM") # Postacıya, belirlediğimiz topic altına "ARM" mesajını yayınlamasını (publish) söylüyoruz.
        print("Sisteme gönderildi: ARM") # Butonun çalıştığını bizim de görebilmemiz için terminale bir not yazdırıyoruz.

    def send_takeoff(self):
        self.client.publish(self.topic, "TAKEOFF")
        print("Sisteme gönderildi: TAKEOFF")

    def send_move(self):
        # Kutucuklardaki veriyi al, gereksiz boşlukları temizle
        x = self.input_x.text().strip()
        y = self.input_y.text().strip()
        z = self.input_z.text().strip()
        
        # Eğer kutucuklar boşsa varsayılan olarak 0 gönder
        if not x: x = "0"
        if not y: y = "0"
        if not z: z = "0"
        
        # Mesajı tam olarak "MOVE:2,3,8" formatında birleştir (arada boşluk olmayacak)
        mesaj = f"MOVE:{x},{y},{z}"
        
        self.client.publish(self.topic, mesaj)
        print(f"Gonderilen: {mesaj}")

    def send_cylinder(self):
        self.client.publish(self.topic, "CYLINDER")
        print("Sisteme gönderildi: CYLINDER")

    def send_land(self):
        self.client.publish(self.topic, "LAND")
        print("Sisteme gönderildi: LAND")

    def send_disarm(self):
        self.client.publish(self.topic, "DISARM")
        print("Sisteme gönderildi: DISARM")

    def send_force_disarm(self):
        self.client.publish(self.topic, "FORCE_DISARM")
        print("Sisteme gönderildi: FORCE DISARM ")    
    

# Uygulamanın çalıştırıldığı ana tetikleyici blok
if __name__ == "__main__": #Güvenlik kontrolu. main.py dosyası yalnızca terminalden açılırsa aşağıdaki kodları çalıştır. 
    #Eğer bu dosya başka bir dosyaya import edilirse pencerenin kendi kendine açılmasını engeller.
    
    app = QApplication(sys.argv) #QApplication motorunu çalıştırıyoruz. İçine windows ile tam uyumlu başlasın diye sys.argv=işletim sisteminden gelebilecek ekstra komutlar ekliyoruz. 
    window = DroneControlGUI() # Sınıfımızdan bir pencere örneği yaratıyoruz
    window.show() # Pencereyi görünür yapıyoruz
    sys.exit(app.exec()) # Çarpı tuşuna basılana kadar pencerenin açık kalmasını sağlıyoruz   