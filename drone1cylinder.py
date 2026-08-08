import math
import threading
import time
from pymavlink import mavutil
import paho.mqtt.client as mqtt

# MQTT AYARLARI (Sadece kendi kanalını dinler)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "cezeri/drone1/komut"

# GERÇEK DONANIM BAĞLANTISI (Raspberry Pi USB Portu)
#REAL_CONNECTION_STRING = '/dev/ttyACM0'
#BAUD_RATE = 57600

SIM_CONNECTION_STRING = 'tcp:127.0.0.1:5760'
print(f"Drone bağlantisi baslatiliyor: {SIM_CONNECTION_STRING}")
drone1 = mavutil.mavlink_connection(SIM_CONNECTION_STRING)

#print(f"Drone baglantisi baslatiliyor: {REAL_CONNECTION_STRING}")
#drone1 = mavutil.mavlink_connection(REAL_CONNECTION_STRING, baud=BAUD_RATE)
drone1.wait_heartbeat()
print("Drone baglantisi basarili.")

# KOMUT FONKSİYONLARI
def set_mode(mode_name):
    mode_id1 = drone1.mode_mapping()[mode_name]
    drone1.mav.set_mode_send(
        drone1.target_system,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id1
    )
    print(f"Ucus modu ayarlandi: {mode_name}")

def arm_drone():
    drone1.mav.command_long_send(
        drone1.target_system, drone1.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 1, 0, 0, 0, 0, 0, 0
    )
    print("ARM komutu gonderiliyor")

