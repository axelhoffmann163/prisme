INTERVAL = {
    "agence": 5,
    "tv": 15,
    "radio": 15,
    "pqn": 30,
    "natif": 30,
    "pqr": 60,
    "magazine": 360,
    "international": 60,
}

SOURCES = [
    # PQN
    {"id": "le_monde", "name": "Le Monde", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.lemonde.fr/rss/une.xml", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {"politique": "https://www.lemonde.fr/politique/rss_full.xml", "economie": "https://www.lemonde.fr/economie/rss_full.xml", "international": "https://www.lemonde.fr/international/rss_full.xml", "societe": "https://www.lemonde.fr/societe/rss_full.xml"}},
    {"id": "le_figaro", "name": "Le Figaro", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.lefigaro.fr/rss/figaro_actualite-france.xml", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {"politique": "https://www.lefigaro.fr/rss/figaro_politique.xml", "economie": "https://www.lefigaro.fr/rss/figaro_economie.xml", "international": "https://www.lefigaro.fr/rss/figaro_international.xml"}},
    {"id": "liberation", "name": "Libération", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.liberation.fr/arc/outboundfeeds/rss/?outputType=xml", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {"politique": "https://www.liberation.fr/arc/outboundfeeds/rss-all/category/politique/?outputType=xml", "international": "https://www.liberation.fr/arc/outboundfeeds/rss-all/category/international/?outputType=xml"}},
    {"id": "les_echos", "name": "Les Échos", "category": "PQN", "subcategory": "Économie", "url": "https://services.lesechos.fr/rss/les-echos-une.xml", "interval": 30, "active": False, "tags": ["économie"], "extra_feeds": {}},
    {"id": "le_parisien", "name": "Le Parisien", "category": "PQN", "subcategory": "Généraliste", "url": "https://feeds.leparisien.fr/arc/outboundfeeds/leparisien/rss/", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {}},
    {"id": "la_croix", "name": "La Croix", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.la-croix.com/RSS", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {"france": "https://www.la-croix.com/RSS/France", "monde": "https://www.la-croix.com/RSS/Monde"}},
    {"id": "l_humanite", "name": "L'Humanité", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.humanite.fr/feed", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {}},
    {"id": "la_tribune", "name": "La Tribune", "category": "PQN", "subcategory": "Économie", "url": "https://news.google.com/rss/search?q=source:latribune.fr&hl=fr&gl=FR&ceid=FR:fr", "interval": 30, "active": True, "tags": ["économie"], "extra_feeds": {}},
    {"id": "l_equipe", "name": "L'Équipe", "category": "PQN", "subcategory": "Sport", "url": "https://dwh.lequipe.fr/api/edito/rss?path=/", "interval": 30, "active": True, "tags": ["sport"], "extra_feeds": {}},
    {"id": "challenges", "name": "Challenges", "category": "PQN", "subcategory": "Économie", "url": "https://www.challenges.fr/rss.xml", "interval": 30, "active": True, "tags": ["économie"], "extra_feeds": {}},
    {"id": "l_opinion", "name": "L'Opinion", "category": "PQN", "subcategory": "Généraliste", "url": "https://news.google.com/rss/search?q=source:lopinion.fr&hl=fr&gl=FR&ceid=FR:fr", "interval": 30, "active": True, "tags": ["politique"], "extra_feeds": {}},
    {"id": "mediapart", "name": "Mediapart", "category": "PQN", "subcategory": "Investigation", "url": "https://www.mediapart.fr/articles/feed", "interval": 30, "active": True, "tags": ["investigation"], "extra_feeds": {}},
    {"id": "vingt_minutes", "name": "20 Minutes", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.20minutes.fr/feeds/rss-une.xml", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {}},
    {"id": "le_huffpost", "name": "Le HuffPost", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.huffingtonpost.fr/feeds/index.xml", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {}},
    {"id": "slate_fr", "name": "Slate.fr", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.slate.fr/rss.xml", "interval": 30, "active": True, "tags": ["société"], "extra_feeds": {}},
    {"id": "marianne", "name": "Marianne", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.marianne.net/feed", "interval": 30, "active": False, "tags": ["politique"], "extra_feeds": {}},
    {"id": "courrier_international", "name": "Courrier International", "category": "PQN", "subcategory": "International", "url": "https://www.courrierinternational.com/rss/all/rss.xml", "interval": 30, "active": True, "tags": ["international"], "extra_feeds": {}},
    {"id": "le_nouvel_obs", "name": "L'Obs", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.nouvelobs.com/a-la-une/rss.xml", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {}},
    {"id": "l_express", "name": "L'Express", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.lexpress.fr/rss/alaune.xml", "interval": 30, "active": True, "tags": ["généraliste"], "extra_feeds": {}},
    {"id": "le_point", "name": "Le Point", "category": "PQN", "subcategory": "Généraliste", "url": "https://www.lepoint.fr/24h-infos/rss.xml", "interval": 30, "active": False, "tags": ["généraliste"], "extra_feeds": {}},
    {"id": "monde_diplomatique", "name": "Le Monde diplomatique", "category": "PQN", "subcategory": "Géopolitique", "url": "https://www.monde-diplomatique.fr/rss/", "interval": 360, "active": True, "tags": ["géopolitique"], "extra_feeds": {}},
    {"id": "arret_sur_images", "name": "Arrêt sur images", "category": "PQN", "subcategory": "Médias", "url": "https://api.arretsurimages.net/api/public/rss/all-content", "interval": 30, "active": True, "tags": ["médias"], "extra_feeds": {}},
    # PQR
    {"id": "ouest_france", "name": "Ouest-France", "category": "PQR", "subcategory": "Grand Ouest", "url": "https://www.ouest-france.fr/rss-en-continu.xml", "interval": 60, "active": True, "tags": ["bretagne", "normandie"], "extra_feeds": {}},
    {"id": "le_telegramme", "name": "Le Télégramme", "category": "PQR", "subcategory": "Grand Ouest", "url": "https://www.letelegramme.fr/rss.xml", "interval": 60, "active": False, "tags": ["bretagne"], "extra_feeds": {}},
    {"id": "sud_ouest", "name": "Sud Ouest", "category": "PQR", "subcategory": "Sud-Ouest", "url": "https://www.sudouest.fr/essentiel/rss.xml", "interval": 60, "active": True, "tags": ["gironde", "bordeaux"], "extra_feeds": {}},
    {"id": "la_depeche", "name": "La Dépêche du Midi", "category": "PQR", "subcategory": "Sud-Ouest", "url": "https://www.ladepeche.fr/rss.xml", "interval": 60, "active": True, "tags": ["occitanie", "toulouse"], "extra_feeds": {}},
    {"id": "midi_libre", "name": "Midi Libre", "category": "PQR", "subcategory": "Midi", "url": "https://www.midilibre.fr/rss.xml", "interval": 60, "active": True, "tags": ["hérault", "montpellier"], "extra_feeds": {}},
    {"id": "la_voix_du_nord", "name": "La Voix du Nord", "category": "PQR", "subcategory": "Nord", "url": "https://news.google.com/rss/search?q=source:lavoixdunord.fr&hl=fr&gl=FR&ceid=FR:fr", "interval": 60, "active": True, "tags": ["nord", "lille"], "extra_feeds": {}},
    {"id": "le_progres", "name": "Le Progrès", "category": "PQR", "subcategory": "Nord-Est", "url": "https://www.leprogres.fr/rss", "interval": 60, "active": True, "tags": ["rhône", "lyon"], "extra_feeds": {}},
    {"id": "le_dauphine", "name": "Le Dauphiné Libéré", "category": "PQR", "subcategory": "Nord-Est", "url": "https://www.ledauphine.com/rss", "interval": 60, "active": True, "tags": ["isère", "grenoble"], "extra_feeds": {}},
    {"id": "l_est_republicain", "name": "L'Est Républicain", "category": "PQR", "subcategory": "Nord-Est", "url": "https://www.estrepublicain.fr/rss", "interval": 60, "active": True, "tags": ["nancy", "vosges"], "extra_feeds": {}},
    {"id": "l_alsace", "name": "L'Alsace", "category": "PQR", "subcategory": "Nord-Est", "url": "https://www.lalsace.fr/rss", "interval": 60, "active": True, "tags": ["alsace", "mulhouse"], "extra_feeds": {}},
    {"id": "dna", "name": "Dernières Nouvelles d'Alsace", "category": "PQR", "subcategory": "Nord-Est", "url": "https://www.dna.fr/rss", "interval": 60, "active": True, "tags": ["strasbourg", "alsace"], "extra_feeds": {}},
    {"id": "la_montagne", "name": "La Montagne", "category": "PQR", "subcategory": "Centre", "url": "https://news.google.com/rss/search?q=source:lamontagne.fr&hl=fr&gl=FR&ceid=FR:fr", "interval": 60, "active": True, "tags": ["auvergne", "clermont"], "extra_feeds": {}},
    {"id": "le_bien_public", "name": "Le Bien Public", "category": "PQR", "subcategory": "Nord-Est", "url": "https://www.bienpublic.com/rss", "interval": 60, "active": False, "tags": ["dijon", "bourgogne"], "extra_feeds": {}},
    {"id": "la_nouvelle_republique", "name": "La Nouvelle République", "category": "PQR", "subcategory": "Centre-Ouest", "url": "https://www.lanouvellerepublique.fr/rss.xml", "interval": 60, "active": False, "tags": ["tours", "vienne"], "extra_feeds": {}},
    {"id": "la_provence", "name": "La Provence", "category": "PQR", "subcategory": "Méditerranée", "url": "https://news.google.com/rss/search?q=source:laprovence.com&hl=fr&gl=FR&ceid=FR:fr", "interval": 60, "active": True, "tags": ["marseille", "paca"], "extra_feeds": {}},
    {"id": "nice_matin", "name": "Nice-Matin", "category": "PQR", "subcategory": "Méditerranée", "url": "https://news.google.com/rss/search?q=source:nicematin.com&hl=fr&gl=FR&ceid=FR:fr", "interval": 60, "active": True, "tags": ["nice", "var"], "extra_feeds": {}},
    {"id": "observateur_douaisis", "name": "L'Observateur du Douaisis", "category": "PQR", "subcategory": "Nord", "url": "https://news.google.com/rss/search?q=source:lobservateur.fr&hl=fr&gl=FR&ceid=FR:fr", "interval": 60, "active": True, "tags": ["douai", "nord"], "extra_feeds": {}},
    {"id": "le_maine_libre", "name": "Le Maine Libre", "category": "PQR", "subcategory": "Grand Ouest", "url": "https://news.google.com/rss/search?q=%22Maine+Libre%22&hl=fr&gl=FR&ceid=FR:fr", "interval": 60, "active": True, "tags": ["sarthe", "le-mans"], "extra_feeds": {}},
    # TV
    {"id": "bfmtv", "name": "BFM TV", "category": "TV", "subcategory": "Info nationale", "url": "https://www.bfmtv.com/rss/news-24-7/", "interval": 15, "active": True, "tags": ["info-continue"], "extra_feeds": {"economie": "https://www.bfmtv.com/rss/economie/", "international": "https://www.bfmtv.com/rss/international/"}},
    {"id": "bfm_business", "name": "BFM Business", "category": "TV", "subcategory": "Économie", "url": "https://www.bfmtv.com/rss/economie/", "interval": 15, "active": True, "tags": ["économie", "bourse"], "extra_feeds": {}},
    {"id": "cnews", "name": "CNews", "category": "TV", "subcategory": "Info nationale", "url": "https://www.cnews.fr/rss.xml", "interval": 15, "active": True, "tags": ["info-continue"], "extra_feeds": {}},
    {"id": "france_tv_info", "name": "France Info TV", "category": "TV", "subcategory": "Info nationale", "url": "https://www.francetvinfo.fr/titres.rss", "interval": 15, "active": True, "tags": ["service-public"], "extra_feeds": {"france": "https://www.francetvinfo.fr/france.rss", "politique": "https://www.francetvinfo.fr/politique.rss", "economie": "https://www.francetvinfo.fr/economie.rss", "monde": "https://www.francetvinfo.fr/monde.rss"}},
    {"id": "france_24_fr", "name": "France 24", "category": "TV", "subcategory": "International", "url": "https://www.france24.com/fr/rss", "interval": 15, "active": True, "tags": ["international"], "extra_feeds": {"france": "https://www.france24.com/fr/france/rss", "europe": "https://www.france24.com/fr/europe/rss", "afrique": "https://www.france24.com/fr/afrique/rss"}},
    {"id": "rfi", "name": "RFI", "category": "TV", "subcategory": "International", "url": "https://www.rfi.fr/fr/rss", "interval": 15, "active": True, "tags": ["international", "afrique"], "extra_feeds": {}},
    {"id": "lci", "name": "LCI", "category": "TV", "subcategory": "Info nationale", "url": "https://www.tf1info.fr/rss/", "interval": 15, "active": False, "tags": ["info-continue"], "extra_feeds": {}},
    # Radio
    {"id": "france_inter", "name": "France Inter", "category": "Radio", "subcategory": "Généraliste", "url": "https://www.radiofrance.fr/franceinter/rss", "interval": 15, "active": True, "tags": ["service-public"], "extra_feeds": {}},
    {"id": "france_info_radio", "name": "France Info Radio", "category": "Radio", "subcategory": "Info continue", "url": "https://www.francetvinfo.fr/titres.rss", "interval": 15, "active": True, "tags": ["service-public"], "extra_feeds": {}},
    {"id": "rtl", "name": "RTL", "category": "Radio", "subcategory": "Généraliste", "url": "https://www.rtl.fr/actu/rss.xml", "interval": 15, "active": False, "tags": ["généraliste"], "extra_feeds": {}},
    {"id": "europe_1", "name": "Europe 1", "category": "Radio", "subcategory": "Généraliste", "url": "https://www.europe1.fr/rss/france", "interval": 15, "active": True, "tags": ["généraliste"], "extra_feeds": {"international": "https://www.europe1.fr/rss/international", "politique": "https://www.europe1.fr/rss/politique"}},
    {"id": "france_culture", "name": "France Culture", "category": "Radio", "subcategory": "Culture", "url": "https://www.radiofrance.fr/franceculture/rss", "interval": 15, "active": True, "tags": ["culture", "science"], "extra_feeds": {}},
    {"id": "france_bleu", "name": "France Bleu", "category": "Radio", "subcategory": "Locale", "url": "https://www.radiofrance.fr/francebleu/rss", "interval": 15, "active": True, "tags": ["local"], "extra_feeds": {}},
    {"id": "sud_radio", "name": "Sud Radio", "category": "Radio", "subcategory": "Talk", "url": "https://www.sudradio.fr/feed", "interval": 15, "active": True, "tags": ["politique", "débats"], "extra_feeds": {}},
    # Agences
    {"id": "afp_google_news", "name": "AFP (via Google News)", "category": "Agence", "subcategory": "Généraliste", "url": "https://news.google.com/rss/search?q=AFP&hl=fr&gl=FR&ceid=FR:fr", "interval": 5, "active": True, "tags": ["agence", "dépêches"], "extra_feeds": {}},
    {"id": "rtbf_info", "name": "RTBF Info", "category": "Agence", "subcategory": "International", "url": "https://news.google.com/rss/search?q=source:rtbf.be&hl=fr&gl=FR&ceid=FR:fr", "interval": 5, "active": True, "tags": ["belgique", "europe"], "extra_feeds": {}},
    # Magazines
    {"id": "capital", "name": "Capital", "category": "Magazine", "subcategory": "Économie", "url": "https://feed.prismamediadigital.com/v1/cap/rss?sources=capital,capital-avec-agence-france-presse", "interval": 360, "active": True, "tags": ["économie", "emploi"], "extra_feeds": {}},
    {"id": "sciences_et_avenir", "name": "Sciences et Avenir", "category": "Magazine", "subcategory": "Science", "url": "https://www.sciencesetavenir.fr/rss.xml", "interval": 360, "active": True, "tags": ["science"], "extra_feeds": {}},
    {"id": "01net", "name": "01net", "category": "Magazine", "subcategory": "Tech", "url": "https://www.01net.com/feed/", "interval": 360, "active": True, "tags": ["tech", "numérique"], "extra_feeds": {}},
    {"id": "reporterre", "name": "Reporterre", "category": "Magazine", "subcategory": "Environnement", "url": "https://reporterre.net/spip.php?page=backend", "interval": 360, "active": True, "tags": ["écologie", "environnement"], "extra_feeds": {}},
    {"id": "telerama", "name": "Télérama", "category": "Magazine", "subcategory": "Culture", "url": "https://www.telerama.fr/rss/une.xml", "interval": 360, "active": True, "tags": ["culture", "cinéma"], "extra_feeds": {}},
    {"id": "les_inrocks", "name": "Les Inrockuptibles", "category": "Magazine", "subcategory": "Culture", "url": "https://www.lesinrocks.com/feed/", "interval": 360, "active": True, "tags": ["musique", "culture"], "extra_feeds": {}},
    {"id": "the_conversation_fr", "name": "The Conversation FR", "category": "Magazine", "subcategory": "Académique", "url": "https://theconversation.com/fr/articles.atom", "interval": 360, "active": True, "tags": ["recherche", "expert"], "extra_feeds": {}},
    {"id": "next_ink", "name": "Next.ink", "category": "Magazine", "subcategory": "Tech", "url": "https://next.ink/feed/", "interval": 360, "active": True, "tags": ["numérique", "droits"], "extra_feeds": {}},
    # Natifs numériques
    {"id": "mediacites", "name": "Médiacités", "category": "Natif", "subcategory": "Investigation locale", "url": "https://www.mediacites.fr/feed", "interval": 30, "active": True, "tags": ["investigation", "local"], "extra_feeds": {}},
    # International
    {"id": "bbc_news_en", "name": "BBC News", "category": "International", "subcategory": "Anglophone", "url": "https://feeds.bbci.co.uk/news/rss.xml", "interval": 60, "active": True, "tags": ["international", "uk"], "extra_feeds": {}},
    {"id": "rts_info", "name": "RTS Info", "category": "International", "subcategory": "Francophone", "url": "https://www.rts.ch/info/rss", "interval": 60, "active": False, "tags": ["suisse"], "extra_feeds": {}},
    {"id": "radio_canada", "name": "Radio-Canada", "category": "International", "subcategory": "Francophone", "url": "https://ici.radio-canada.ca/rss/4159", "interval": 60, "active": True, "tags": ["canada", "québec"], "extra_feeds": {}},
]

def get_active_sources():
    return [s for s in SOURCES if s["active"]]

def get_all_feeds():
    feeds = []
    for source in get_active_sources():
        feeds.append({"source_id": source["id"], "source_name": source["name"], "category": source["category"], "label": "une", "url": source["url"], "interval": source["interval"]})
        for label, url in (source.get("extra_feeds") or {}).items():
            feeds.append({"source_id": source["id"], "source_name": source["name"], "category": source["category"], "label": label, "url": url, "interval": source["interval"]})
    return feeds

def get_source_by_id(source_id):
    return next((s for s in SOURCES if s["id"] == source_id), None)
