import sys
import os
import json
import pandas as pd

#Пуляем звуковые файлы в модель и получаем жисоны
def transcribe(path_in, path_out, file_extension='.wav', model_addr='http://localhost:8091/api/v2/stt/ru-ru'):
    print(f"Исходный путь: {path_in}")
    print(f"Путь назначения: {path_out}")
    file_list = get_files_in_dir(path_in, file_extension)
    if len(file_list) == 0:
        print(f"В папке {path_in} не обнаружено файлов с расширением {file_extension}")
        exit
    
    print(f"В папке {path_in} обнаружено {len(file_list)} файлов с расширением {file_extension}")
    print(f"Начинаю распознавать файлы")
    counter = 1
    total_files = len(file_list)
    for file in file_list:
        cur_file_name = file.split("/")[-1].split(".")[0]
        print(f"Отправляю на обраотку: {file}")
        os.system(f"curl -s -F 'upload_file=@{file}' {model_addr} -o {path_out}/{cur_file_name}.json")
        print(f"Обработано шт:{counter}; Выполнение задачи: {counter / total_files}")
        counter += 1
    return True

#Коонвертирую жисоны в csv
def convert_json_to_csv(path_in, path_out, file_extension = ".json"):
    print(f"Исходный путь: {path_in}")
    print(f"Путь назначения: {path_out}")
    file_list = get_files_in_dir(path_in, file_extension)
    if len(file_list) == 0:
        print(f"В папке {path_in} не обнаружено файлов с расширением {file_extension}")
        exit
    
    print(f"В папке {path_in} обнаружено {len(file_list)} файлов с расширением {file_extension}")
    print(f"Начинаю распознавать файлы")
    counter = 1
    total_files = len(file_list)
    for file in file_list:
        cur_file_name = file.split("/")[-1].split(".")[0]
        print(f"Отправляю на обраотку: {file}")
        with open(file, 'r') as myfile:
            data=myfile.read()
        obj = json.loads(data)
        d = {'start': 0, 'text': ['a'], 'denormalized': ['b']}
        df = pd.DataFrame(data=d)
        for i in obj:
            for j in obj[i]['metadata']['smoothed']:
                test = {'start': j['start'], 'text': j['text'], 'denormalized':j['denormalized']}
                df = df.append(test,ignore_index=True)

        df = df.drop(0)
        df = df.sort_values(by=['start'])
        new_csv = f"{path_out}/{cur_file_name}.txt"
        df.to_csv(new_csv, sep=";", index=False, encoding='cp1251')
        print(f"Обработано шт:{counter}; Выполнение задачи: {counter / total_files}")
        counter += 1

def get_files_in_dir(path_in, mask):
    file_list = [] #Результирующий список обнаруженных файлов
    for file in os.listdir(path_in):
        if file.endswith(mask):
            file_list.append(os.path.join(path_in, file))
            
    return file_list        
    
if sys.argv[1] == '-transcribe':
    print("транскрибируем вавы")
    transcribe(sys.argv[2], sys.argv[3])
elif sys.argv[1] == '-convert':
    print("конвертируем жисоны")
    convert_json_to_csv(sys.argv[2], sys.argv[3])
elif sys.argv[1] == '-help':
    print("Скармливаемые скрипту папки должны существовать.")
    print("Для распознавания используйте команду:")
    print(" python3 stt_transcriber.py -transcribe полный/путь/до/папки/с/аудиофайлами полный/до/папки/назначения/жисонов")
    print(" Пример: python3 stt_transcriber.py -transcribe /home/adminguide/audio /home/adminguide/json")
    print("Для конвертации используйте команду")
    print(" python3 stt_transcriber.py -convert полный/путь/до/папки/содержащей/жисоны полный/до/папки/назначения/цсв")
    print(" Пример: python3 stt_transcriber.py -convert /home/adminguide/json /home/adminguide/csv")
