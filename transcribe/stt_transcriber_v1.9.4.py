import sys
import os
import json
# import pandas as pd
import time
import fnmatch
# import paramiko
# import time
import threading
from threading import Thread
import shutil


def pick_audio(path_in, path_out, input_file_extension='.wav', each=10):
    path_in_list = os.listdir(path_in)  # Смотрим список файлов в текущей директории.
    print(f"Список объектов в директории пасин {path_in_list}")
    for path_in_obj in path_in_list:  # перебираем всё что есть в исходной директории (это должна быть папка куда происходит загрузка аудиофайлов от мцн нтт
        print(f"Проверяю объект {path_in}/{path_in_obj}")
        if (os.path.isdir(f"{path_in}/{path_in_obj}")):  # Если это директория, дербаним её
            print(f"Это папка")
            file_list = get_files_in_dir(f"{path_in}/{path_in_obj}",
                                         input_file_extension)  # Получить список файлов в директории
            print(f"{path_in_obj}")
            print(f"{path_out}")
            print(f"{input_file_extension}")
            print(f"{each}")
            #	print(f"{}")
            print(f"Обнаружено файлов {len(file_list)}")

            counter = 0
            for file in file_list:
                if (counter % int(each) == 0):
                    cur_file_name = file.split("/")[-1].split(".")[0]  # Получаем имя файла без расширения
                    adate = cur_file_name.split("!")[0]
                    ayyyy = adate[0:4]
                    amm = adate[4:6]
                    add = adate[6:8]
                    cur_file_dir_safe = f"/root/safe/{ayyyy}/{amm}/{add}"
                    # Проверяем наличие файла в пасауте
                    cur_file_name = file.split("/")[-1]  # Получаем имя файла
                    print(f"Проверяю наличие файла {cur_file_dir_safe}/{cur_file_name}")
                    print(f"ИЛИ Проверяю наличие файла {path_out}/{cur_file_name}")
                    if os.path.isfile(f"{cur_file_dir_safe}/{cur_file_name}"):
                        print(f"Файл обнаружен в сэйфе, копировать не надо")
                    elif os.path.isfile(f"{path_out}/{cur_file_name}"):  # Если файл обнаружен
                        print(f"Файл обнаружен в папке для транскрибации, копировать не надо")
                    else:
                        print(f"Файл не найден, копирую")
#                        shutil.copy(file, path_out)
                        shutil.move(file, path_out)
                        #shutil.copy(file, '/root/safe/')
                counter += 1
        else:
            print(f"Это не папка")


def multi_transcribe(path_in, path_out, input_file_extension='.wav', output_file_extension='.wav.json', threads=3,
                     model_addr='http://localhost:8091/api/v2/stt/ru-ru'):
    print(f"Источник файлов для транскрибации: {path_in}")
    print(f"Расширение файлов для транскрибации: {input_file_extension}")
    print(f"Путь выгрузки жисонов: {path_out}")
    print(f"Расширение выгружаемых жисонов: {output_file_extension}")
    print(f"Количество потоков: {threads}")
    print(f"Адрес кластера STT: {model_addr}")
    while True:
        if (threading.active_count() < (21 + 1)):
            stt_thread = Thread(target=transcribe,
                                args=(path_in, path_out, input_file_extension, output_file_extension, model_addr,))
            stt_thread.start()
            print("Запущено потоков: %i" % threading.active_count())
        time.sleep(5)


def transcribe(path_in, path_out, input_file_extension='.wav', output_file_extension='.wav.json',
               model_addr='http://localhost:8091/api/v2/stt/ru-ru'):

    safe_directory = '/root/safe/' #Директория куда сохраняются транскрибированные файлы на N дней

#    print(f"Исходный путь: {path_in}")
    # Проверка исходного пути
    if not os.path.isdir(path_in):  # Проверить наличие исходного пути
        print(f"Исходный путь не обнаружен: {path_in}")
        exit  # Выходим
#    print(f"Исходный путь обнаружен")

    file_list = get_files_in_dir(path_in, input_file_extension)  # Получить список файлов в директории
    if len(file_list) == 0:  # Если файлов 0
        print(f"В папке {path_in} не обнаружено файлов с расширением {input_file_extension}")
        exit  # Выходим

