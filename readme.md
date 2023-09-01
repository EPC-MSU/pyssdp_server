# revealer_srv

Сервер c поддержкой SSDP на python.

#### Принцип работы:
Скрипт запускает SSDP-сервер, который подключается к мультикасту на всех адаптерах и прослушивает все входящие SSDP-сообщения. При получении правильного M-SEARCH, он отвечает по протоколу UPnP, а затем отправляет NOTIFY-пакеты по всем доступным адаптерам (чтобы Revealer смог обнаружить устройство, даже если оно находится в другой сети).\
Также запускается HTTP-сервер, который при получении запроса возвращает xml-файл с информацией об устройстве. Эту информацию скрипт получает из конфигурационного файла `configuration.ini`.

## Конфигурационный файл

В папке с программой/скриптом должен присутствовать конфигурационный файл `configuration.ini`. \
Структура конфигурационного файла:


```ini
[MAIN]
friendly_name =
manufacturer =
manufacturer_url =
model_description =
model_name =
model_number =
model_url =
serial_number =
presentation_url =

[SERVER]
os =
os_version =
product =
product_version =
```
Для работы программы обязательно должны быть заполнены поля *friendly_name*, *product* и *product_version*. Остальные поля могут отсутствовать или быть пустыми - они будут интерпретированы как пустые строки.

## Автозапуск на Linux

Чтобы настроить автозапуск с помощью systemd, нужно создать сервис, который будет запускаться после подключения устройства к сети.

1. В файле `revealer.service` в строке WorkingDirectory указать правильный путь на папку со скриптом. Поместить этот файл в папку /etc/systemd/system.

2. Дать команду systemd, что этот сервис должен быть включен в автозапуск:

```bash
sudo systemctl enable revealer
sudo systemctl start revealer
```


## Выпуск релиза

### Выпуск релиза в Windows

5. Для выпуска релиза в Windows нужно выполнить скрипт `release.bat`:

```bash
release.bat
```

### Выпуск релиза в Linux

5. Для выпуска релиза в Linux нужно выполнить скрипт `release.sh`:

```bash
bash release.sh
```

Обратите внимание, что для запуска скрипта в Linux могут потребоваться дополнительные действия:
* Добавьте `release.sh` права на запуск:
```bash
chmod +x ./release.sh
```
* Установите версию python3 с поддержкой виртуальных окружений:
```bash
sudo apt-get install python3.8-venv
```

## Запуск скрипта на python
Установить зависимости (см. requirements.txt) в виртуальное окружениеб перейти в папку с файлом main.py и запустить скрипт:

### Запуск в Windows (из venv)

```bash
venv\Scripts\python main.py
```

### Запуск в Linux (из venv)
```bash
venv/bin/python3 main.py
```