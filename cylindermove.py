import math
import threading
import time # Kodun içinde bekletme yapmak için kullanıyoruz.
from pymavlink import mavutil # Drone'un anladığı dil olan MAVLink paketlerini oluşturmamızı sağlar.
import paho.mqtt.client as mqtt # Arayüzümüzle internet üzerinden haberleşmek için MQTT .

# MQTT
MQTT_BROKER = "broker.hivemq.com" # Mesajların toplandığı ve dağıtıldığı ana sunucu (broker).
MQTT_PORT = 1883 # MQTT iletişiminin dünya standartlarındaki varsayılan port numarası.
MQTT_TOPIC = "cezeri/drone/komut" # Arayüzün mesaj gönderdiği ve bizim dinlediğimiz özel iletişim kanalı.

# Raspberry Pi ve Cube Orange arasindaki fiziksel USB baglanti portu.
#REAL_CONNECTION_STRING = '/dev/ttyACM0' 
#BAUD_RATE = 57600 # ArduPilot'un varsayılan telemetri haberleşme hızı

SIM_CONNECTION_STRING = 'tcp:127.0.0.1:5760'

print(f"Drone baglantisi baslatiliyor: {SIM_CONNECTION_STRING}")
# Drone ile bağlantıyı kurarken baud hızını da ekliyoruz
drone = mavutil.mavlink_connection(SIM_CONNECTION_STRING)

# ArduPilot'tan gelecek Heartbeat sinyalini duyana kadar kodu burada bekletiyoruz.
drone.wait_heartbeat()
print("Drone baglantisi basarili.")

# KOMUT FONKSİYONLARI
def set_mode(mode_name):
    # ArduPilot'taki isimleri (örn: GUIDED), sistemin anladığı ID numaralarına çeviriyoruz.
    mode_id = drone.mode_mapping()[mode_name]
    # Drone'a hedef modu ayarlaması için MAVLink mesajı gönderiyoruz.
    drone.mav.set_mode_send(
        drone.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id
    )
    print(f"Ucus modu ayarlandi: {mode_name}")

def arm_drone():
    # Motorları ARM etmek için uzun formatlı komut gönderiyoruz.
    # Buradaki 2. parametre olan '1', ARM işlemini temsil eder.
    drone.mav.command_long_send(
        drone.target_system, drone.target_component, #Hangi cihaza gideceği, hangi bileşene gideceği (ardupilota gider)
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, #ArduPilot'a komutun konu başlığını (ARM,DİSARM) belirtir
        0, 1, 0, 0, 0, 0, 0, 0
    )
    print("ARM komutu gonderiliyor")

