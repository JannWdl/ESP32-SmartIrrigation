"""
plants_db.py – Pflanzendatenbank (ohne Wetteranpassung)
"""

PLANTS = [
    # id, name_de, name_en, emoji, min%, max%, ideal%, dauer_s, interval_h, notiz
    (0,  'Benutzerdefiniert', 'Custom',       '🌱', 20, 80, 50, 30, 6,  ''),
    (1,  'Tomate',            'Tomato',        '🍅', 45, 80, 65, 45, 8,  'Viel Wasser'),
    (2,  'Basilikum',         'Basil',         '🌿', 50, 80, 65, 20, 6,  'Gleichmäßig feucht'),
    (3,  'Kaktus',            'Cactus',        '🌵', 5,  30, 15, 10, 72, 'Sehr selten gießen'),
    (4,  'Sukkulente',        'Succulent',     '🪴', 10, 35, 20, 10, 48, 'Staunässe vermeiden'),
    (5,  'Lavendel',          'Lavender',      '💜', 15, 45, 30, 20, 24, 'Trockenheit bevorzugt'),
    (6,  'Rose',              'Rose',          '🌹', 40, 75, 55, 40, 12, 'Regelmäßig gießen'),
    (7,  'Erdbeere',          'Strawberry',    '🍓', 50, 80, 65, 35, 8,  'Nie austrocknen'),
    (8,  'Paprika',           'Bell Pepper',   '🫑', 45, 75, 60, 40, 10, 'Gleichmäßig feucht'),
    (9,  'Minze',             'Mint',          '🌿', 55, 85, 70, 25, 6,  'Immer feucht'),
    (10, 'Orchidee',          'Orchid',        '🌸', 30, 50, 40, 15, 48, 'Staunässe schädlich'),
    (11, 'Farn',              'Fern',          '🌿', 60, 90, 75, 30, 6,  'Hohe Luftfeuchtigkeit'),
    (12, 'Efeutute',          'Pothos',        '🌿', 30, 60, 45, 20, 12, 'Robust'),
    (13, 'Grünlilie',         'Spider Plant',  '🌿', 35, 65, 50, 20, 12, 'Pflegeleicht'),
    (14, 'Einblatt',          'Peace Lily',    '🤍', 45, 75, 60, 25, 8,  'Hängende Blätter = Durst'),
    (15, 'Aloe Vera',         'Aloe Vera',     '🌵', 10, 30, 20, 15, 48, 'Sehr selten gießen'),
    (16, 'Salat',             'Lettuce',       '🥬', 60, 90, 75, 30, 4,  'Immer feucht'),
    (17, 'Gurke',             'Cucumber',      '🥒', 55, 85, 70, 45, 6,  'Viel Wasser'),
    (18, 'Sonnenblume',       'Sunflower',     '🌻', 35, 65, 50, 30, 12, 'Selten gießen'),
    (19, 'Chili',             'Chili',         '🌶️', 40, 70, 55, 30, 10, 'Zwischen Gießen trocknen'),
]

F_ID, F_NAME_DE, F_NAME_EN, F_EMOJI = 0, 1, 2, 3
F_MIN, F_MAX, F_IDEAL, F_DUR, F_IVL, F_NOTES = 4, 5, 6, 7, 8, 9


def get_plant(idx):
    if 0 <= idx < len(PLANTS):
        return PLANTS[idx]
    return PLANTS[0]


def as_dict(plant):
    return {
        'id': plant[F_ID], 'name_de': plant[F_NAME_DE], 'name_en': plant[F_NAME_EN],
        'emoji': plant[F_EMOJI], 'min': plant[F_MIN], 'max': plant[F_MAX],
        'ideal': plant[F_IDEAL], 'duration': plant[F_DUR], 'interval': plant[F_IVL],
        'notes': plant[F_NOTES]
    }


def all_as_list():
    return [as_dict(p) for p in PLANTS]
