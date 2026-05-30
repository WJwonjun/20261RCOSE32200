CREATE TABLE pokemon (
  id INTEGER PRIMARY KEY,
  dex INTEGER, name_ko TEXT, name_en TEXT UNIQUE NOT NULL, form TEXT,
  type1 TEXT, type2 TEXT,
  hp INTEGER, atk INTEGER, def INTEGER, spa INTEGER, spd INTEGER, spe INTEGER, total INTEGER,
  ability_hidden TEXT, champions_legal INTEGER
);
CREATE TABLE pokemon_abilities (
  pokemon_en TEXT NOT NULL, ability_en TEXT NOT NULL, slot INTEGER, is_hidden INTEGER,
  PRIMARY KEY (pokemon_en, ability_en)
);
CREATE TABLE moves (
  id INTEGER PRIMARY KEY,
  name_ko TEXT, name_en TEXT UNIQUE NOT NULL,
  type_ko TEXT, type_en TEXT, category TEXT,
  power INTEGER, accuracy INTEGER, pp INTEGER, priority INTEGER, target TEXT,
  effect_en TEXT, champions_legal INTEGER
);
CREATE TABLE pokemon_moves (
  pokemon_en TEXT NOT NULL, move_en TEXT NOT NULL,
  PRIMARY KEY (pokemon_en, move_en)
);
CREATE TABLE abilities (
  id INTEGER PRIMARY KEY, name_ko TEXT, name_en TEXT UNIQUE NOT NULL,
  desc_en TEXT, champions_legal INTEGER
);
CREATE TABLE items (
  id INTEGER PRIMARY KEY, name_ko TEXT, name_en TEXT UNIQUE NOT NULL,
  category TEXT, desc_en TEXT, champions_legal INTEGER
);
CREATE TABLE natures (
  id INTEGER PRIMARY KEY, name_ko TEXT, name_en TEXT UNIQUE NOT NULL,
  increased TEXT, decreased TEXT, champions_legal INTEGER
);
CREATE TABLE type_chart (
  attacking TEXT NOT NULL, defending TEXT NOT NULL, multiplier REAL,
  PRIMARY KEY (attacking, defending)
);
CREATE TABLE reference (key TEXT PRIMARY KEY, value_ko TEXT, value_en TEXT);
CREATE INDEX idx_pm_move ON pokemon_moves(move_en);
CREATE INDEX idx_moves_type ON moves(type_en);
CREATE INDEX idx_moves_legal ON moves(champions_legal);
CREATE INDEX idx_pa_ability ON pokemon_abilities(ability_en);
CREATE VIEW v_pokemon_movepool AS
  SELECT p.name_ko AS 포켓몬, p.name_en AS pokemon, m.name_ko AS 기술, m.name_en AS move,
         m.type_ko AS 타입, m.category, m.power, m.accuracy, m.pp
  FROM pokemon_moves pm
  JOIN pokemon p ON p.name_en = pm.pokemon_en
  JOIN moves   m ON m.name_en = pm.move_en
/* v_pokemon_movepool("포켓몬",pokemon,"기술",move,"타입",category,power,accuracy,pp) */;
CREATE VIEW v_pokemon_abilities AS
  SELECT p.name_ko AS 포켓몬, p.name_en AS pokemon, a.name_ko AS 특성, pa.ability_en AS ability,
         pa.is_hidden AS 숨겨진특성, a.desc_en
  FROM pokemon_abilities pa
  JOIN pokemon p ON p.name_en = pa.pokemon_en
  LEFT JOIN abilities a ON a.name_en = pa.ability_en
/* v_pokemon_abilities("포켓몬",pokemon,"특성",ability,"숨겨진특성",desc_en) */;
