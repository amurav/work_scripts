import sys
import os
import json
import pandas as pd
import time

 
#Пуляем звуковые файлы в модель и получаем жисоны
def transcribe(path_in, path_out, input_file_extension='.wav', output_file_extension='.wav.json', model_addr='http://localhost:8091/api/v2/stt/ru-ru'):
    
    print(f"Исходный путь: {path_in}")
    # Проверка исходного пути
    if not os.path.isdir(path_in): #Проверить наличие исходного пути
        print(f"Исходный путь не обнаружен")
        exit # Выходим
    print(f"Исходный путь обнаружен")
    
    file_list = get_files_in_dir(path_in, input_file_extension) # Получить список файлов в директории
    if len(file_list) == 0: # Если файлов 0
        print(f"В папке {path_in} не обнаружено файлов с расширением {input_file_extension}")
        exit # Выходим
    
    print(f"Обнаружено файлов с расширением {input_file_extension}: {len(file_list)}")
    
    print(f"Путь назначения: {path_out}")
    if not os.path.isdir(path_out):
        print(f"Путь назначения не обнаружен")
        exit    
    print(f"Путь назначения обнаружен")
     
    print(f"В папке {path_in} обнаружено {len(file_list)} файлов с расширением {input_file_extension}")
    print(f"Начинаю распознавать файлы")
    counter = 0 # счётчик обработанных файлов
    processed_files_size = 0 # Объём обработанных данных в Мб
    total_files = len(file_list) # Количество проверяемых файлов
    retrascribed = 0
    skipped = 0
    not_found = 0
    avg_file_size = 0
    time_spent = 0
    time_from_start = time.time()
    for file in file_list: # Перебираем все файлы
        cur_file_name = file.split("/")[-1].split(".")[0] # Получаем имя файла без расширения
        print(f"Отправляю на обраотку: {file}")
        need_transcribe = False
        if os.path.isfile(f"{file}"): # Если файл обнаружен
            out_json=f"{path_out}/{cur_file_name}.json" # Имя жисона с этого аудиофайла
            if os.path.isfile(out_json): # Проверяем транскрибирован ли уже этот файл
                if os.path.getsize(out_json) < 30: # Проверка на файл "Internal Server Error"
                    print(f"    Обнаружен неправилный жисон. Транскрибирую повторно")
                    retrascribed += 1
                    need_transcribe = True # Если объём жисона 21 байт то аудиофайл необходимо транскрибировать
                else:
                    print(f"Обнаружен жисон. Пропускаю файл")
                    skipped += 1
                    # Если размер жисона > 30 байту то транскрибация не нужна
            else:
                need_transcribe = True # Если жисон не найден то надо транскрибировать
        else:
            not_found += 1
            # Если аудиофайл не обнаружен - транскрибация не нужна
            print(f"Целевой файл не обнаружен - пропускаю")
            
        # Если таки транскрибация нужна
        
        if need_transcribe:
            while True:
                # Засекаем время
                transcribe_start = time.time() # Таймер начала обработки
                # Отправляем файл в апишечку
                os.system(f"curl -s -F 'upload_file=@{file}' {model_addr} -o {path_out}/{cur_file_name}.json")
                # Замеряем время
                transcribe_stop = time.time()
                if os.path.getsize(out_json) > 30: # Если получившийся жисон больше 21 байта
                    counter += 1
                    cur_file_size = os.path.getsize(file)/1024/1024 # Получаем объём текущего файла
                    processed_files_size += cur_file_size
                    avg_file_size = processed_files_size / counter
                    cur_time_spent = round(transcribe_stop - transcribe_start,2)
                    time_spent += cur_time_spent
                    print(f"    На обработку текущего файла ушло {cur_time_spent}s; Среднее время обработки {round(time_spent / counter,2)}s; Обработка идёт: {round(time.time() - time_from_start,2)}s")
                    break; #прерываем текущий цикл
                print(f"    Неудачная транскрибация - повторно транскрибирую файл")

        print(f"    Не обнаружено файлов:{not_found}; Пропущено файлов:{skipped}; Обработано файлов:{counter}; \n    Средний объём файла:{round(avg_file_size,2)}mb; Обработано данных: {round(processed_files_size,2)}; \n    Выполнение задачи:{round(counter / total_files, 2)}")
    return True
 
#Коонвертирую жисоны в csv
def convert_json_to_csv(path_in, path_out, input_file_extension = ".json"):
    print(f"Исходный путь: {path_in}")
    print(f"Путь назначения: {path_out}")
    file_list = get_files_in_dir(path_in, input_file_extension)
    if len(file_list) == 0:
        print(f"В папке {path_in} не обнаружено файлов с расширением {input_file_extension}")
        exit
     
    print(f"В папке {path_in} обнаружено {len(file_list)} файлов с расширением {input_file_extension}")
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