#    print(f"Путь назначения: {path_out}")
    if not os.path.isdir(path_out):
        print(f"Путь назначения не обнаружен: {path_out}")
        exit
#    print(f"Путь назначения обнаружен")

    print(f"В папке {path_in} обнаружено {len(file_list)} файлов с расширением {input_file_extension}")
#    print(f"Начинаю распознавать файлы")
    counter = 0  # счётчик обработанных файлов
    processed_files_size = 0  # Объём обработанных данных в Мб
    total_files = len(file_list)  # Количество проверяемых файлов
    retrascribed = 0
    skipped = 0
    not_found = 0
    avg_file_size = 0
    time_spent = 0
    time_from_start = time.time()
    for file in file_list:  # Перебираем все файлы
        cur_file_name = file.split("/")[-1].replace(input_file_extension, "") #Берём путь до файла и разбиваем его по /
        # и берём последний результат. В этом результате заменяем расширение из переменной input_file_extension на ""
        cur_file_lock = f"{path_out}/{cur_file_name}.lock"

        cur_file_out_json = f"{path_out}/{cur_file_name}.wav.json"  # Имя жисона с этого аудиофайла собираем из path_out и
        # текущего имени файла + расширение .wav

#        print(f"Имя файла без расширения: {cur_file_name}")
        print(f"Отправляю на обраотку: {file}")
        need_transcribe = False # Заранее устанавливаем необходимость транскрибации в False
        if os.path.isfile(f"{file}"):  # Если файл обнаружен
            if os.path.isfile(cur_file_out_json):  # Проверяем транскрибирован ли уже этот файл
                print("Файл транскрибирован")
                # Если файл транскрибирован, смотрим на результат транскрибации
                #if os.path.getsize(cur_file_out_json) < 1:  # Проверка на файл "Internal Server Error". Если размер файла < 21
                #    print(f"    Обнаружен неправилный жисон. Транскрибирую повторно. Override not transcribe agein")
                #    retrascribed += 1
                #    # need_transcribe = True # Если объём жисона 21 байт то аудиофайл необходимо транскрибировать
                #else:
                #    print(f"Обнаружен жисон. Пропускаю файл")
                #    # os.remove(f"{file}")
                #    skipped += 1
                #    # Если размер жисона > 30 байту то транскрибация не нужна
            else: #Если файл не транскрибирован
                if os.path.isfile(cur_file_lock): # Проверяем наличие файла блокировки
#                    print(f"Обнаружен файл блокировки. Файл уже транскрибируется другим потоком")
                    skipped += 1
                else: # Если файл блокировки не обнаружен
                    need_transcribe = True  # Помечаем файл для транскрибации
        else: # Если файл не обнаружен
            not_found += 1
            # Ничего не делаем
            print(f"Целевой файл не обнаружен - пропускаю")

        # Если таки транскрибация нужна
        ready_to_upload = False # Помечаем файл неготовым к транскрибации

        if need_transcribe: # Если файл помечен готовым к транскрибации
#            print(f"Отправляю файл {file} на транскрибацию")
            # Создаём файл блокировки, чтобы другие потоки его игнорировали
            lock_file = open(f"{path_out}/{cur_file_name}.lock", "a+")

            # Команда для транскрибации
            transcribe_command = f"curl -s -F 'upload_file=@{file}' {model_addr} -o {path_out}/{cur_file_name}.wav.json"
            print(transcribe_command)


            # REGION - Работа без повторной транскрибации - START
            os.system(transcribe_command) # Отправляем файл на транскрибацию
            lock_file.close()
            os.remove(f"{path_out}/{cur_file_name}.lock")
            ready_to_upload = True
            # REGION - Работа без повторной транскрибации - END
            # while True:
            #     # Засекаем время
            #     transcribe_start = time.time()  # Таймер начала обработки
            #     # Отправляем файл в апишечку
            #     os.system(transcribe_command)
            #     # Замеряем время
            #     transcribe_stop = time.time()
            #     #               if os.path.getsize(cur_file_out_json) > 30: # Если получившийся жисон больше 21 байта
            #     if os.path.getsize(cur_file_out_json) > 1:  # Если получившийся жисон больше 21 байта
            #         counter += 1
            #         cur_file_size = os.path.getsize(file) / 1024 / 1024  # Получаем объём текущего файла
            #         processed_files_size += cur_file_size
            #         avg_file_size = processed_files_size / counter
            #         cur_time_spent = round(transcribe_stop - transcribe_start, 2)
            #         time_spent += cur_time_spent
            #         # print(f"    На обработку текущего файла ушло {cur_time_spent}s; Среднее время обработки {round(time_spent / counter,2)}s; Обработка идёт: {round(time.time() - time_from_start,2)}s")
            #         lock_file.close()
            #         #		    Удаляем файл блокировки в пасауте
            #         os.remove(f"{path_out}/{cur_file_name}.lock")
            #         #		    Удаляем исходный файл из пасина
            #         #                    os.remove(f"{file}")
            #         ready_to_upload = True
            #         break;  # прерываем текущий цикл
            #     else:
            #         print(f"Проблемы транскрибации, os.path.getsize(cur_file_out_json) = {os.path.getsize(cur_file_out_json)}")
            # print(f"    Неудачная транскрибация - повторно транскрибирую файл")

        if ready_to_upload:
