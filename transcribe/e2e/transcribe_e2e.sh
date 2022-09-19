#!/usr/bin/bash

if [ -z $1 ]; then
       echo "use $0 directory for run"
       echo "example: $0 wav/"
       exit 1
fi       

mkdir -p output

for file in `find $1 | grep .wav`;
do
   filename=$(basename $file)
   echo "Working with '$file', output filename: $filename.xml"
   # curl -k --data-binary "@$file" -H "Transfer-Encoding: chunked" -H "Content-Type: audio/x-pcm; rate=8000" -H "Host: e2e-tuned.ru-RU" "https://asr04.voice.bssys.com:445" > output/"$filename".xml
   ### for using e2e-general - use command below: ###
   # curl -k --data-binary "@$file" -H "Transfer-Encoding: chunked" -H "Content-Type: audio/x-pcm; rate=8000" -H "Host: e2e_general.ru-RU" "https://asr04.voice.bssys.com:445" > output/"$filename".xml
   curl -k --data-binary "@$file" -H "Transfer-Encoding: chunked" -H "Content-Type: audio/x-pcm; rate=8000" -H "Host: e2e-general-aeb.ru-RU" "https://asr04.voice.bssys.com:445" > output/"$filename".xml

done



