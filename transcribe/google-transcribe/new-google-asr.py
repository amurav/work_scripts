#!/usr/bin/python3

from google.cloud import storage
from google.cloud import speech_v1p1beta1 as speech
from google.protobuf.json_format import MessageToJson
import os, json, concurrent.futures, uuid, argparse, subprocess, shutil
from shutil import copyfile

silenceLength=0.7
maxLengthForWord=4.0
tempDir = '/tmp/gASR/temp'

def getParams():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--diarization',             default=False, action='store_true', help='Enable diarization')
    parser.add_argument('--channels',                default=1, type=int, help='Channels in file')
    parser.add_argument('--language',                default="ru-RU", help='ASR Language')
    parser.add_argument('--threads',                 default=16, type=int, help='Recognition threads')
    parser.add_argument('--remove-bucket-files',     default=False, action='store_true', help='Remove files from bucket if exist')
    parser.add_argument('--enable-punctuation',      default=False, action='store_true', help='Enable automatic punctuation')
    parser.add_argument('--model',                   default="default", help='Which model to select for the given request')

    args = parser.parse_args()
    return args

def createBucket(bucket_name):
    storage_client = storage.Client()
    buckets = storage_client.list_buckets()

    for bucket in buckets:
        if bucket.name == bucket_name:
            return bucket.name

    bucket = storage_client.bucket(bucket_name)
    bucket.storage_class = "STANDARD"
    new_bucket = storage_client.create_bucket(bucket)
    return new_bucket.name


def loadFilesToBucket(files,bucket_name, params):
    print('Uploading files to bucket '+bucket_name+'...')
    os.makedirs('/tmp/gASR/audio', mode=0o777, exist_ok=True)

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    for f in files:
        soxes = [ [ 'sox', 'audio/'+f, '-b', '16', '-r', '8000' ] ]
        if params.channels == 1: # or params.diarization:
            soxes[0].append('-c')
            soxes[0].append('1')
            soxes[0].append('/tmp/gASR/audio/0_'+f)
        elif params.diarization:
            soxes[0].append('/tmp/gASR/audio/0_'+f)
            soxes.append(['sox','/tmp/gASR/audio/0_'+f,'/tmp/gASR/audio/1_'+f,'remix','1'])
            soxes.append(['sox','/tmp/gASR/audio/0_'+f,'/tmp/gASR/audio/2_'+f,'remix','2'])
        for sox in soxes:
            subprocess.call(sox,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL)

        for i in range(len(soxes)):
            if storage.Blob(bucket=bucket, name=str(i)+'_'+f).exists(storage_client):
                if params.remove_bucket_files:
                    storage.Blob(bucket=bucket, name=str(i)+'_'+f).delete()
                    print('deleted: '+ str(i)+'_' + f)
                else:
                    print('exists: '+ str(i)+'_' + f)
                    continue
            blob = bucket.blob(str(i)+'_'+f)
            blob.upload_from_filename('/tmp/gASR/audio/'+str(i)+'_'+f)
            print('uploaded: '+str(i)+'_'+f)


def makeRequest(operation,wav):
    response = operation.result(timeout=300)
    response = speech.types.LongRunningRecognizeResponse.to_dict(response)
    if len(response) > 0:
        json.dump(response,open(wav, 'w' ))
        return 'finished: '+wav
    else:
        return 'error: '+wav


def recognizeFiles(files,bucket_name, params):
    os.makedirs(tempDir, mode=0o777, exist_ok=True)
    client = speech.SpeechClient()
    results = []
    print('recognizing files...')
    fls = []
    for fl in files:
        f = 'audio/'+fl
        if not os.path.isfile(f+'.json') and os.path.isfile(f):
            fls.append(fl)
    if len(fls) == 0:
        print('all files recognized')
        return
    files = fls
    with concurrent.futures.ThreadPoolExecutor(params.threads) as executor:
        for fl in files:
            if params.diarization:
                config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=8000,
                    language_code=params.language,
                    enable_automatic_punctuation=params.enable_punctuation,
                    model=params.model,
                    enable_speaker_diarization=True,
                    diarization_speaker_count=2
                )
                if params.channels == 1:
                    if os.path.isfile(tempDir + '/0_'+fl+'.json'):
                        continue
                    audio = speech.RecognitionAudio(uri='gs://'+bucket_name+'/0_'+fl)
                    operation = client.long_running_recognize(config=config, audio=audio)
                    results.append(executor.submit(makeRequest, operation=operation, wav=tempDir + '/0_'+fl+'.json'))
                else:
                    if os.path.isfile(tempDir + '/1_'+fl+'.json') and os.path.isfile(tempDir + '/1_'+fl+'.json'):
                        continue
                    audio = speech.RecognitionAudio(uri='gs://'+bucket_name+'/1_'+fl)
                    operation = client.long_running_recognize(config=config, audio=audio)
                    results.append(executor.submit(makeRequest, operation=operation, wav=tempDir + '/1_'+fl+'.json'))
                    audio = speech.RecognitionAudio(uri='gs://'+bucket_name+'/2_'+fl)
                    operation = client.long_running_recognize(config=config, audio=audio)
                    results.append(executor.submit(makeRequest, operation=operation, wav=tempDir + '/2_'+fl+'.json'))
            else:
                if os.path.isfile(tempDir + '/0_'+fl+'.json'):
                    continue
                if params.channels == 1:
                    config = speech.RecognitionConfig(
                        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                        sample_rate_hertz=8000,
                        enable_word_time_offsets=True,
                        enable_automatic_punctuation=params.enable_punctuation,
                        model=params.model,
                        language_code=params.language
                    )
                else:
                    config = speech.RecognitionConfig(
                        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                        sample_rate_hertz=8000,
                        enable_word_time_offsets=True,
                        language_code=params.language,
                        enable_automatic_punctuation=params.enable_punctuation,
                        model=params.model,
                        audio_channel_count=2,
                        enable_separate_recognition_per_channel=True
                    )
                operation = client.long_running_recognize(config=config, audio=audio)
                results.append(executor.submit(makeRequest, operation=operation, wav=tempDir + '/0_'+fl+'.json'))

        for future in concurrent.futures.as_completed(results):
            print(future.result())