#            print(f"ЗАГРУЖАЮ!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # Конвертируем вав в 16 бит 8к
            # Команда конвертации текущего wav в 16 бит 8 КГц, два канала
            convert_wav_command = f"sox {file} -t wav -b 16 -r 8000 -c 2 {path_out}/{cur_file_name}.wav"
            print(convert_wav_command)

            os.system(convert_wav_command)


            # Потрошим имя файла на составляющие
            # 20210615!035842!89622230325!GOSUSLUGI_1LP!W1_CEK_068!571C6166-CDE6-84A4-74FF-0407AB7D60D1!cvx-1-4-1637006189.314404!0.wav
            cur_file_name_array = cur_file_name.split("!")
            adate = cur_file_name_array[0] # Дата в своём исходном формате 20210615
            ayyyy = adate[0:4] # Часть даты содержащая год. 2021
            amm = adate[4:6] # Часть даты содержащая месяц. 06
            add = adate[6:8] # Часть даты содержащая номер дня. 15
            atime = cur_file_name_array[1] # Время начала диалога в своём исходном формате 035842
            # ahour = str(int(atime[0:2])+3).zfill(2) #Если нужно изменять время взятое из названия файла НЕ с помощью указания часового пояса
            ahour = atime[0:2] # Часть даты содержащая номер часа. 03
            aminute = atime[2:4] # Часть даты содержащая номер минуты. 58
            asecond = atime[4:6] # Часть даты содержащая номер секунды. 42
            atime_offset = "00:00" # Смещение по часовому поясу. В названии файла отсутствует
            telephone = cur_file_name_array[2] # Номер телефона. 89622230325
            operator = cur_file_name_array[4] # Оператор. GOSUSLUGI_1LP
            group = cur_file_name_array[3] # Группа операторов. W1_CEK_068
            session_id = cur_file_name_array[5] # ID сессии. 571C6166-CDE6-84A4-74FF-0407AB7D60D1
            global_id = cur_file_name_array[6] # ID глобальный. cvx-1-4-1637006189.314404
            call_score = cur_file_name_array[7] # Оценка. 0
            # print(f"{adate}")
            #print(f"{ahour}")
            #print(f"{aminute}")
            #print(f"{asecond}")
            # print(f"{adate[6:8]}")
            # os.system
            # -c="{'custom.global_id':'cvx-1-3-1636433304'}"
            # -c="{\"custom.global_id\":\"cvx-1-3-1636433304\"}"

            # Директория куда будет перемещён файл и жисон после окончания транскрибации
            cur_file_new_dir = f"{safe_directory}{ayyyy}/{amm}/{add}"


            # Переменная в которую пишутся кастом параметры.
            custom_parameter_json = '-c="' + '{' \
                                             '\\"' + str('custom.global_id') + '\\":\\"{0}'.format(global_id) + '\\", ' \
                                             '\\"' + str('custom.call_score') + '\\":\\"{0}'.format(call_score) \
                                    + '\\"}' + '"'

            upload2index_command = f'/root/upload2index.sh -a=@{path_out}/{cur_file_name}.wav -j={path_out}/{cur_file_name}.wav.json -p=default_ru-ru -i={session_id} -e=spa_611e26829a74caecb0a9b576 -s={adate[0:4]}-{adate[4:6]}-{adate[6:8]}T{ahour}:{aminute}:{asecond}+{atime_offset} -t={telephone} -o={operator} -g={group} -x=https://192.168.130.183:8081/indexer/api/v1/upload -w=http://192.168.130.183:9236/bert/predict3 {custom_parameter_json}'
            print(upload2index_command)
            os.system(upload2index_command)
            # T${time:0:2}:${time:2:2}:${time:4:2}+00:00 -t=${filename[2]} -o=${filename[4]} -g=${filename[3]} -x=https://192.168.130.183:8081/indexer/api/v1/upload

            # if not os.path.isdir(path_in):

            os.makedirs(cur_file_new_dir, mode=0o777, exist_ok=True)
            # Перемещаем файлы в папку для хранения
