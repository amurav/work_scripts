#!/usr/bin/bash

mkdir -p output

for file in `find ./100_audio/ | grep .wav`;
do
   filename=`echo $file | cut -d '.' -f 1-4` 
   filename=`echo $filename | cut -d '/' -f 3` 
   echo $file $filename
   curl -k --data-binary "@$file" -H "Transfer-Encoding: chunked" -H "Content-Type: audio/x-pcm; rate=8000" -H "Host: e2e-basic.uz-UZ" "https://192.168.90.50:443" > output/"$filename".xml
   ### for using e2e-general - use command below: ###
   # curl -k --data-binary "@audio.wav" -H "Transfer-Encoding: chunked" -H "Content-Type: audio/x-pcm; rate=8000" -H "Host: e2e_general.ru-RU" "https://asr04.voice.bssys.com:445"

done



