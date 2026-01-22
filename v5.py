import os
import torch
import re
from num2words import num2words
#from transliterate import translit
from pydub import AudioSegment
#import array

# pip install silero --break-system-packages

local_file_models = 'latest_silero_models.yml'
local_file_tts = 'v5_ru.pt'
# local_file_tts = 'v5_1_ru.pt'
device = torch.device('cpu')
torch.set_num_threads(16)
sample_rate = 24000 # v4_ru 8000, 24000, 48000
speaker = 'xenia' # baya, kseniya
put_accent = True
put_stress = True
put_yo = True
put_stress_homo = True
put_yo_homo = True

# Сначала книгу надо из фб2 сконвертить в текст unoconv -f txt *.fb2
books = [
    "kolonist_vano.txt",
    "zagonnaya_okhota.txt",
    "centr_sily.txt",
    "gorodmechta.txt",
    "druzhba_narodov.txt",
    "yapona_osen.txt",
    "zimnie_khodoki.txt",
    "zlovonyuchaya_dolina.txt",
    "volchij_chas.txt"
  ]
prefix_name = "antikrizisniy_aktiv" # название серии


# очистка текста от мусора. И растнановка ударений.
def text_enhancement(text):
  # цикл по количеству строк
  for i in range(len(text)):
    # правлю текст удаляя и заменя нечитаемые символы
    # если строка больше 3 символов читаю ее. меньше 3 мусор.
    if len(text[i]) > 3:
      text[i] = re.sub(r'\s', ' ', text[i]) # все знаки пробела таб, пробел, конец строки заменяю на пробел.
      text[i] = re.sub(r'[\s]{2,}', ' ', text[i]) # удаляю лишние пробелы
      text[i] = re.sub(r'^\s{1,}', '', text[i]) # удаляю пробелы в начале строки
      text[i] = re.sub(r'\s([\.,!?])', r'\1', text[i]) # удаляю проблел перед знаком припинания
      text_tmp = text[i] # после базовых замен сохраняю временную строку.

      # если в строке есть цифра, заменяю ее на слово.
      text[i] = re.sub(r'(\d+)',lambda x: num2words(int(x.group(0)),lang='ru'), text[i])
      # транслит текста.
      # text[i] = translit(text[i], 'ru')

      text[i] = text[i].replace('*', '-') # читалка * не читает, падает
      # text[i] = text[i].replace(')', ',')
      # text[i] = text[i].replace('—', '-')
      # text[i] = text[i].replace('…', '...')
      # text[i] = re.sub(r'[^а-яА-Я0-9ё\.,!?\s%\’\'\"\-\+\—]', ' ', text[i]) # все что не буквы, знаки припинания и пробелы, заменяю на пробелы

      # показывает разницу что было и что поправило
      if text_tmp != text[i]:
        print (i)
        print (text_tmp)
        print (text[i])

  return text

def tts(text, index):
  # загружаю модель
  model_tts = torch.package.PackageImporter(local_file_tts).load_pickle("tts_models", "model")
  model_tts.to(device)
  # построчно пишет вейвы. 
  for i in range(len(text)):
    filename_wav = f'wav/{prefix_name}_{str(index+1).zfill(2)}_{str(i).zfill(5)}.wav'
    # если строка меньше 3 символов, считаю ее мусором. пеервод строки это тоже символ.
    if len(text[i]) > 3:
      # проверяю есть ли уже файл с озвученой строкой.
      if not os.path.exists(filename_wav):
        print (i, len(text), text[i])
        # https://github.com/snakers4/silero-models/wiki/SSML
        # ssml_sample = "<speak><s>"+text[i]+"</s></speak>"
        # audio_paths = model_tts.save_wav(ssml_text=ssml_sample,

        audio_paths = model_tts.save_wav(text=text[i],
                                        speaker=speaker,
                                        sample_rate=sample_rate,
                                        put_accent=put_accent,
                                        put_yo=put_yo,
                                        put_stress_homo=put_stress_homo,
                                        put_yo_homo=put_yo_homo)

        # Не нашел как передавать имя файла. поэтому переименовываю его в ручную.
        os.rename(audio_paths, filename_wav)
        print (filename_wav,'\n')


def save_ogg(text, index):
  glava = 0
  combined = AudioSegment.empty()
  for i in range(len(text)):
    filename_ogg = f'ogg/{prefix_name}_{str(index+1).zfill(2)}_{str(glava).zfill(2)}.ogg'
    filename_wav = f'wav/{prefix_name}_{str(index+1).zfill(2)}_{str(i).zfill(5)}.wav'

    # если найдена строчка с новой главой. сохраняю старую и очищаю собраный вейв.
    if re.search(r'Глава', text[i]):
      print(filename_ogg)
      glava = glava+1
      if (not os.path.exists(filename_ogg)) or (os.path.getsize(filename_ogg) == 0):
        glava = glava-1
        combined.export(filename_ogg, format='ogg' )
        combined = AudioSegment.empty()
        print(os.path.getsize(filename_ogg))
        glava = glava+1

    # если есть сохраненная строка добавляю ее к собранной главе
    if os.path.exists(filename_wav):
      if (not os.path.exists(filename_ogg)) or (os.path.getsize(filename_ogg) == 0):
        combined = combined + AudioSegment.from_file(filename_wav, format='wav')

  # сохраняю последнюю главу
  if (not os.path.exists(filename_ogg)) or (os.path.getsize(filename_ogg) == 0):
    combined.export(filename_ogg, format='ogg' )
    combined = AudioSegment.empty()
    print(filename_ogg)
    print(os.path.getsize(filename_ogg))


# считает количество глав и строк.
def test(text):
  glava = 0
  glavs = [0]
  for i in range(len(text)):
    if re.search(r'Глава', text[i]):
      glava = glava+1
      glavs.insert(glava,i)
      print(glava,i)
  glavs.remove(0)
  print(glavs)


# основной код
if not os.path.isfile(local_file_tts):
  print ('load tts model', local_file_tts)
  torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v5_ru.pt',local_file_tts)
  # torch.hub.download_url_to_file('https://models.silero.ai/models/tts/ru/v5_1_ru.pt',local_file_tts)

for i in range(len(books)):
  print ('читаю книгу')
  print (i,f'book/{books[i]}')
  file = open(f'book/{books[i]}','r')
  text = file.readlines()
  file.close()

  print ('\n''стартую обработку текста')
  text = text_enhancement(text)
  test(text)

  print ('\n''стартую ттс')
  tts(text, i)

  print ('\n''Сохраняю по главам ogg')
  save_ogg(text, i)

  print ('\n')