#            shutil.move(f"{path_out}/{cur_file_name}.wav", f"{cur_file_new_dir}/{cur_file_name}.wav") # Перемещаем файл который отправлялся на транскрибацию в сейф
            print(f"Перемещаю исходный аудиофайл {file} на новое место {cur_file_new_dir}/{cur_file_name}.wav")
            shutil.move(f"{file}", f"{cur_file_new_dir}/{cur_file_name}.wav") # Перемещаем исходный файл в сей
            print(f"Перемещаю жисон {path_out}/{cur_file_name}.wav.json на новое место {cur_file_new_dir}/{cur_file_name}.wav.json")
            shutil.move(f"{path_out}/{cur_file_name}.wav.json", f"{cur_file_new_dir}/{cur_file_name}.wav.json")
            # Удаляем
#            os.remove(f"{file}") # Удаляем исходный файл
            print(f"Удаляю результирующий аудиофайл {path_out}/{cur_file_name}.wav")
            os.remove(f"{path_out}/{cur_file_name}.wav") # Удаляем аудиофайл который отправлялся на транскрибацию
        #print(
        #    f" Не обнаружено файлов:{not_found}; Пропущено файлов:{skipped}; Обработано файлов:{counter}; \n Средний объём файла:{round(avg_file_size, 2)}mb; Обработано данных: {round(processed_files_size, 2)}; \n Выполнение задачи:{round(counter / total_files, 2)}")
    return True

