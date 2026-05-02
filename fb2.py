import torch
import xml.etree.ElementTree as ET
import re
from num2words import num2words
from transliterate import translit
from fb2reader import fb2book
import os
from pydub import AudioSegment


local_file_tts = 'v5_ru.pt'
device = torch.device('cpu')
torch.set_num_threads(16)
sample_rate = 24000 # v4_ru 8000, 24000, 48000
speaker = 'xenia' # baya, kseniya
put_accent = True
put_stress = True
put_yo = True
put_stress_homo = True
put_yo_homo = True

prefix_name = "antikrizisniy_aktiv" # название серии
books = [
    "kolonist_vano.fb2",
    "zagonnaya_okhota.fb2",
    "centr_sily.fb2",
    "gorodmechta.fb2",
    "druzhba_narodov.fb2",
    "yapona_osen.fb2",
    "zimnie_khodoki.fb2",
    "zlovonyuchaya_dolina.fb2",
    "volchij_chas.fb2"
  ]


def tts(text, index):
    for glava in range(len(text)):
        for line in range(len(text[glava])):
            filename_wav = f'wav/{prefix_name}_{str(index+1).zfill(2)}_{str(glava).zfill(2)}_{str(line).zfill(5)}.wav'
            if not os.path.exists(filename_wav):
                print ("Книга",index+1)
                print ("Глава",glava,"из", len(text)-1)
                print ("Cтрока", line, "из", len(text[glava])-1, "длина строки", len(text[glava][line])-1)
                print (text[glava][line])
                ssml_sample = "<speak>"+text[glava][line]+"</speak>"
                audio_paths = model_tts.save_wav(ssml_text=ssml_sample,
                                                speaker=speaker,
                                                sample_rate=sample_rate,
                                                put_accent=put_accent,
                                                put_yo=put_yo,
                                                put_stress_homo=put_stress_homo,
                                                put_yo_homo=put_yo_homo)
                os.rename(audio_paths, filename_wav)
                print(filename_wav,'\n')

def text_enhancement(text):
    print(text)
    text = re.sub(r'(?:<p>)(.{400,}[.!?])?(.{400,}?)(?:</p>)', r'\1</p>\n<p>\2', text, re.DOTALL)
    text = re.sub(r'<p/>|<body>|</body>|<section>', '', text) # удаляю лишнии теги
    text = re.sub(r'\s+', ' ', text) # все переводы строки, табы, пробелы... заменяю на пробел.
    text = re.sub(r'(<image ).+(/>)', '', text) # удаляю тег картинки
    text = re.sub(r'<p>', r'<s>', text) # уменьшаю паузы. заменяю главы на предложения
    text = re.sub(r'</p>', r'</s>', text)
    text = re.sub(r'<title>', r'<prosody pitch="x-low">', text) # меняю озвучку
    text = re.sub(r'<strong>', r'<prosody pitch="x-low">', text)
    text = re.sub(r'<emphasis>', r'<prosody pitch="low">', text)
    text = re.sub(r'</strong>|</emphasis>|</title>', r'</prosody>', text) # закрываю тег озвучки
    # тут ошибка порядка тегов. Название книги и глава. Меняю местами теги.
    text = re.sub(r'</s> </prosody>', '</prosody> </s>', text)
    text = re.sub(r'<prosody pitch="x-low"> <s>', '\n<s> <prosody pitch="x-low">', text)
    text = re.sub(r'[.]{2,}', '…', text) # заменяю точки подряд на многоточие
    text = re.sub(r' <', '<', text) # удаляю пробелы между тегами
    text = re.sub(r'> ', '>', text)
    text = re.sub(r'<', '\n<', text) # делаю красиво, перенос строки перед и после тега
    text = re.sub(r'>', '>\n', text)
    text = re.sub(r'\n\n', '\n', text) # заменяю 2 перевода строки на 1

    # разбиваю длинные цифры на куски до 18. нумерация не знает такие большие буквы
    text = re.sub(r'(\d{1,18})(\d{1,18})(\d{1,18})',r'\1 \2 \3', text)
    # если в строке есть цифра, заменяю ее на слово.
    text = re.sub(r'(\d+)',lambda x: num2words(int(x.group(0)),lang='ru'), text)
    # читалка только руские читает. делаю транслит. если не в   .
    text = re.sub(r'(!<)([a-z|A-Z])+((!>))',lambda x: translit(x.group(0), 'ru'), text)
    text = re.sub(r'<s>[^а-яА-ЯёЁ]+</s>', '', text) # удаляю строки без букв.

    # делю длинны строки на 2.
    # text = re.sub(r'(?:<s>)(.{400,})[.!?](.{400,})(?:</s)', r'\1</s><s>\2', text)

    # растановка ударений
    text = re.sub(r'потом[.!?,\s]', 'пот+ом', text)
    text = re.sub(r'Листова И.А.', 'Л+истова И.А.', text)

    print(text)

    # делю на главы
    glavs = re.split('</section>', text)
    glavs.pop(len(glavs)-1) # последнее добавление лишнее.
    # делю на строки
    text = []
    for glava in glavs:
        glava = re.sub(r'^\n', '', glava)
        # делю на строки
        row = re.split('</s>', glava)
        for i in range(len(row)):
            # удаляю перевод строки после сплита.
            row[i] = re.sub(r'\n<s>', '<s>', row[i])
            row[i] = row[i] +"</s>" # добавляю обратно конец предложения.
        row.pop(len(row) -1) # последнее добавление лишнее.
        text.append(row)

    # strong <prosody pitch="low">
    # emphasis <prosody pitch="high">
    # <prosody rate="low">я говорю довольно медленно</prosody> x-slow, slow, medium, fast, x-fast
    # <prosody pitch="high">а могу говорить тоном выше</prosody> x-low, low, medium, high, x-high, robot
    return text