def makeFilesForSA(files):
    for fl in files:
        channels = { '1': [], '2': [] }
        if not os.path.exists(tempDir + '/1_' + fl + '.json'):
            f = tempDir + '/0_' + fl + '.json'
            if not os.path.exists(f):
                continue
            with open(f) as json_file:
                data = json.load(json_file)
                for result in data['results']:
                    for alternative in result['alternatives']:
                        for word in alternative['words']:
                            if word['speaker_tag'] != 0 and params.diarization:
                                channels[str(word['speaker_tag'])].append({
                                    'start_time': float(word['start_time'].replace('s','')),
                                    'end_time': float(word['end_time'].replace('s','')),
                                    'word': word['word'].lower()
                                })
                            else:
                                channels[str(result['channel_tag'])].append({
                                    'start_time': float(word['start_time'].replace('s','')),
                                    'end_time': float(word['end_time'].replace('s','')),
                                    'word': word['word'].lower()
                                })
        else:
            for i in range(2):
                channel = str(i+1)
                f = tempDir + '/'+channel+'_' + fl + '.json'
                if not os.path.exists(f):
                    continue
                with open(f) as json_file:
                    data = json.load(json_file)
                    for result in data['results']:
                        for alternative in result['alternatives']:
                            for word in alternative['words']:
                                channels[channel].append({
                                    'start_time': float(word['start_time'].replace('s','')),
                                    'end_time': float(word['end_time'].replace('s','')),
                                    'word': word['word'].lower()
                                })
        uid = str(uuid.uuid1())
        result = {
            uid+'_1': {
                'meta': 'outdir/'+uid+'_1/'+uid+'_1_meta.json',
                'chunks': [],
                'cid': '1',
                'metadata': {
                    'raw': [],
                    'smoothed': [],
                    'config': {
                        "fid": uid,
                        "in_dir": "/appl/indir",
                        "out_dir": "/appl/outdir",
                        "tmp_dir": "/appl/tmp",
                        "vad_engine": "smn",
                        "threshold": 15,
                        "thresh2": 17,
                        "thresh3": 10,
                        "thresh4": 19,
                        "width": 30,
                        "aggressiveness": 3,
                        "detect_gender": False,
                        "del_tmp": True,
                        "del_out": False,
                        "verbose": False,
                        "infile": "/appl/indir/"+uid+"/"+uid+"_1.wav"
                    }
                }
            },
            uid+'_2': {
                'meta': 'outdir/'+uid+'_2/'+uid+'_2_meta.json',
                'chunks': [],
                'cid': '2',
                'metadata': {
                    'raw': [],
                    'smoothed': [],
                    'config': {
                        "fid": uid,
                        "in_dir": "/appl/indir",
                        "out_dir": "/appl/outdir",
                        "tmp_dir": "/appl/tmp",
                        "vad_engine": "smn",
                        "threshold": 15,
                        "thresh2": 17,
                        "thresh3": 10,
                        "thresh4": 19,
                        "width": 30,
                        "aggressiveness": 3,
                        "detect_gender": False,
                        "del_tmp": True,
                        "del_out": False,
                        "verbose": False,
                        "infile": "/appl/indir/"+uid+"/"+uid+"_2.wav"
                    }
                }
            }
        }

        for channel in channels:
            words = []
            for i in range(len(channels[channel])):
                word = channels[channel][i]
                words.append(word['word'])
                if i == 0:
                    start_time = word["start_time"]
                end_time = word["end_time"]

                if word["start_time"] - end_time > silenceLength or word["end_time"] - word["start_time"] > maxLengthForWord or i == len(channels[channel]) - 1:
                    result[uid+'_'+channel]['metadata']['raw'].append(["male", start_time, end_time])
                    result[uid+'_'+channel]['metadata']['smoothed'].append({
                        "duration": end_time - start_time,
                        "start": start_time,
                        "end": end_time,
                        "stype": "male",
                        "fname": uid+"_"+channel+"__s"+str(start_time)+"__e"+str(end_time)+".wav",
                        "fpath": "/appl/outdir/"+uid+"/"+uid+"_"+channel+"__s"+str(start_time)+"__e"+str(end_time)+".wav",
                        "cid": "C"+channel,
                        "text": ' '.join(words),
                        "uttid": uid+"_"+channel+"__s"+str(start_time)+"__e"+str(end_time),
                        "denormalized": ' '.join(words),
                        "entities": []
                    })
                    words = []
                    start_time = word["start_time"]
        with open('audio/'+fl+'.json', 'w') as outfile:
            json.dump(result, outfile)



# Getting params from cli
params = getParams()

# Creating bucket if not exists
#bucket = createBucket("safiles")
bucket = createBucket("dskfiles")

# Getting files from dir
files = [f for f in os.listdir('audio') if os.path.isfile('audio/'+f) and f.endswith(".wav") ]

# loading files to bucket
loadFilesToBucket(files,bucket,params)

# Recognizing files
recognizeFiles(files,bucket,params)

# Making files for SA
makeFilesForSA(files)
