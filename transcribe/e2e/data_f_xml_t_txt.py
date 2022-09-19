#!/usr/bin/python3
import xml.etree.ElementTree as ET
import os

DIR='./output/'

with open('ural_e2e-aeb.txt', 'w') as f:
    for root, dirs, files in os.walk(DIR):
        for filename in files:
            print(f'Работаем с {filename}')
            shortfilename=filename[:-4:]
            try:
                tree = ET.parse(DIR+filename)
                root = tree.getroot()
            except ET.ParseError:
                f.write(f'{shortfilename};\n')
            else:
                for get_data in root.iter('SWI_spoken'):
                    data = get_data.text
                    print(f'{shortfilename}\t{data}')
                    f.write(f'{shortfilename};{data}\n')

