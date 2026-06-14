"""Patch index.html with broader job queries and new categories."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('../index.html', encoding='utf-8') as f:
    content = f.read()

changes = 0

# ── 1. CAT_KW ──────────────────────────────────────────────────────────
old = (
    "const CAT_KW = {\n"
    "  edu: ['animateur','animation','BAFA','périscolaire','AESH','accompagnant','assistant éducatif','AED','assistant éducation','surveillant','éducateur','jeunesse','enfant','baby-sitter','baby sitter','garde enfant','garde d\\'enfant','crèche','maternelle','loisirs','ALSH','centre de loisirs','animateur loisirs'],\n"
    "  rh:  ['ressources humaines','RH','recrutement','recruteur','assistant RH','junior RH','chargé RH','administration personnel','chargé de formation','paie','secrétaire RH'],\n"
    "  client: ['clientèle','relation client','téléconseiller','conseiller clientèle','chargé de clientèle','support client','call center','hôtesse','hôte','accueil','réception','standard','service client','SAV','vendeur','vendeuse','vente','conseiller vente','caissier','caissière','hôte de caisse','conseiller commercial'],\n"
    "  hotel: ['réceptionniste','hôtel','hébergement','femme de chambre','valet de chambre','valet chambre','équipier hôtel','équipier','bagagiste','conciergerie','hôtellerie','restauration','serveur','serveuse','commis','plongeur','aide cuisine','agent entretien hôtel','chambre','ménage hôtel'],\n"
    "  noxp: ['débutant','sans expérience','sans diplôme','formation assurée','pas d\\'expérience','ouvert aux débutants','junior sans expérience','premier emploi','job étudiant','emploi étudiant','job temps partiel','emploi saisonnier','profil débutant','accessible sans expérience','étudiant recherche'],\n"
    "};"
)
new = (
    "const CAT_KW = {\n"
    "  edu:  ['animateur','animation','BAFA','périscolaire','AESH','accompagnant','AED','assistant éducation','surveillant','éducateur','enfant','baby-sitter','baby sitter','garde enfant','garde d\\'enfant','crèche','maternelle','loisirs','ALSH','centre de loisirs','soutien scolaire','cours particulier','répétiteur','professeur domicile','colo','colonie vacances'],\n"
    "  rh:   ['ressources humaines','RH','recrutement','recruteur','assistant RH','administration personnel','paie','secrétaire RH'],\n"
    "  client: ['clientèle','relation client','téléconseiller','conseiller clientèle','call center','hôtesse','hôte','accueil','réception','standard','service client','SAV','vendeur','vendeuse','vente','caissier','caissière','hôte de caisse','employé libre service','employé de commerce','grande surface','magasin'],\n"
    "  hotel: ['réceptionniste','hôtel','hébergement','femme de chambre','valet de chambre','équipier','bagagiste','conciergerie','hôtellerie','restauration','serveur','serveuse','commis','plongeur','aide cuisine','barista','boulangerie','snack'],\n"
    "  logistique: ['manutentionnaire','préparateur de commandes','préparateur commandes','entrepôt','logistique','magasinier','cariste','opérateur logistique','livreur','coursier','chauffeur livreur','livraison','agent de quai'],\n"
    "  aide:  ['aide à domicile','auxiliaire de vie','aide ménagère','accompagnateur','assistant de vie','aide personnes','ADVF','agent de soins'],\n"
    "  securite: ['agent de sécurité','agent sécurité','gardiennage','vigile','SSIAP','gardien','enquêteur terrain','enquêteur','sondage','interviewer'],\n"
    "  noxp:  ['débutant','sans expérience','sans diplôme','formation assurée','pas d\\'expérience','premier emploi','job étudiant','emploi étudiant','job temps partiel','emploi saisonnier','accessible sans expérience','étudiant'],\n"
    "};"
)
if old in content:
    content = content.replace(old, new, 1)
    print('1. CAT_KW updated OK')
    changes += 1
else:
    print('1. CAT_KW NOT FOUND')

# ── 2. CAT_LABELS ───────────────────────────────────────────────────────
old = "const CAT_LABELS = { edu:'📚 Éducation', rh:'👔 RH', client:'🤝 Relation client', hotel:'🏨 Hôtellerie', noxp:'✨ Sans exp.', other:'🔹 Autre' };"
new = "const CAT_LABELS = { edu:'📚 Éducation & Enfants', rh:'👔 RH & Admin', client:'🤝 Commerce & Accueil', hotel:'🏨 Hôtellerie & Resto', logistique:'📦 Logistique', aide:'🏠 Aide dom.', securite:'🔍 Sécu & Enquête', noxp:'✨ Sans exp.', other:'🔹 Autre' };"
if old in content:
    content = content.replace(old, new, 1)
    print('2. CAT_LABELS updated OK')
    changes += 1
else:
    print('2. CAT_LABELS NOT FOUND')

# ── 3. CAT_CLS ──────────────────────────────────────────────────────────
old = "const CAT_CLS    = { edu:'tag-edu', rh:'tag-rh', client:'tag-client', hotel:'tag-hotel', noxp:'tag-noxp', other:'tag-edu' };"
new = "const CAT_CLS    = { edu:'tag-edu', rh:'tag-rh', client:'tag-client', hotel:'tag-hotel', logistique:'tag-hotel', aide:'tag-noxp', securite:'tag-rh', noxp:'tag-noxp', other:'tag-edu' };"
if old in content:
    content = content.replace(old, new, 1)
    print('3. CAT_CLS updated OK')
    changes += 1
else:
    print('3. CAT_CLS NOT FOUND')

# ── 4. fetchAdzunaFR queries ─────────────────────────────────────────────
old = (
    "    const queries = customQuery ? [customQuery] : [\n"
    "      // Éducation / jeunesse sans diplôme\n"
    "      'animateur périscolaire débutant BAFA',\n"
    "      'baby sitter garde enfant domicile débutant',\n"
    "      'assistant éducation AED surveillant lycée',\n"
    "      'AESH accompagnant élèves débutant',\n"
    "      'animateur centre loisirs ALSH sans expérience',\n"
    "      // RH junior accessible\n"
    "      'assistant RH junior débutant recrutement',\n"
    "      'chargé recrutement junior sans expérience',\n"
    "      // Relation client sans expérience\n"
    "      'téléconseiller débutant formation assurée',\n"
    "      'hôtesse accueil standardiste débutant',\n"
    "      'conseiller clientèle débutant sans expérience',\n"
    "      'vendeur débutant sans expérience',\n"
    "      'caissier hôte de caisse sans diplôme',\n"
    "      // Hôtellerie sans diplôme requis\n"
    "      'réceptionniste hôtel débutant junior',\n"
    "      'femme de chambre valet équipier hôtel',\n"
    "      'serveur restauration débutant sans expérience',\n"
    "      'agent entretien ménage hôtel',\n"
    "      // Jobs étudiants / sans exp transversaux\n"
    "      'job étudiant temps partiel',\n"
    "      'aide à domicile auxiliaire débutant',\n"
    "      'emploi sans diplôme sans expérience',\n"
    "    ];"
)
new = (
    "    const queries = customQuery ? [customQuery] : [\n"
    "      // Jeunesse & enfants\n"
    "      'baby sitter garde enfant',\n"
    "      'animateur enfant animation',\n"
    "      'soutien scolaire cours particuliers',\n"
    "      'animation vacances periscolaire',\n"
    "      // Commerce & distribution\n"
    "      'vendeur magasin',\n"
    "      'employe polyvalent commerce',\n"
    "      'caissier employe libre service',\n"
    "      'agent accueil hotesse',\n"
    "      // Logistique & entrepôt\n"
    "      'preparateur commandes entrepot',\n"
    "      'manutentionnaire logistique',\n"
    "      // Relation client & téléphone\n"
    "      'teleconseiller service client',\n"
    "      'charge clientele',\n"
    "      // Restauration & hôtellerie\n"
    "      'serveur aide cuisine restauration',\n"
    "      'receptionniste hotel',\n"
    "      // Livraison\n"
    "      'livreur livraison coursier',\n"
    "      // Aide à la personne\n"
    "      'aide domicile auxiliaire',\n"
    "      // Enquête terrain & sécurité\n"
    "      'enqueteur terrain sondage',\n"
    "      'agent securite gardiennage',\n"
    "    ];"
)
if old in content:
    content = content.replace(old, new, 1)
    print('4. fetchAdzunaFR queries updated OK')
    changes += 1
else:
    print('4. fetchAdzunaFR queries NOT FOUND')

# ── 5. fetchJoobleFR queries ─────────────────────────────────────────────
old = (
    "  const queries = customQuery ? [{ keywords: customQuery, location: loc }] : [\n"
    "    { keywords: 'baby sitter garde enfant débutant', location: loc },\n"
    "    { keywords: 'animateur périscolaire BAFA sans expérience', location: loc },\n"
    "    { keywords: 'assistant RH junior débutant', location: loc },\n"
    "    { keywords: 'téléconseiller débutant formation assurée', location: loc },\n"
    "    { keywords: 'réceptionniste hôtel débutant', location: loc },\n"
    "    { keywords: 'femme de chambre équipier hôtel', location: loc },\n"
    "    { keywords: 'serveur restauration débutant', location: loc },\n"
    "    { keywords: 'vendeur caissier sans diplôme', location: loc },\n"
    "    { keywords: 'job étudiant sans expérience', location: loc },\n"
    "    { keywords: 'aide à domicile débutant', location: loc },\n"
    "  ];"
)
new = (
    "  const queries = customQuery ? [{ keywords: customQuery, location: loc }] : [\n"
    "    { keywords: 'baby sitter garde enfant', location: loc },\n"
    "    { keywords: 'animateur enfant animation', location: loc },\n"
    "    { keywords: 'soutien scolaire cours particuliers', location: loc },\n"
    "    { keywords: 'vendeur magasin employe polyvalent', location: loc },\n"
    "    { keywords: 'caissier employe libre service', location: loc },\n"
    "    { keywords: 'preparateur commandes manutentionnaire', location: loc },\n"
    "    { keywords: 'teleconseiller service client', location: loc },\n"
    "    { keywords: 'receptionniste hotel accueil', location: loc },\n"
    "    { keywords: 'serveur restauration plongeur', location: loc },\n"
    "    { keywords: 'livreur coursier livraison', location: loc },\n"
    "    { keywords: 'aide domicile auxiliaire', location: loc },\n"
    "    { keywords: 'enqueteur terrain agent securite', location: loc },\n"
    "  ];"
)
if old in content:
    content = content.replace(old, new, 1)
    print('5. fetchJoobleFR queries updated OK')
    changes += 1
else:
    print('5. fetchJoobleFR queries NOT FOUND')

# ── 6. fetchIndeedRSSFR queries ──────────────────────────────────────────
old = (
    "  const queries = [\n"
    "    { q: 'baby+sitter+garde+enfant+débutant' },\n"
    "    { q: 'animateur+périscolaire+BAFA+sans+expérience' },\n"
    "    { q: 'AED+surveillant+assistant+éducation' },\n"
    "    { q: 'téléconseiller+débutant+formation+assurée' },\n"
    "    { q: 'hôtesse+accueil+débutant' },\n"
    "    { q: 'vendeur+caissier+sans+diplôme' },\n"
    "    { q: 'réceptionniste+hôtel+débutant' },\n"
    "    { q: 'femme+de+chambre+équipier+hôtel' },\n"
    "    { q: 'serveur+restauration+débutant' },\n"
    "    { q: 'job+étudiant+sans+expérience' },\n"
    "  ];"
)
new = (
    "  const queries = [\n"
    "    { q: 'baby+sitter+garde+enfant' },\n"
    "    { q: 'animateur+enfant+animation' },\n"
    "    { q: 'soutien+scolaire+cours+particuliers' },\n"
    "    { q: 'vendeur+magasin' },\n"
    "    { q: 'employe+polyvalent+commerce' },\n"
    "    { q: 'preparateur+commandes+entrepot' },\n"
    "    { q: 'manutentionnaire+logistique' },\n"
    "    { q: 'teleconseiller+service+client' },\n"
    "    { q: 'receptionniste+hotel' },\n"
    "    { q: 'serveur+restauration' },\n"
    "    { q: 'livreur+livraison' },\n"
    "    { q: 'aide+domicile+auxiliaire' },\n"
    "    { q: 'enqueteur+terrain+sondage' },\n"
    "  ];"
)
if old in content:
    content = content.replace(old, new, 1)
    print('6. fetchIndeedRSSFR queries updated OK')
    changes += 1
else:
    print('6. fetchIndeedRSSFR queries NOT FOUND')

# ── 7. fetchJobtomeRSSFR queries ─────────────────────────────────────────
old = (
    "  const queries = [\n"
    "    'baby-sitter', 'animateur-periscolaire', 'assistant-education',\n"
    "    'teleconseiller-debutant', 'hotesse-accueil', 'vendeur-debutant',\n"
    "    'receptionniste-hotel-debutant', 'femme-de-chambre', 'serveur-restauration',\n"
    "    'job-etudiant', 'emploi-sans-diplome',\n"
    "  ];"
)
new = (
    "  const queries = [\n"
    "    'baby-sitter', 'animateur-enfant', 'soutien-scolaire',\n"
    "    'vendeur-magasin', 'employe-polyvalent', 'caissier',\n"
    "    'preparateur-commandes', 'manutentionnaire',\n"
    "    'teleconseiller', 'receptionniste-hotel',\n"
    "    'serveur-restauration', 'livreur-livraison',\n"
    "    'aide-domicile', 'enqueteur-terrain', 'agent-securite',\n"
    "  ];"
)
if old in content:
    content = content.replace(old, new, 1)
    print('7. fetchJobtomeRSSFR queries updated OK')
    changes += 1
else:
    print('7. fetchJobtomeRSSFR queries NOT FOUND')

# ── 8. fetchTalentRSSFR queries ──────────────────────────────────────────
old = (
    "  const queries = [\n"
    "    'baby sitter débutant', 'animateur périscolaire',\n"
    "    'téléconseiller débutant', 'vendeur débutant',\n"
    "    'réceptionniste hôtel débutant', 'job étudiant sans expérience',\n"
    "  ];"
)
new = (
    "  const queries = [\n"
    "    'baby sitter garde enfant', 'animateur enfant',\n"
    "    'soutien scolaire', 'vendeur magasin',\n"
    "    'employe polyvalent', 'preparateur commandes',\n"
    "    'teleconseiller', 'receptionniste hotel',\n"
    "    'serveur restauration', 'livreur livraison',\n"
    "    'aide domicile', 'enqueteur terrain',\n"
    "  ];"
)
if old in content:
    content = content.replace(old, new, 1)
    print('8. fetchTalentRSSFR queries updated OK')
    changes += 1
else:
    print('8. fetchTalentRSSFR queries NOT FOUND')

with open('../index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\nDone — {changes}/8 changes applied')