def disarm_drone():
    drone1.mav.command_long_send(
        drone1.target_system, drone1.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("DISARM komutu gonderiliyor")

def force_disarm_drone():
    drone1.mav.command_long_send(
        drone1.target_system, drone1.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0, 0, 21196, 0, 0, 0, 0, 0
    )
    print("FORCE DISARM KOMUTU GONDERILDI")

def takeoff_drone(altitude=10):
    drone1.mav.command_long_send(
        drone1.target_system, drone1.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, 0, 0, 0, altitude
    )
    print(f"TAKEOFF komutu gonderiliyor. Hedef irtifa: {altitude}m")

def land_drone():
    drone1.mav.command_long_send(
        drone1.target_system, drone1.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("LAND komutu gonderiliyor.")

def move_drone(hedef_drone, dist_x, dist_y, dist_z):
    hedef_drone.mav.send(
        mavutil.mavlink.MAVLink_set_position_target_local_ned_message(
            0, hedef_drone.target_system, hedef_drone.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_OFFSET_NED,
            int(0b0000111111111000),
            dist_x, dist_y, -dist_z,
            0, 0, 0,
            0, 0, 0,
            0, 0
        )
    )
    print(f"MOVE komutu uygulandi: {dist_x}m, {dist_y}m, {dist_z}m")

def send_velocity(hedef_drone, vx, vy, vz):
    hedef_drone.mav.send(
        mavutil.mavlink.MAVLink_set_position_target_local_ned_message(
            0, hedef_drone.target_system, hedef_drone.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            int(0b0000111111000111),
            0, 0, 0,
            vx, vy, vz,
            0, 0, 0,
            0, 0
        )
    )

def execute_cylinder_maneuver():
    global stop_maneuver_flag #başka bir komut vererek bu hareketi durdurmamızı sağlar. (örn:land)
    stop_maneuver_flag = False #başlangıçta silindir hareketinin çalışması için durdurmayı false yapıyoruz.
    
    radius = 4.0         # Çemberin yarıçapı (metre)
    omega = 0.3          # Açısal hız (limitlere takılmamak için yavaşlatıldı)
    forward_speed = 1.0  # İleri gidiş hızı
    tur_sayisi = 1
    duration = tur_sayisi * (2 * math.pi) / omega
    
    print(f"Silindirik gorev basladi. Toplam {tur_sayisi} tur atilacak. (Yaklasik {duration:.1f} saniye)")

    start_time = time.time()
    
    while time.time() - start_time < duration: #başlangıca göre geçen zamanı hesapla. duration ile eşitlenene kadar fonksiyonu çalıştır.
        if stop_maneuver_flag:
            print("Sarmal hareket iptal edildi!")
            break
            
        t = time.time() - start_time
        
        vx = radius * omega * math.cos(omega * t)
        vz = -radius * omega * math.sin(omega * t)
        vy = forward_speed
        
        send_velocity(drone1, vx, vy, vz)
        time.sleep(0.1)
        
    send_velocity(drone1, 0, 0, 0)
    print("Silindirik gorev tamamlandi.")


# ACK DİNLEYİCİSİ
def wait_command_ack(expected_cmd_id, timeout=2):
    msg = drone1.recv_match(type='COMMAND_ACK', condition=f'COMMAND_ACK.command=={expected_cmd_id}', blocking=True, timeout=timeout)
    
    if msg is None:
        return "Zaman Asimi (Cevap Alinamadi)"
    elif msg.result == 0:
        return "Komut Onaylandi"
    else:
        if expected_cmd_id == 22:
            return "Reddedildi (Drone zaten havada veya motorlar ARM edilmedi.)"
        elif expected_cmd_id == 400:
            return "Reddedildi! (Drone su an havada veya ucus oncesi sensor kontrolleri gecilemedi.)"
        else:
            return "Reddedildi"
# -----------------------------------------------------------


# MQTT DİNLEYİCİSİ
def on_connect(client, userdata, flags, rc):
    print("MQTT Broker baglantisi saglandi. Dinleniyor")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    command = msg.payload.decode('utf-8').strip()
    print(f"Alinan MQTT Komutu: {command}")
    
    if command == "ARM":
        set_mode("GUIDED")
        time.sleep(1)
        
        while drone1.recv_match(type='COMMAND_ACK', blocking=False):
            pass
            
        arm_drone()
        sonuc = wait_command_ack(400)
        print(f"ARM Komutu Sonucu: {sonuc}")
         
    elif command == "DISARM":
        global stop_maneuver_flag
        stop_maneuver_flag = True
        while drone1.recv_match(type='COMMAND_ACK', blocking=False):
            pass
        
        disarm_drone()
        sonuc = wait_command_ack(400)
        print(f"DISARM Komutu Sonucu: {sonuc}")
        
    elif command == "FORCE_DISARM":
        stop_maneuver_flag = True
        while drone1.recv_match(type='COMMAND_ACK', blocking=False):
            pass
            
        force_disarm_drone()
        sonuc = wait_command_ack(400)
        print(f"FORCE DISARM Sonucu: {sonuc}")

    elif command == "TAKEOFF":
        while drone1.recv_match(type='COMMAND_ACK', blocking=False):
            pass
            
        takeoff_drone(10) 
        sonuc = wait_command_ack(22)
        print(f"TAKEOFF Komutu Sonucu: {sonuc}")
        
    elif command == "LAND":
        while drone1.recv_match(type='COMMAND_ACK', blocking=False):
            pass
            
        land_drone()
        sonuc = wait_command_ack(21)
        print(f"LAND Komutu Sonucu: {sonuc}")

    elif command == "CYLINDER":
        # Posta kutusu bosaltma islemi (Sadece tek drone icin)
        while drone1.recv_match(blocking=False):
            pass
            
        drone1.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
        
        if not drone1.motors_armed():
            print("CYLINDER Reddedildi: Drone ARM degil")
        else:
            set_mode("GUIDED")
            maneuver_thread = threading.Thread(target=execute_cylinder_maneuver)
            maneuver_thread.start()

    elif command.startswith("MOVE:"):
        try:
            coords = command.split(":")[1]
            x, y, z = map(float, coords.split(","))
            
            if not drone1.motors_armed():
                print("MOVE Reddedildi: Motorlar ARM degil")
            else:
                set_mode("GUIDED")
                move_drone(drone1, x, y, z)
                
        except Exception as e:
            print(f"HATA: MOVE formati hatasi. Detay: {e}")
    else:
        print(f"Bilinmeyen komut geldi: {command}")

# ANA ÇALIŞMA DÖNGÜSÜ
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("MQTT Broker'a baglaniliyor")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()