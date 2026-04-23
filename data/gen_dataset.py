"""Generate hotpot_100.json with 100 multi-hop QA examples."""
import json, random
from pathlib import Path

TEMPLATES = [
    # (question, gold, ctx1_title, ctx1_text, ctx2_title, ctx2_text, difficulty)
    ("Which river flows through {city}?", "{river}",
     "{person}", "{person} was born in {city}.",
     "{city}", "{city} is crossed by the {river}.", "medium"),
    ("What ocean borders the country whose capital is {capital}?", "{ocean}",
     "{capital}", "{capital} is the capital of {country}.",
     "{country}", "{country} borders the {ocean}.", "medium"),
    ("Which mountain range contains the highest peak in {country}?", "{range}",
     "{country}", "{country}'s capital is {capital}.",
     "{peak}", "{peak} in {country} is part of the {range}.", "hard"),
    ("What language family does the official language of {country} belong to?", "{family}",
     "{country}", "The official language of {country} is {language}.",
     "{language}", "{language} is a {family} language.", "medium"),
    ("What instrument did the composer of {work} mainly play?", "{instrument}",
     "{work}", "{work} was composed by {composer}.",
     "{composer}", "{composer} was a virtuoso {instrument} player.", "easy"),
]

DATA = [
    # city, river, person
    dict(city="Paris", river="Seine", person="Victor Hugo", capital="Paris", country="France",
         ocean="Atlantic Ocean", range="Alps", peak="Mont Blanc", language="French", family="Romance",
         work="Les Misérables", composer="Hector Berlioz", instrument="guitar"),
    dict(city="Vienna", river="Danube", person="Mozart", capital="Vienna", country="Austria",
         ocean="Atlantic Ocean", range="Alps", peak="Grossglockner", language="German", family="Germanic",
         work="The Magic Flute", composer="Mozart", instrument="piano"),
    dict(city="Cairo", river="Nile", person="Naguib Mahfouz", capital="Cairo", country="Egypt",
         ocean="Indian Ocean", range="Atlas Mountains", peak="Mount Catherine", language="Arabic", family="Semitic",
         work="Palace Walk", composer="Umm Kulthum", instrument="oud"),
    dict(city="Rome", river="Tiber", person="Galileo", capital="Rome", country="Italy",
         ocean="Mediterranean Sea", range="Apennines", peak="Gran Sasso", language="Italian", family="Romance",
         work="The Four Seasons", composer="Vivaldi", instrument="violin"),
    dict(city="Moscow", river="Moskva", person="Tolstoy", capital="Moscow", country="Russia",
         ocean="Arctic Ocean", range="Ural Mountains", peak="Mount Elbrus", language="Russian", family="Slavic",
         work="War and Peace", composer="Tchaikovsky", instrument="piano"),
    dict(city="Beijing", river="Yangtze", person="Confucius", capital="Beijing", country="China",
         ocean="Pacific Ocean", range="Himalayas", peak="Mount Everest", language="Mandarin", family="Sino-Tibetan",
         work="The Yellow River Cantata", composer="Xian Xinghai", instrument="erhu"),
    dict(city="Tokyo", river="Sumida", person="Matsuo Basho", capital="Tokyo", country="Japan",
         ocean="Pacific Ocean", range="Japanese Alps", peak="Mount Fuji", language="Japanese", family="Japonic",
         work="The Four Seasons", composer="Toru Takemitsu", instrument="biwa"),
    dict(city="London", river="River Thames", person="Ada Lovelace", capital="London", country="United Kingdom",
         ocean="Atlantic Ocean", range="Pennines", peak="Ben Nevis", language="English", family="Germanic",
         work="Messiah", composer="Handel", instrument="harpsichord"),
    dict(city="Madrid", river="Manzanares", person="Cervantes", capital="Madrid", country="Spain",
         ocean="Atlantic Ocean", range="Pyrenees", peak="Mulhacén", language="Spanish", family="Romance",
         work="Don Quixote", composer="Manuel de Falla", instrument="guitar"),
    dict(city="Lisbon", river="Tagus", person="Fernando Pessoa", capital="Lisbon", country="Portugal",
         ocean="Atlantic Ocean", range="Serra da Estrela", peak="Torre", language="Portuguese", family="Romance",
         work="Fado", composer="Amália Rodrigues", instrument="guitar"),
    dict(city="Amsterdam", river="Amstel", person="Rembrandt", capital="Amsterdam", country="Netherlands",
         ocean="North Sea", range="Ardennes", peak="Vaalserberg", language="Dutch", family="Germanic",
         work="The Night Watch", composer="Jan Sweelinck", instrument="organ"),
    dict(city="Brussels", river="Senne", person="René Magritte", capital="Brussels", country="Belgium",
         ocean="North Sea", range="Ardennes", peak="Signal de Botrange", language="French", family="Romance",
         work="The Treachery of Images", composer="César Franck", instrument="organ"),
    dict(city="Warsaw", river="Vistula", person="Chopin", capital="Warsaw", country="Poland",
         ocean="Baltic Sea", range="Carpathians", peak="Rysy", language="Polish", family="Slavic",
         work="Nocturnes", composer="Chopin", instrument="piano"),
    dict(city="Prague", river="Vltava", person="Kafka", capital="Prague", country="Czech Republic",
         ocean="North Sea", range="Sudetes", peak="Sněžka", language="Czech", family="Slavic",
         work="The Metamorphosis", composer="Dvořák", instrument="viola"),
    dict(city="Budapest", river="Danube", person="Liszt", capital="Budapest", country="Hungary",
         ocean="Black Sea", range="Carpathians", peak="Kékes", language="Hungarian", family="Uralic",
         work="Hungarian Rhapsodies", composer="Liszt", instrument="piano"),
    dict(city="Athens", river="Ilissos", person="Socrates", capital="Athens", country="Greece",
         ocean="Mediterranean Sea", range="Pindus", peak="Mount Olympus", language="Greek", family="Hellenic",
         work="Oedipus Rex", composer="Mikis Theodorakis", instrument="bouzouki"),
    dict(city="Istanbul", river="Bosphorus", person="Orhan Pamuk", capital="Ankara", country="Turkey",
         ocean="Black Sea", range="Taurus Mountains", peak="Mount Ararat", language="Turkish", family="Turkic",
         work="My Name Is Red", composer="Zeki Müren", instrument="oud"),
    dict(city="Tehran", river="Karaj", person="Omar Khayyam", capital="Tehran", country="Iran",
         ocean="Indian Ocean", range="Alborz", peak="Mount Damavand", language="Persian", family="Indo-Iranian",
         work="Rubaiyat", composer="Mohammad Reza Shajarian", instrument="setar"),
    dict(city="Delhi", river="Yamuna", person="Rabindranath Tagore", capital="New Delhi", country="India",
         ocean="Indian Ocean", range="Himalayas", peak="Kangchenjunga", language="Hindi", family="Indo-Aryan",
         work="Gitanjali", composer="Ravi Shankar", instrument="sitar"),
    dict(city="Bangkok", river="Chao Phraya", person="King Bhumibol", capital="Bangkok", country="Thailand",
         ocean="Pacific Ocean", range="Dawna Range", peak="Doi Inthanon", language="Thai", family="Kra-Dai",
         work="Royal Compositions", composer="King Bhumibol", instrument="saxophone"),
]

random.seed(42)
records = []
qid = 1
difficulties = ["easy", "medium", "hard"]

for d in DATA:
    for tmpl_q, tmpl_a, t1, c1, t2, c2, diff in TEMPLATES:
        try:
            question = tmpl_q.format(**d)
            gold = tmpl_a.format(**d)
            ctx1_title = t1.format(**d)
            ctx1_text = c1.format(**d)
            ctx2_title = t2.format(**d)
            ctx2_text = c2.format(**d)
        except KeyError:
            continue
        records.append({
            "qid": f"hp{qid:03d}",
            "difficulty": diff,
            "question": question,
            "gold_answer": gold,
            "context": [
                {"title": ctx1_title, "text": ctx1_text},
                {"title": ctx2_title, "text": ctx2_text},
            ]
        })
        qid += 1
        if len(records) >= 100:
            break
    if len(records) >= 100:
        break

out = Path(__file__).parent / "hotpot_100.json"
out.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Generated {len(records)} records → {out}")