def merge_audio(path_in, path_out, input_file_extension='.wav', output_file_extension='.wav',
                output_codec_parm='-codec:a pcm_mulaw -ar 8000 -ac 2'):
    print(f"Исходный путь: {path_in}")
    # Проверка исходного пути
    if not os.path.isdir(path_in):  # Проверить наличие исходного пути
        print(f"Исходный путь не обнаружен")
        exit  # Выходим
    print(f"Исходный путь обнаружен")

    file_list = get_files_in_dir(path_in, input_file_extension)  # Получить список файлов в директории
    if len(file_list) == 0:  # Если файлов 0
        print(f"В папке {path_in} не обнаружено файлов с расширением {input_file_extension}")
        exit  # Выходим

    print(f"Путь назначения: {path_out}")
    if not os.path.isdir(path_out):
        print(f"Путь назначения не обнаружен")
        exit
    print(f"Путь назначения обнаружен")

    print(f"В папке {path_in} обнаружено {len(file_list)} файлов с расширением {input_file_extension}")
    print("Начинаю мержить файлы")

    counter = -1  # счётчик обработанных файлов
    processed_files_size = 0  # Объём обработанных данных в Мб
    total_files = len(file_list)  # Количество проверяемых файлов
    # retrascribed = 0
    skipped = 0
    not_found = 0
    avg_file_size = 0
    time_spent = 0
    time_from_start = time.time()
    processed_files = []
    for file in file_list:  # Перебираем все файлы
        counter += 1
        cur_file_name = file.split("/")[-1].split(".")[0]  # Получаем имя файла без расширения
        print(f"Отправляю на обраотку: {file}")
        new_file_name = cur_file_name[:-5]  # Получаем имя будущего файла без расширения
        cur_new_file_left = False  # Путь до файла с каналом оператора
        cur_new_file_right = False  # Путь до файла с каналом клиента
        if not os.path.isfile(
                f"{path_out}/{new_file_name}{output_file_extension}"):  # Смотрим в конечной папке результирующий двухканальный файл
            # Если результирующий файл не найден
            if not new_file_name in processed_files:
                # Каждый файл который мы обрабатываем, надо поместить в массив с именами файлов которые будут исключаться из дальнейших проверок.
                # Таким образом найдя первый файл с одним из каналов диалога, мы добавим его в массив и проверим следующие 10 файлов
                # Таким образом найтя второй канал диалога, расположенный на теоретической позиции N+1.
                # Когда же мы закончим работу с текущим файлом и перейдём по порядку на следующий файл, то обнаружив там снова вторую часть уже
                # По факту обработанного диалога, мы найдём его имя в массиве и пропустим этот файл т.к. он уже либо не подошёл либо уже обработан.
                processed_files.append(new_file_name)
            else:
                print(f"Диалог {new_file_name} уже обрабатывался, пропускаю")
                # counter += 1
                continue;

            print(
                f'Файл {new_file_name}{output_file_extension} не обнаружен в папке назначения. Приступаю к поиску файлов с аудиоканалами')
            for i in range(counter,
                           counter + 10):  # Смотрим в нижеидущих по списку файлах файлы у которых в названии есть {new_file_name}
                # print(f"Файл из диапазона: {file_list[i]}")
                if new_file_name in file_list[i]:
                    # Критерии определения ху из ху
                    print(f"Файл подходящий по маске: {file_list[i]}, последние цифры {file_list[i][-8:-4]}")
                    if int(file_list[i][-8:-4]) > 999 and int(file_list[i][-8:-4]) < 1999:
                        print(f"Обнаружен аудиоканал оператора")
                        cur_new_file_left = file_list[i]
                    #                    elif int(file_list[i][-8:-4]) > 4999 and int(file_list[i][-8:-4]) < 5050:
                    #                        print(f"Обнаружен аудиоканал оператора")
                    #                        cur_new_file_left = file_list[i]
                    elif int(file_list[i][-8:-4]) > 5050 and int(file_list[i][-8:-4]) < 5999:
                        print(f"Обнаружен аудиоканал клиента")
                        cur_new_file_right = file_list[i]
                    elif int(file_list[i][-8:-4]) > 3999 and int(file_list[i][-8:-4]) < 4999:
                        # Если нам попался файл где есть автоответчик - значит пропускаем данный диалог
                        print(f"Обнаружен признак автоответчика, пропускаю данный диалог")
                        skip = True
                        break
            # if skip: break
            if cur_new_file_left and cur_new_file_right:  # Если оба канала текущего диалога найдены
                print(f"Оба канала найдены. Приступаю к склейке: \n {cur_new_file_left} \n {cur_new_file_right}")
                cur_command = f"/home/sagutdinov/ffmpeg-4.4-amd64-static/ffmpeg -i {cur_new_file_left} -i {cur_new_file_right} -filter_complex '[0:a][1:a]amerge=inputs=2[a]' -map '[a]' {output_codec_parm} {path_out}/{new_file_name}{output_file_extension}"
                print(f"Команда: \n {cur_command}")
                os.system(cur_command)

            cur_new_file_left = False  # Путь до файла с каналом оператора
            cur_new_file_right = False  # Путь до файла с каналом клиента
            # counter += 1

    return True


# Переименовывает файлы по захардкоденному алгоритму
def rename_files(path_in, path_out):
    file_list = os.listdir(path_in)  # Смотрим список файлов в текущей директории
    print(file_list)
    if len(file_list) == 0:  # Если файлов 0
        print(f"В папке {path_in} не обнаружено файлов")
        exit  # Выходим
    for i in range(len(file_list)):  # Перебираем все файлы
        print(file_list[i])
        cur_file_name = file_list[i].split("!")  # Разбиваем имя файла по делиметру
        print(cur_file_name)
        new_file_name = f"{cur_file_name[0]}{cur_file_name[1]}!{cur_file_name[2]}!{cur_file_name[3]}!{cur_file_name[4]}!{cur_file_name[5]}"  # Собираем новое имя файла
        print(new_file_name)
        os.rename(f"{path_in}/{file_list[i]}", f"{path_out}/{new_file_name}")  # Переименовываем файл


