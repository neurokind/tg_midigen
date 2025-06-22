#!/usr/bin/env python3
"""
Скрипт для запуска MIDI Generator Telegram Bot
"""

import sys
import logging
import asyncio
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Проверяет наличие всех необходимых файлов"""
    required_files = [
        'config.py',
        'main.py',
        'ai_utils/use_model.py',
        'ai_utils/model_params.py',
        'ai_utils/tokenizer.pt',
        'ai_utils/transformer_epoch_7.pt',
        'resources/strings.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Отсутствуют необходимые файлы: {missing_files}")
        return False
    
    logger.info("✅ Все необходимые файлы найдены")
    return True

def check_config():
    """Проверяет конфигурацию бота"""
    try:
        from config import TOKEN
        if not TOKEN or TOKEN == "ваш_токен_бота":
            logger.error("❌ Токен бота не настроен в config.py")
            return False
        logger.info("✅ Конфигурация бота корректна")
        return True
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта config.py: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка проверки конфигурации: {e}")
        return False

async def main():
    """Основная функция запуска бота"""
    logger.info("🎵 Запуск MIDI Generator Telegram Bot...")
    
    # Проверяем зависимости
    if not check_dependencies():
        logger.error("💥 Проверка зависимостей не пройдена")
        return False
    
    # Проверяем конфигурацию
    if not check_config():
        logger.error("💥 Проверка конфигурации не пройдена")
        return False
    
    try:
        # Импортируем и запускаем бота
        from main import main as bot_main
        logger.info("🚀 Запуск бота...")
        await bot_main()
        return True
        
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
        return True
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при запуске бота: {e}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        if not success:
            sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка: {e}")
        sys.exit(1) 