def disarm_drone():
    # Motorları DISARM etmek için ARM komutunun aynısını gönderiyoruz,
    # fakat 2. parametreyi '0' yaparak sistemi motorlar durmuş hale getiriyoruz.
    drone.mav.command_long_send(
        drone.target_system, drone.target_component, 
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("DISARM komutu gonderiliyor")
def force_disarm_drone():
    # 2. Parametredeki 21196, ArduPilot'a her şeyi yoksay ve motorları durdur demektir.
    drone.mav.command_long_send(
        drone.target_system, drone.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 0, 21196, 0, 0, 0, 0, 0
    )
    print("FORCE DISARM KOMUTU GONDERILDI")
def takeoff_drone(altitude=10):
    # Bulunduğu konumdan dikey kalkış yapması için MAV_CMD_NAV_TAKEOFF komutu yolluyoruz.
    # En sondaki parametre (altitude) drone'un çıkacağı hedef yüksekliği belirtir.
    drone.mav.command_long_send(
        drone.target_system, drone.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, #Kalkış komutu olduğunu belirtir
        0, 0, 0, 0, 0, 0, 0, altitude
    )
    print(f"TAKEOFF komutu gonderiliyor. Hedef irtifa: {altitude}m")

def land_drone():
    drone.mav.command_long_send(
        drone.target_system, drone.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND, #İniş komutu olduğunu belirtir
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("LAND komutu gonderiliyor.")

def move_drone(dist_x, dist_y, dist_z):
    # Fonksiyonun ihtiyaç duyduğu tam 16 parametreyi sırasıyla gönderiyoruz
    drone.mav.send(
        mavutil.mavlink.MAVLink_set_position_target_local_ned_message(
            0,                     # time_boot_ms (0: önemsiz)
            drone.target_system,   # target_system
            drone.target_component,# target_component
            mavutil.mavlink.MAV_FRAME_LOCAL_OFFSET_NED, # Referans: Gövde
            int(0b0000111111111000), # Maske: Sadece konumu (x,y,z) dinle
            dist_x,                # X (m)
            dist_y,                # Y (m)
            -dist_z,               # Z (m) (Yukarı doğru hareket için eksi)
            0, 0, 0,               # VX, VY, VZ (Hızlar - Maskeli)
            0, 0, 0,               # AFX, AFY, AFZ (İvmeler - Maskeli)
            0, 0                   # YAW, YAW_RATE (Dönüşler - Maskeli)
        )
    )
    print(f"MOVE komutu uygulandi: {dist_x}m, {dist_y}m, {dist_z}m")

def send_velocity(vx, vy, vz):
    # Drone'a maskeleme yaparak sadece hız komutlarını dikkate almasını söylüyoruz.
    drone.mav.send(
        mavutil.mavlink.MAVLink_set_position_target_local_ned_message(
            0, drone.target_system, drone.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            int(0b0000111111000111), # Maske: Pozisyon ve ivmeyi yoksay, sadece HIZI (VX,VY,VZ) oku
            0, 0, 0,                 # X, Y, Z Pozisyon (Maskelendiği için önemsiz)
            vx, vy, vz,              # X, Y, Z Hız (m/s)
            0, 0, 0,                 # İvme değerleri (Maskelendi)
            0, 0                     # Yaw ve Yaw Hızı (Maskelendi)
        )
    )

def execute_cylinder_maneuver():
    global stop_maneuver_flag
    stop_maneuver_flag = False
    
    radius = 2.0         # Çemberin yarıçapı (metre)
    omega = 0.6          # Açısal hız (ne kadar hızlı döneceği)
    forward_speed = 1.0  # Y ekseninde (sağa doğru) ilerleme hızı (m/s)
    tur_sayisi = 1
    duration = tur_sayisi * (2 * math.pi) / omega
    
    print(f"Silindirik gorev basladi. Toplam {tur_sayisi} tur atilacak. (Yaklasik {duration:.1f} saniye)")

    start_time = time.time()
    
    while time.time() - start_time < duration:
        # Eger baska bir komut gelirse (ornek: DISARM), bu donguyu hemen kir
        if stop_maneuver_flag:
            print("Silindirik hareket iptal edildi!")
            break
            
        t = time.time() - start_time
        
        # Hız vektörlerinin hesaplanması
        vx = radius * omega * math.cos(omega * t)
        vz = -radius * omega * math.sin(omega * t) # Z ekseni asagiya dogru (+), yukariya dogru (-) 
        vy = forward_speed
        
        send_velocity(vx, vy, vz)
        time.sleep(0.1) # Komutu 10Hz (saniyede 10 kere) sıklıkla gonder
        
    # Manevra bittiginde veya durduruldugunda drone'un sürüklenmemesi için hızları sıfırla
    send_velocity(0, 0, 0)
    print("Silindirik gorev tamamlandi.")


# ACK DİNLEYİCİSİ
def wait_command_ack(expected_cmd_id, timeout=2):
    # ArduPilot'tan gelecek COMMAND_ACK mesajını arıyoruz. 
    # Sadece gönderdiğimiz emrin ID'sine sahip olan cevabı (condition) yakalıyoruz.
    msg = drone.recv_match(type='COMMAND_ACK', condition=f'COMMAND_ACK.command=={expected_cmd_id}', blocking=True, timeout=timeout)
    
    if msg is None:
        return "Zaman Asimi (Cevap Alinamadi)"
    elif msg.result == 0: 
        # 0 sayısı MAVLink standardında MAV_RESULT_ACCEPTED (Kabul Edildi) demektir.
        return "Komut Onaylandi"
    else:
        # Hangi komutun reddedildiğine bakıp ona göre mantıklı bir Türkçe açıklama yapıyoruz.
        if expected_cmd_id == 22: # 22 = TAKEOFF
            return "Reddedildi (Drone zaten havada veya motorlar ARM edilmedi.)"
        elif expected_cmd_id == 400: # 400 = ARM veya DISARM
            return "Reddedildi! (Drone su an havada veya ucus oncesi sensor (Pre-Arm) kontrolleri gecilemedi.)"
        else:
            return "Reddedildi"
# -----------------------------------------------------------


# MQTT DİNLEYİCİSİ
def on_connect(client, userdata, flags, rc):
    # Postacımız internetteki sunucuya bağlandığında otomatik olarak bu fonksiyon çalışır.
    print("MQTT Broker baglantisi saglandi. Dinleniyor")
    # İlgili kanala abone oluyoruz ki mesaj geldiğinde anında haberimiz olsun.
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    # Odaya mesaj düştüğünde bu fonksiyon otomatik tetiklenir.
    # Gelen elektrik/byte sinyalini bizim okuyabileceğimiz normal metne çeviriyoruz.
    command = msg.payload.decode('utf-8').strip()
    print(f"Alinan MQTT Komutu: {command}")
    
    # Gelen komuta göre doğru fonksiyonu çağırıyoruz.
    if command == "ARM":
        set_mode("GUIDED") # Önce dışarıdan kontrole izin veren GUIDED moduna geçiyoruz.
        # Modun ArduPilot tarafından tamamen işlenip onaylanması için motorları açmadan önce 1 saniye bekliyoruz.
        time.sleep(1) 
        
        # Yeni emri vermeden hemen önce, kutudaki eski onayları (varsa) atıyoruz
        while drone.recv_match(type='COMMAND_ACK', blocking=False):
            pass
            
        arm_drone()
        
        # Sonuç Kontrolü (ARM ID: 400)
        sonuc = wait_command_ack(400)
        print(f"ARM Komutu Sonucu: {sonuc}")
         
    elif command == "DISARM":
        global stop_maneuver_flag
        stop_maneuver_flag = True # Varsa arka plan görevini durdur
        while drone.recv_match(type='COMMAND_ACK', blocking=False):
            pass
        
        disarm_drone()
        
        # Sonuç Kontrolü
        # 400 sayısı MAV_CMD_COMPONENT_ARM_DISARM komutunun id'sidir.
        # ArduPilot'un vereceği yanıtı 2 saniye boyunca dinleyip sonucu öğreniyoruz.
        sonuc = wait_command_ack(400)
        print(f"DISARM Komutu Sonucu: {sonuc}")
        
    elif command == "FORCE_DISARM":
        stop_maneuver_flag = True
        # Acil durumda bekleme yapmadan önce kutuyu temizliyoruz
        while drone.recv_match(type='COMMAND_ACK', blocking=False):
            pass
            
        force_disarm_drone()
        
        # Sonuç Kontrolü
        sonuc = wait_command_ack(400)
        print(f"FORCE DISARM Sonucu: {sonuc}")

    elif command == "TAKEOFF":
        while drone.recv_match(type='COMMAND_ACK', blocking=False):
            pass
            
        takeoff_drone(10)  
        # 22 sayısı MAV_CMD_NAV_TAKEOFF komutunun kimlik numarasıdır.
        sonuc = wait_command_ack(22)
        print(f"TAKEOFF Komutu Sonucu: {sonuc}")
        
    elif command == "LAND":
        while drone.recv_match(type='COMMAND_ACK', blocking=False):
            pass
            
        land_drone() 
        # 21 sayısı MAV_CMD_NAV_LAND komutunun kimlik numarasıdır.
        sonuc = wait_command_ack(21)
        print(f"LAND Komutu Sonucu: {sonuc}")

    elif command == "CYLINDER":
        if not drone.motors_armed():
            print("CYLINDER Reddedildi: Motorlar ARM degil")
        else:
            set_mode("GUIDED")
            # MQTT'nin kitlenmemesi için fonksiyonu arka planda bir thread olarak başlatıyoruz
            maneuver_thread = threading.Thread(target=execute_cylinder_maneuver)
            maneuver_thread.start()

    elif command.startswith("MOVE:"):
        try:
            # "MOVE:2,3,8" -> "2,3,8"
            coords = command.split(":")[1] 
            x, y, z = map(float, coords.split(",")) #Gelen xyz değerlerini bitlere dönüştürür.
            
            if not drone.motors_armed():
                print("MOVE Reddedildi: Motorlar ARM degil")
            else:
                set_mode("GUIDED")
                move_drone(x, y, z)
                
        except Exception as e:
            print(f"HATA: MOVE formati hatasi. Mesaj: {command}, Hata detayi: {e}")
    else:
        print(f"Bilinmeyen komut geldi: {command}")

# ANA ÇALIŞMA DÖNGÜSÜ
# Kendimize MQTT kütüphanesinden bir postacı nesnesi yaratıyoruz.
client = mqtt.Client()

# Postacıya, sunucuya bağlanınca ve mesaj gelince hangi fonksiyonları çalıştıracağını öğretiyoruz.
client.on_connect = on_connect
client.on_message = on_message

print("MQTT Broker'a baglaniliyor")
# Broker adresine standart port (1883) üzerinden bağlanıyoruz. 60, zaman aşımı (timeout) süresidir.
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Kodu sonsuz bir dinleme döngüsüne sokuyoruz. Biz programı kapatana kadar yeni mesajları bekler.
client.loop_forever()