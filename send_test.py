#!/usr/bin/env python3
import socket
import time


def send_packet(pulse, emg, eeg, gsr=400):
    """
    Отправляет пакет в формате ESP32
    pulse, emg, eeg, gsr: значения 0-4095
    gsr теперь не используется, но пакет требует 4 значения
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    pulse_h = (pulse >> 8) & 0xFF
    pulse_l = pulse & 0xFF
    emg_h = (emg >> 8) & 0xFF
    emg_l = emg & 0xFF
    eeg_h = (eeg >> 8) & 0xFF
    eeg_l = eeg & 0xFF
    gsr_h = (gsr >> 8) & 0xFF
    gsr_l = gsr & 0xFF

    xor = 0xAA ^ pulse_h ^ pulse_l ^ emg_h ^ emg_l ^ eeg_h ^ eeg_l ^ gsr_h ^ gsr_l
    packet = bytes([0xAA, pulse_h, pulse_l, emg_h, emg_l, eeg_h, eeg_l, gsr_h, gsr_l, xor, 0x55])

    sock.sendto(packet, ('127.0.0.1', 5005))
    sock.close()
    print(f"   Пакет отправлен: pulse={pulse}, emg={emg}, eeg={eeg}")


# Сценарии для тестирования (3 параметра)
scenarios = {
    "1": {
        "name": "🟢 Норма",
        "pulse": 1500,  # BPM ~75
        "emg": 200,  # мышечная активность ~0%
        "eeg": 400,  # ЭЭГ ~30%
        "desc": "BPM~75, мышцы~0%, ЭЭГ~30%"
    },
    "2": {
        "name": "❤️ Сердечный риск (высокий пульс)",
        "pulse": 2800,  # BPM ~112
        "emg": 250,  # мышечная активность ~8%
        "eeg": 400,  # ЭЭГ ~30%
        "desc": "BPM~112, мышцы~8%, ЭЭГ~30%"
    },
    "3": {
        "name": "💪 Мышечная активность",
        "pulse": 1700,  # BPM ~80
        "emg": 800,  # мышечная активность ~100%
        "eeg": 400,  # ЭЭГ ~30%
        "desc": "BPM~80, мышцы~100%, ЭЭГ~30%"
    },
    "4": {
        "name": "🧠 Мозговая активность (высокий ЭЭГ)",
        "pulse": 1700,  # BPM ~80
        "emg": 250,  # мышечная активность ~8%
        "eeg": 750,  # ЭЭГ ~100%
        "desc": "BPM~80, мышцы~8%, ЭЭГ~100%"
    },
    "5": {
        "name": "🩺 Комбинированный (сердце + мышцы)",
        "pulse": 2800,  # BPM ~112
        "emg": 700,  # мышечная активность ~83%
        "eeg": 500,  # ЭЭГ ~50%
        "desc": "BPM~112, мышцы~83%, ЭЭГ~50%"
    },
    "6": {
        "name": "🧠 Пониженная мозговая активность",
        "pulse": 1700,  # BPM ~80
        "emg": 250,  # мышечная активность ~8%
        "eeg": 250,  # ЭЭГ ~0%
        "desc": "BPM~80, мышцы~8%, ЭЭГ~0%"
    },
    "7": {
        "name": "все плохо(очень)",
        "pulse": 9000,  # BPM ~80
        "emg": 4095,  # мышечная активность ~8%
        "eeg": 4095,  # ЭЭГ ~100%
        "desc": "BPM~150, мышцы~100%, ЭЭГ~100%"
    }
}

print("\n" + "=" * 50)
print("📡 Симулятор отправки данных (3 параметра)")
print("   Пульс (ФПГ) | Мышечная активность (ЭМГ) | Мозговая активность (ЭЭГ)")
print("=" * 50 + "\n")

for key, sc in scenarios.items():
    print(f"  {key}. {sc['name']}")
    print(f"     {sc['desc']}\n")

choice = input("👉 Введи номер сценария (1-7): ").strip()

if choice in scenarios:
    sc = scenarios[choice]
    print(f"\n✅ Отправка: {sc['name']}")
    print(f"   {sc['desc']}")
    send_packet(sc['pulse'], sc['emg'], sc['eeg'])
    print("\n📤 Пакет отправлен!")
    print("🔄 Проверь diagnosis_history.json или last_diagnosis.json")
else:
    print("\n❌ Неверный выбор! Запусти программу снова.")