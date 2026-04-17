-- ── Table territories ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS territories (
    id          TEXT        PRIMARY KEY,  -- ex: 'region-idf', 'dept-75', 'commune-paris'
    name        TEXT        NOT NULL,
    type        TEXT        NOT NULL,     -- 'region', 'department', 'commune'
    code        TEXT,                     -- code INSEE
    region_id   TEXT        REFERENCES territories(id),
    dept_id     TEXT        REFERENCES territories(id),
    keywords    TEXT[]      DEFAULT '{}', -- mots-clés géographiques
    source_ids  TEXT[]      DEFAULT '{}', -- sources PQR associées
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_territories_type ON territories(type);
CREATE INDEX IF NOT EXISTS idx_territories_region ON territories(region_id);

-- ── Régions ───────────────────────────────────────────────────
INSERT INTO territories (id, name, type, code, keywords, source_ids) VALUES
('region-idf',  'Île-de-France',          'region', '11', ARRAY['île-de-france','paris','seine','val-de-marne','hauts-de-seine','seine-saint-denis','essonne','yvelines','val-d''oise'], ARRAY['le_parisien','le_monde','le_figaro','liberation']),
('region-hdf',  'Hauts-de-France',         'region', '32', ARRAY['hauts-de-france','nord','pas-de-calais','somme','oise','aisne','lille','amiens','valenciennes','dunkerque','lens','calais'], ARRAY['la_voix_du_nord','courrier_picard','nord_eclair']),
('region-gest', 'Grand Est',               'region', '44', ARRAY['grand-est','alsace','lorraine','champagne','strasbourg','nancy','reims','metz','mulhouse','colmar','troyes','épinal'], ARRAY['l_est_republicain','l_alsace','dna','republicain_lorrain','vosges_matin','l_union_ardennais']),
('region-norm', 'Normandie',               'region', '28', ARRAY['normandie','seine-maritime','calvados','manche','eure','orne','rouen','caen','le havre','cherbourg','évreux'], ARRAY['paris_normandie','la_manche_libre','ouest_france']),
('region-bret', 'Bretagne',                'region', '53', ARRAY['bretagne','finistère','morbihan','ille-et-vilaine','côtes-d''armor','rennes','brest','quimper','lorient','vannes','saint-brieuc'], ARRAY['ouest_france','le_telegramme']),
('region-pdl',  'Pays de la Loire',        'region', '52', ARRAY['pays-de-la-loire','loire-atlantique','maine-et-loire','vendée','sarthe','mayenne','nantes','angers','le mans','saint-nazaire','la roche-sur-yon'], ARRAY['presse_ocean','courrier_de_l_ouest','le_maine_libre']),
('region-cvl',  'Centre-Val de Loire',     'region', '24', ARRAY['centre-val-de-loire','loiret','loir-et-cher','indre-et-loire','cher','indre','orléans','tours','bourges','blois','chartres'], ARRAY['la_nouvelle_republique','la_republique_du_centre','le_berry_republicain','l_echo_republicain']),
('region-bfc',  'Bourgogne-Franche-Comté', 'region', '27', ARRAY['bourgogne','franche-comté','côte-d''or','saône-et-loire','yonne','nièvre','doubs','jura','haute-saône','dijon','besançon','chalon-sur-saône'], ARRAY['journal_saone_et_loire','l_yonne_republicaine','le_bien_public']),
('region-ara',  'Auvergne-Rhône-Alpes',    'region', '84', ARRAY['auvergne','rhône-alpes','rhône','isère','puy-de-dôme','haute-savoie','savoie','ain','ardèche','drôme','lyon','grenoble','clermont-ferrand','saint-étienne','annecy','chambéry'], ARRAY['le_progres','le_dauphine','la_montagne']),
('region-naq',  'Nouvelle-Aquitaine',      'region', '75', ARRAY['nouvelle-aquitaine','gironde','dordogne','charente','corrèze','creuse','haute-vienne','lot-et-garonne','pyrénées-atlantiques','bordeaux','limoges','poitiers','pau','périgueux'], ARRAY['sud_ouest','charente_libre','le_populaire_du_centre']),
('region-occ',  'Occitanie',               'region', '76', ARRAY['occitanie','hérault','haute-garonne','gard','var','aude','lozère','pyrénées-orientales','toulouse','montpellier','nîmes','perpignan','carcassonne'], ARRAY['la_depeche','midi_libre','l_independant']),
('region-paca', 'Provence-Alpes-Côte d''Azur', 'region', '93', ARRAY['provence','alpes','côte-d''azur','bouches-du-rhône','var','alpes-maritimes','alpes-de-haute-provence','hautes-alpes','vaucluse','marseille','nice','toulon','aix-en-provence','avignon'], ARRAY['la_provence','nice_matin','var_matin']),
('region-cors', 'Corse',                   'region', '94', ARRAY['corse','haute-corse','corse-du-sud','ajaccio','bastia'], ARRAY['corse_matin'])
ON CONFLICT (id) DO UPDATE SET
    keywords = EXCLUDED.keywords,
    source_ids = EXCLUDED.source_ids;

-- ── Départements (sélection des principaux) ───────────────────
INSERT INTO territories (id, name, type, code, region_id, keywords, source_ids) VALUES
-- IDF
('dept-75', 'Paris',            'department', '75', 'region-idf', ARRAY['paris','75','seine'], ARRAY['le_parisien']),
('dept-92', 'Hauts-de-Seine',   'department', '92', 'region-idf', ARRAY['hauts-de-seine','92','nanterre','boulogne','neuilly','issy'], ARRAY['le_parisien']),
('dept-93', 'Seine-Saint-Denis','department', '93', 'region-idf', ARRAY['seine-saint-denis','93','saint-denis','montreuil','bobigny'], ARRAY['le_parisien']),
('dept-94', 'Val-de-Marne',     'department', '94', 'region-idf', ARRAY['val-de-marne','94','créteil','vincennes','vitry'], ARRAY['le_parisien']),
-- Hauts-de-France
('dept-59', 'Nord',             'department', '59', 'region-hdf', ARRAY['nord','59','lille','roubaix','tourcoing','valenciennes','dunkerque'], ARRAY['la_voix_du_nord']),
('dept-62', 'Pas-de-Calais',    'department', '62', 'region-hdf', ARRAY['pas-de-calais','62','calais','boulogne','lens','arras'], ARRAY['la_voix_du_nord']),
('dept-80', 'Somme',            'department', '80', 'region-hdf', ARRAY['somme','80','amiens','abbeville'], ARRAY['courrier_picard']),
-- Grand Est
('dept-67', 'Bas-Rhin',         'department', '67', 'region-gest', ARRAY['bas-rhin','67','strasbourg','haguenau','sélestat'], ARRAY['l_alsace','dna']),
('dept-57', 'Moselle',          'department', '57', 'region-gest', ARRAY['moselle','57','metz','thionville','forbach'], ARRAY['republicain_lorrain']),
('dept-51', 'Marne',            'department', '51', 'region-gest', ARRAY['marne','51','reims','châlons-en-champagne','épernay'], ARRAY['l_union_ardennais']),
-- Normandie
('dept-76', 'Seine-Maritime',   'department', '76', 'region-norm', ARRAY['seine-maritime','76','rouen','le havre','dieppe'], ARRAY['paris_normandie']),
('dept-14', 'Calvados',         'department', '14', 'region-norm', ARRAY['calvados','14','caen','bayeux','lisieux'], ARRAY['paris_normandie']),
-- Bretagne
('dept-35', 'Ille-et-Vilaine',  'department', '35', 'region-bret', ARRAY['ille-et-vilaine','35','rennes','saint-malo','fougères'], ARRAY['ouest_france','le_telegramme']),
('dept-29', 'Finistère',        'department', '29', 'region-bret', ARRAY['finistère','29','brest','quimper','lorient'], ARRAY['le_telegramme','ouest_france']),
-- Pays de la Loire
('dept-44', 'Loire-Atlantique', 'department', '44', 'region-pdl',  ARRAY['loire-atlantique','44','nantes','saint-nazaire','la baule'], ARRAY['presse_ocean','ouest_france']),
('dept-49', 'Maine-et-Loire',   'department', '49', 'region-pdl',  ARRAY['maine-et-loire','49','angers','saumur','cholet'], ARRAY['courrier_de_l_ouest']),
-- Auvergne-RA
('dept-69', 'Rhône',            'department', '69', 'region-ara',  ARRAY['rhône','69','lyon','villeurbanne','vénissieux'], ARRAY['le_progres']),
('dept-38', 'Isère',            'department', '38', 'region-ara',  ARRAY['isère','38','grenoble','vienne','bourgoin'], ARRAY['le_dauphine']),
('dept-63', 'Puy-de-Dôme',      'department', '63', 'region-ara',  ARRAY['puy-de-dôme','63','clermont-ferrand','thiers','riom'], ARRAY['la_montagne']),
-- Nouvelle-Aquitaine
('dept-33', 'Gironde',          'department', '33', 'region-naq',  ARRAY['gironde','33','bordeaux','mérignac','pessac','libourne'], ARRAY['sud_ouest']),
-- Occitanie
('dept-31', 'Haute-Garonne',    'department', '31', 'region-occ',  ARRAY['haute-garonne','31','toulouse','colomiers','muret'], ARRAY['la_depeche']),
('dept-34', 'Hérault',          'department', '34', 'region-occ',  ARRAY['hérault','34','montpellier','sète','béziers'], ARRAY['midi_libre']),
-- PACA
('dept-13', 'Bouches-du-Rhône', 'department', '13', 'region-paca', ARRAY['bouches-du-rhône','13','marseille','aix-en-provence','arles'], ARRAY['la_provence']),
('dept-06', 'Alpes-Maritimes',  'department', '06', 'region-paca', ARRAY['alpes-maritimes','06','nice','cannes','antibes','grasse'], ARRAY['nice_matin']),
('dept-83', 'Var',              'department', '83', 'region-paca', ARRAY['var','83','toulon','draguignan','fréjus'], ARRAY['var_matin'])
ON CONFLICT (id) DO UPDATE SET
    keywords = EXCLUDED.keywords,
    source_ids = EXCLUDED.source_ids,
    region_id = EXCLUDED.region_id;
