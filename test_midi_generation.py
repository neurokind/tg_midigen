#!/usr/bin/env python3
"""
Тестовый скрипт для проверки генерации MIDI
"""

import os
import sys
from ai_utils.use_model import generate_midi

def test_midi_generation():
    """Тестирует генерацию MIDI-файла"""
    try:
        print("🎵 Тестирование генерации MIDI...")
        
        # Проверяем наличие файлов модели
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ai_utils_dir = os.path.join(current_dir, 'ai_utils')
        
        tokenizer_path = os.path.join(ai_utils_dir, 'tokenizer.pt')
        model_path = os.path.join(ai_utils_dir, 'transformer_epoch_7.pt')
        
        if not os.path.exists(tokenizer_path):
            print(f"❌ Файл токенизатора не найден: {tokenizer_path}")
            return False
            
        if not os.path.exists(model_path):
            print(f"❌ Файл модели не найден: {model_path}")
            return False
        
        print("✅ Файлы модели найдены")
        
        # Генерируем MIDI
        print("🎼 Генерируем MIDI-файл...")
        midi_data = generate_midi(temperature=1.2)
        
        # Сохраняем тестовый файл
        test_output_path = os.path.join(current_dir, 'test_generated.mid')
        midi_data.write(test_output_path)
        
        print(f"✅ MIDI-файл успешно сгенерирован и сохранен: {test_output_path}")
        print(f"📁 Размер файла: {os.path.getsize(test_output_path)} байт")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False

if __name__ == "__main__":
    success = test_midi_generation()
    if success:
        print("\n🎉 Тест прошел успешно! Бот готов к работе.")
    else:
        print("\n💥 Тест не прошел. Проверьте настройки.")
        sys.exit(1) 