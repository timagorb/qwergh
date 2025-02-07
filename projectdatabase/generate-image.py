from __future__ import annotations
import pathlib
import os
import re
from yandex_cloud_ml_sdk import YCloudML
from main import title, guid_id  # Импортируем guid_id
from yandex_cloud_ml_sdk._exceptions import AioRpcError
from grpc import StatusCode

def extract_numeric_guid(guid_tags):
    """Извлекает только числовые значения из тэгов guid_id, игнорируя пустые значения"""
    return [re.sub(r'\D', '', str(tag)) for tag in guid_tags if tag]

def main():
    sdk = YCloudML(
        folder_id=os.environ['FOLDER_ID'],
        auth=os.environ['AUTHIM'],
    )

    model = sdk.models.image_generation("yandex-art")
    model = model.configure(width_ratio=2, height_ratio=1, seed=1863)

    output_dir = pathlib.Path("generated_images")  # Папка для изображений
    output_dir.mkdir(exist_ok=True)  # Создаём, если её нет

    numeric_guid_ids = extract_numeric_guid(guid_id)  # Преобразуем guid_id в числовые значения

    for i, (message, guid) in enumerate(zip(title, numeric_guid_ids)):
        filename = f"genim_{guid}.jpeg"  # Используем числовой guid для имени файла
        path = output_dir / filename
        
        try:
            operation = model.run_deferred(message)
            result = operation.wait()
            path.write_bytes(result.image_bytes)
            print(f"✅ Изображение сохранено: {path}")
        except AioRpcError as e:
            if e.code() == StatusCode.INVALID_ARGUMENT:
                print(f"⚠️ Пропущен файл {filename} из-за ошибки: {e.details()}")
                continue  # Пропускаем и идём к следующему сообщению
            else:
                raise  # Прочие ошибки не игнорируем

if __name__ == "__main__":
    main()



'''
from __future__ import annotations
import pathlib
import os
from yandex_cloud_ml_sdk import YCloudML
from main import title
from yandex_cloud_ml_sdk._exceptions import AioRpcError
from grpc import StatusCode
from main import guid_id

def main():
    sdk = YCloudML(
        folder_id=os.environ['FOLDER_ID'],
        auth=os.environ['AUTHIM'],
    )

    model = sdk.models.image_generation("yandex-art")
    model = model.configure(width_ratio=2, height_ratio=1, seed=1863)

    output_dir = pathlib.Path("generated_images")  # Папка для изображений
    output_dir.mkdir(exist_ok=True)  # Создаём, если её нет

    for i, message in enumerate(title):
        path = output_dir / f"aigenimage_{i + 1}.jpeg"
        try:
            operation = model.run_deferred(message)
            result = operation.wait()
            path.write_bytes(result.image_bytes)
            print(f"✅ Изображение сохранено: {path}")
        except AioRpcError as e:
            if e.code() == StatusCode.INVALID_ARGUMENT:
                print(f"⚠️ Пропущен файл {i + 1} из-за ошибки: {e.details()}")
                continue  # Пропускаем и идём к следующему сообщению
            else:
                raise  # Прочие ошибки не игнорируем

if __name__ == "__main__":
    main()
print(title)
print(guid_id)
'''
'''
from __future__ import annotations
import pathlib
from yandex_cloud_ml_sdk import YCloudML
import os
from main import title
message = "узор из цветных пастельных суккулентов разных сортов, hd full wallpaper, четкий фокус, множество сложных деталей, глубина кадра, вид сверху"


def main():
    sdk = YCloudML(
        folder_id= os.environ['FOLDER_ID'],
        auth= os.environ['AUTH'],
    )

    model = sdk.models.image_generation("yandex-art")

    # configuring model
    model = model.configure(width_ratio=2, height_ratio=1, seed=1863)

    path = pathlib.Path("./image.jpeg")
    operation = model.run_deferred(message)
    result = operation.wait()
    path.write_bytes(result.image_bytes)


if __name__ == "__main__":
    main()
print(title)
'''