from __future__ import annotations
import re
import os
from yandex_cloud_ml_sdk import YCloudML
from main import all_texts

def clean_text(text: str) -> str:
    # Исправляем ситуации, когда после точки нет пробела и следующая буква большая
    text = re.sub(r'\.(\S)', r'. \1', text)
    # Убираем лишние пробелы после точки, если их больше одного
    text = re.sub(r'\. {2,}', '. ', text)
    return text

def main():
    sdk = YCloudML(
        folder_id = os.environ["FOLDER_ID"],
        auth = os.environ["AUTH"],
    )
    
    # Переменная для хранения всех перефразированных текстов
    rephrased_texts = []
    
    for idx, text in enumerate(all_texts, start=1):
        messages = [
            {"role": "system", "text": "Действуй как главный редактор новостей, выполни перефразировку текста и сделай готовую новостную статью, в формате html, заголовок сохраняй только в тэгах <title>, для всего остального текста разрешается использовать исключительно тэг <p> и ничего кроме него" },
            {"role": "user", "text": text},
        ]
        
        # Запрашиваем перефразированный текст
        result = sdk.models.completions("yandexgpt").configure(temperature=0.5).run(messages)

        # Обрабатываем результат
        for alternative in result:
            cleaned_text = clean_text(alternative.text).replace("\n", "")  # Убираем переносы строк
            rephrased_texts.append(cleaned_text)  # Сохраняем очищенный текст в HTML формате
            
            # Вывод перефразированного текста
            print(f"Перефразированная новость {idx}:\n{cleaned_text}\n")
            print("-" * 80)
            break  # Берем только первый вариант
    
    print("\nВсе перефразированные тексты:")
    print(rephrased_texts)

if __name__ == "__main__":
    main()
