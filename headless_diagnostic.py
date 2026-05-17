#!/usr/bin/env python3
"""
Диагностическая система без GUI (headless mode)
Принимает данные с ESP32 (пульс, ЭМГ, ЭЭГ) и сохраняет диагноз в JSON
"""

import socket
import json
import time
import os
import sys
import joblib
import numpy as np
from tensorflow.keras.models import load_model
from datetime import datetime

# ==================== НАСТРОЙКИ ====================
UDP_PORT = 5005
BUFFER_SIZE = 11
DATA_FILE = "shared_data.json"

# ПУТИ К МОДЕЛИ (3 параметра)
MODEL_PATH = "medical_risk_model_3params/model.keras"
SCALER_PATH = "medical_risk_model_3params/scaler.pkl"
LABEL_MAP_PATH = "medical_risk_model_3params/label_map.json"

DIAGNOSIS_HISTORY_FILE = "diagnosis_history.json"


# ==================== ЗАГРУЗКА МОДЕЛИ ====================
def load_model_and_scaler():
    """Загружает нейросеть и скейлер"""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Модель не найдена: {MODEL_PATH}")
    if not os.path.exists(SCALER_PATH):
        raise FileNotFoundError(f"Скейлер не найден: {SCALER_PATH}")

    model = load_model(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    with open(LABEL_MAP_PATH, "r") as f:
        label_map = json.load(f)
    reverse_label_map = {v: k for k, v in label_map.items()}

    return model, scaler, reverse_label_map


# ==================== ДЕКОДЕР ПАКЕТОВ ====================
def decode_esp_packet(data):
    """
    Декодирует пакет ESP32 формата:
    [0xAA][pulse_H][pulse_L][emg_H][emg_L][eeg_H][eeg_L][gsr_H][gsr_L][XOR][0x55]
    """
    if len(data) != BUFFER_SIZE or data[0] != 0xAA or data[10] != 0x55:
        return None
    pulse = (data[1] << 8) | data[2]
    emg = (data[3] << 8) | data[4]
    eeg = (data[5] << 8) | data[6]
    gsr = (data[7] << 8) | data[8]  # GSR больше не используется, но пакет содержит
    return {"pulse": pulse, "emg": emg, "eeg": eeg, "gsr": gsr}


# ==================== ПРЕОБРАЗОВАНИЕ СЫРЫХ ДАННЫХ ====================
def calculate_bpm_from_pulse(raw_pulse):
    """
    Преобразует сырое значение пульса (0-4095) в BPM
    Калибровка: 1500 → 75 BPM, 2800 → 112 BPM
    """
    bpm = 30 + (raw_pulse / 4095) * 120
    return round(bpm, 1)


def calculate_muscle_from_emg(raw_emg):
    """
    Преобразует сырое значение ЭМГ (0-4095) в мышечную активность 0-100%
    Калибровка: 200 → 0%, 800 → 100%
    """
    min_emg, max_emg = 200, 800
    if raw_emg <= min_emg:
        return 0
    if raw_emg >= max_emg:
        return 100
    return round((raw_emg - min_emg) / (max_emg - min_emg) * 100)


def calculate_eeg_from_raw(raw_eeg):
    """
    Преобразует сырое значение ЭЭГ (0-4095) в мозговую активность 0-100%
    Калибровка: 300 → 0%, 700 → 100%
    """
    min_eeg, max_eeg = 300, 700
    if raw_eeg <= min_eeg:
        return 0
    if raw_eeg >= max_eeg:
        return 100
    return round((raw_eeg - min_eeg) / (max_eeg - min_eeg) * 100)


# ==================== ДИАГНОСТИКА ====================
def predict_diagnosis(bpm, muscle, eeg, model, scaler, label_map):
    """
    Ставит диагноз по трём показателям: пульс, мышечная активность, ЭЭГ
    """
    features = np.array([[bpm, muscle, eeg]])
    features_scaled = scaler.transform(features)
    prediction = model.predict(features_scaled, verbose=0)
    predicted_class = np.argmax(prediction[0])
    confidence = float(np.max(prediction[0]) * 100)
    diagnosis_code = label_map.get(predicted_class, "unknown")

    diagnosis_map = {
        "normal": {"code": "normal", "short": "Норма", "full": "Все показатели в норме."},
        "heart": {"code": "heart", "short": "Сердечный риск",
                  "full": "Риски сердечно-сосудистой системы. Рекомендуется контроль пульса."},
        "muscle_head": {"code": "muscle_head", "short": "Мышечная активность",
                        "full": "Повышенная мышечная активность. Возможно напряжение."},
        "brain": {"code": "brain", "short": "Мозговая активность",
                  "full": "Повышенная мозговая активность. Возможны неврологические проявления."},
        "combined": {"code": "combined", "short": "Комбинированный риск",
                     "full": "Комбинированный риск сердечной и мышечной систем."}
    }

    result = diagnosis_map.get(diagnosis_code, {
        "code": "unknown",
        "short": "Неизвестно",
        "full": "Не удалось определить диагноз"
    })
    return result, confidence


def save_diagnosis_result(diagnosis, confidence, bpm, muscle, eeg, raw_data):
    """Сохраняет результат диагностики в JSON файл"""
    history = []
    if os.path.exists(DIAGNOSIS_HISTORY_FILE):
        try:
            with open(DIAGNOSIS_HISTORY_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    history = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            history = []

    new_record = {
        "timestamp": time.time(),
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bpm": float(bpm),
        "muscle": int(muscle),
        "eeg": int(eeg),
        "diagnosis_code": diagnosis["code"],
        "diagnosis_short": diagnosis["short"],
        "diagnosis_full": diagnosis["full"],
        "confidence": float(confidence),
        "raw_data": {
            "pulse": int(raw_data["pulse"]),
            "emg": int(raw_data["emg"]),
            "eeg": int(raw_data["eeg"])
        }
    }

    history.append(new_record)

    with open(DIAGNOSIS_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    last_result = {"last_diagnosis": new_record}
    with open("last_diagnosis.json", "w", encoding="utf-8") as f:
        json.dump(last_result, f, indent=2, ensure_ascii=False)

    return new_record


# ==================== UDP СЕРВЕР ====================
def udp_server(model, scaler, label_map):
    """Запускает UDP сервер для приёма данных"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', UDP_PORT))
    sock.settimeout(1.0)

    print(f"📡 Диагностическая система запущена")
    print(f"   Порт UDP: {UDP_PORT}")
    print(f"   Модель: 3 параметра (пульс, мышечная активность, ЭЭГ)")
    print(f"   Сохранение: {DIAGNOSIS_HISTORY_FILE}")
    print("\n⏳ Ожидание данных от ESP32...\n")

    packet_count = 0

    try:
        while True:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                packet_count += 1
                raw = decode_esp_packet(data)

                if raw:
                    # Преобразование сырых данных в показатели
                    bpm = calculate_bpm_from_pulse(raw["pulse"])
                    muscle = calculate_muscle_from_emg(raw["emg"])
                    eeg = calculate_eeg_from_raw(raw["eeg"])

                    # Диагностика
                    diagnosis, confidence = predict_diagnosis(bpm, muscle, eeg, model, scaler, label_map)

                    # Сохранение
                    record = save_diagnosis_result(diagnosis, confidence, bpm, muscle, eeg, raw)

                    # Вывод в консоль
                    print(f"[{packet_count}] {record['datetime']}")
                    print(f"   Показатели: BPM={bpm}, Мышечная активность={muscle}%, ЭЭГ={eeg}%")
                    print(f"   Диагноз: {diagnosis['short']} (уверенность: {confidence:.1f}%)")
                    print(f"   Сохранён: {DIAGNOSIS_HISTORY_FILE}\n")

            except socket.timeout:
                pass
            except Exception as e:
                print(f"Ошибка: {e}")

    except KeyboardInterrupt:
        print(f"\n⏹️ Диагностическая система остановлена")
        print(f"Всего обработано пакетов: {packet_count}")
    finally:
        sock.close()


# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    print("=" * 50)
    print("🩺 Медицинский диагностический ассистент (Headless Mode)")
    print("   3 параметра: пульс, мышечная активность, ЭЭГ")
    print("=" * 50)

    # Загружаем модель
    print("\n🔧 Загрузка нейросети...")
    try:
        model, scaler, label_map = load_model_and_scaler()
        print("✅ Модель загружена")
        print(f"📋 Доступные диагнозы: {list(label_map.keys())}")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("\nСначала обучи модель:")
        print("   python generate_clean_data.py")
        print("   python train_neural_network.py")
        sys.exit(1)

    # Запускаем сервер
    udp_server(model, scaler, label_map)