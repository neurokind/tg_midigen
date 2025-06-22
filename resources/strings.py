class Strings:
    greeting = {"ru": "Привет! Я бот для генерации случайной MIDI-музыки.",
                "en": "Hello! I'm a bot for generating random MIDI music."}
    start_dialog = {"ru": "🎵 Сгенерировать случайную музыку",
                    "en": "🎵 Generate random music"}
    waiting_message_1 = {"ru": "🎼 Генерирую музыку...",
                          "en": "🎼 Generating music..."}
    waiting_message_2 = {"ru": "🎵 Создаю мелодию...",
                          "en": "🎵 Creating melody..."}
    waiting_message_3 = {"ru": "🎶 Обрабатываю ноты...",
                          "en": "🎶 Processing notes..."}
    waiting_message_4 = {"ru": "🎹 Формирую MIDI...",
                          "en": "🎹 Forming MIDI..."}
    generation_complete = {"ru": "✅ Генерация завершена! Отправляю файл...",
                           "en": "✅ Generation complete! Sending file..."}
    generation_error = {"ru": "❌ Ошибка при генерации. Попробуйте еще раз.",
                        "en": "❌ Generation error. Please try again."}
    queue_position = {"ru": "Вы в очереди на позиции: {position}",
                      "en": "You are in queue at position: {position}"}
    caption = {"ru": "🎵 Случайная MIDI-музыка",
               "en": "🎵 Random MIDI music"}

    @staticmethod
    def get(key: str, lang: str = "ru") -> str:
        """Get string in selected language"""
        if hasattr(Strings, key):
            value = getattr(Strings, key)
            if isinstance(value, dict):
                return value.get(lang, value["ru"])
        return key