def correct_files_ext(path_in, path_out):
    file_list = os.listdir(path_in)  # Смотрим список файлов в текущей директории
    print(file_list)
    if len(file_list) == 0:  # Если файлов 0
        print(f"В папке {path_in} не обнаружено файлов")
        exit  # Выходим
    for i in range(len(file_list)):  # Перебираем все файлы
        print(file_list[i])
        cur_file_name = file_list[i].split(".")  # Разбиваем имя файла по делиметру
        print(cur_file_name)
        new_file_name = f"{cur_file_name[0]}.wav.json"  # Собираем новое имя файла
        print(new_file_name)
        os.rename(f"{path_in}/{file_list[i]}", f"{path_out}/{new_file_name}")  # Переименовываем файл


# Коонвертирую жисоны в csv
def convert_json_to_csv(path_in, path_out, input_file_extension=".json"):
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
            data = myfile.read()
        obj = json.loads(data)
        d = {'start': 0, 'cid': 0, 'text': ['a']}
        df = pd.DataFrame(data=d)
        for i in obj:
            for j in obj[i]['metadata']['smoothed']:
                test = {'start': j['start'], 'cid': j['cid'], 'text': j['text']}
                df = df.append(test, ignore_index=True)

        df = df.drop(0)
        df = df.sort_values(by=['start'])
        df.drop(['start'], axis=1, inplace=True)
        new_csv = f"{path_out}/{cur_file_name}.tsv"
        df.to_csv(new_csv, sep="	", index=False, encoding='utf8')
        print(f"Обработано шт:{counter}; Выполнение задачи: {counter / total_files}")
        counter += 1


def get_files_in_dir(path_in, mask):
    file_list = []  # Результирующий список обнаруженных файлов
    for file in sorted(os.listdir(path_in)):
        if file.endswith(mask):
            file_list.append(os.path.join(path_in, file))

    return file_list


if sys.argv[1] == '-transcribe':
    print("транскрибируем вавы")
    print(f"папка с откуда брать файлы {sys.argv[2]}")
    print(f"папка куда класть файлы {sys.argv[3]}")
    transcribe(sys.argv[2], sys.argv[3])
#    if sys.argv[4] == '--remote':
#        get_remote_file(5,6)
elif sys.argv[1] == '-convert':
    print("конвертируем жисоны")
    convert_json_to_csv(sys.argv[2], sys.argv[3])
elif sys.argv[1] == '-merge':
    print("мержим треки")
    merge_audio(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
elif sys.argv[1] == '-rename':
    print(f"переименовываем файлы")
    print(f"папка откуда брать файлы {sys.argv[2]}")
    print(f"папка куда класть файлы {sys.argv[3]}")
    rename_files(sys.argv[2], sys.argv[3])
elif sys.argv[1] == '-correct_ext':
    print(f"zameniajem extensioni na wav.json")
    print(f"папка откуда брать файлы {sys.argv[2]}")
    print(f"папка куда класть файлы {sys.argv[3]}")
    correct_files_ext(sys.argv[2], sys.argv[3])
elif sys.argv[1] == '-multi_transcribe':
    #    multi_transcribe(path_in, path_out, input_file_extension='.wav', output_file_extension='.wav.json', threads=3, model_addr='http://localhost:8091/api/v2/stt/ru
    multi_transcribe(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7])
elif sys.argv[1] == '-pick_audio':
    # (path_in, path_out, input_file_extension='.wav', each=10):
    print(f"Исходная папка {sys.argv[2]}")
    print(f"Папка назначения {sys.argv[3]}")
    print(f"Расширение обрабатываемых файлов: {sys.argv[4]}")
    print(f"Будет производиться отбор каждого {sys.argv[5]} файла")
    pick_audio(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
elif sys.argv[1] == '-help':
    print("Скармливаемые скрипту папки должны существовать.")
    print("Для распознавания используйте команду:")
    print(
        " python3 stt_transcriber.py -transcribe полный/путь/до/папки/с/аудиофайлами полный/до/папки/назначения/жисонов")
    print(" Пример: python3 stt_transcriber.py -transcribe /home/adminguide/audio /home/adminguide/json")
    print("Для конвертации используйте команду")
    print(" python3 stt_transcriber.py -convert полный/путь/до/папки/содержащей/жисоны полный/до/папки/назначения/цсв")
    print(" Пример: python3 stt_transcriber.py -convert /home/adminguide/json /home/adminguide/csv")
    print("Для переименоваяни файлов используйте команду")
    print(" python3 stt_transcriber.py -rename /home/adminguide/files /home/adminguide/files")
    print(" алгоритм переименования необходимо руками править в функции rename_files")