def save_ogg(text, index):
    combined = AudioSegment.empty()
    for glava in range(len(text)): # цикл по главам
        filename_ogg = f'ogg/{prefix_name}_{str(index+1).zfill(2)}_{str(glava).zfill(2)}.ogg'
        print(filename_ogg)
        if (not os.path.exists(filename_ogg)) or (os.path.getsize(filename_ogg) == 0): # есть ли уже файл ogg
            for line in range(len(text[glava])): # цикл по строкам.
                filename_wav = f'wav/{prefix_name}_{str(index+1).zfill(2)}_{str(glava).zfill(2)}_{str(line).zfill(5)}.wav'
                combined = combined + AudioSegment.from_file(filename_wav, format='wav')

            combined.export(filename_ogg, format='ogg', bitrate="32k",
                           tags={"album": title, "artist": authors[0]['full_name'], \
                           "genre": tags, "tracknumber": str(glava).zfill(2), \
                           "comment": description, "series": series})
            combined = AudioSegment.empty()
            print(os.path.getsize(filename_ogg))


# загружаю модель
model_tts = torch.package.PackageImporter(local_file_tts).load_pickle("tts_models", "model")
model_tts.to(device)

# for i in range(0, 1):
for i in range(len(books)):
    print ('читаю книгу')
    print (i,f'book/{books[i]}')
    book = fb2book(f'book/{books[i]}')
    body = book.get_body()

    print ('\n''стартую обработку текста')
    body = text_enhancement(body)
    # print(body)

    # Get book metadata
    title = book.get_title()
    authors = book.get_authors()
    description = book.get_description()
    series = book.get_series()
    lang = book.get_lang()
    tags = book.get_tags()

    # print(f"Title: {title}")
    # print(f"Authors: {authors}")
    # print(f"Description: {description}")
    # print(f"Series: {series}")
    # print(f"Lang: {lang}")
    # print(f"Tags: {tags}")

    print ('\n''стартую ттс')
    tts(body, i)

    # print ('\n''Сохраняю по главам ogg')
    # save_ogg(body, i)

    print()
