"""Journal alimentaire et recherche d'aliments par nom."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from miamstock.nutrition import chercher_ciqual, mots, pertinence

NUTELLA = "3017620422003"
AUJOURDHUI = date.today().isoformat()


def saisie(**champs):
    base = {
        "day": AUJOURDHUI, "meal": "dejeuner", "label": "Riz blanc, cuit",
        "source": "ciqual", "ref": "9100", "grams": 200, "kcal_100g": 145,
        "prot_100g": 2.9, "gluc_100g": 31.8, "lip_100g": 0.4,
    }
    base.update(champs)
    return base


# --- Le classement de la recherche (pur) ------------------------------------------


def test_tous_les_mots_doivent_figurer_dans_nimporte_quel_ordre():
    nom = "Yaourt, lait fermenté ou spécialité laitière, nature"
    assert pertinence(nom, mots("yaourt nature")) is not None
    assert pertinence(nom, mots("nature yaourt")) is not None
    assert pertinence(nom, mots("yaourt fraise")) is None


def test_les_accents_ne_comptent_pas():
    assert pertinence("Pâtes sèches", mots("pates")) is not None


def test_un_nom_qui_commence_par_le_mot_passe_devant():
    fruit = pertinence("Pomme, pulpe, crue", mots("pomme"))
    plat = pertinence("Aligot (purée de pomme de terre)", mots("pomme"))
    assert fruit > plat


def test_le_mot_exact_passe_devant_le_prefixe():
    exact = pertinence("Pomme, crue", mots("pomme"))
    prefixe = pertinence("Pommes de terre, cuites", mots("pomme"))
    assert exact > prefixe


def test_ciqual_trouve_le_fruit_avant_les_preparations():
    premier = chercher_ciqual("pomme", 1)[0]
    assert premier.nom.lower().startswith("pomme")
    assert "terre" not in premier.nom.lower()


def test_ciqual_trouve_le_yaourt_nature_malgre_lordre_des_mots():
    assert any("yaourt" in a.nom.lower() for a in chercher_ciqual("yaourt nature"))


# --- Recherche par l'API -----------------------------------------------------------


def test_recherche_locale_renvoie_ciqual(client):
    resultats = client.get("/api/search", params={"q": "banane"}).json()["results"]
    assert resultats
    assert resultats[0]["source"] == "ciqual"
    assert resultats[0]["kcal_100g"] > 0


def test_le_stock_passe_devant_les_aliments_generiques(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 2})
    resultats = client.get("/api/search", params={"q": "nutella"}).json()["results"]
    assert resultats[0]["source"] == "catalogue"
    assert resultats[0]["in_stock"] == 2


def test_recherche_open_food_facts(client):
    reponse = client.get("/api/search", params={"q": "skyr", "scope": "off"}).json()
    assert reponse["off_unavailable"] is False
    assert reponse["results"][0]["brand"] == "Danone"


def test_panne_open_food_facts_signalee_sans_erreur(client):
    reponse = client.get("/api/search", params={"q": "panne", "scope": "off"})
    assert reponse.status_code == 200
    assert reponse.json()["off_unavailable"] is True


# --- Journal ---------------------------------------------------------------------------


def test_calories_calculees_sur_la_quantite(client):
    entree = client.post("/api/diary", json=saisie(grams=200)).json()
    assert entree["kcal"] == 290.0
    assert entree["gluc"] == pytest.approx(63.6, abs=0.1)


def test_totaux_du_jour_et_par_repas(client):
    client.post("/api/diary", json=saisie(meal="dejeuner", grams=100))
    client.post("/api/diary", json=saisie(meal="diner", grams=200))
    jour = client.get("/api/diary").json()
    assert jour["totals"]["kcal"] == 435.0
    assert jour["meals"]["dejeuner"]["kcal"] == 145.0
    assert jour["meals"]["diner"]["kcal"] == 290.0
    assert jour["meals"]["petit_dejeuner"]["kcal"] == 0


def test_les_jours_sont_separes(client):
    hier = (date.today() - timedelta(days=1)).isoformat()
    client.post("/api/diary", json=saisie(day=hier))
    assert client.get("/api/diary").json()["entries"] == []
    assert len(client.get("/api/diary", params={"day": hier}).json()["entries"]) == 1


def test_macros_absentes_ne_faussent_pas_le_total(client):
    client.post("/api/diary", json=saisie(prot_100g=None, gluc_100g=None, lip_100g=None))
    jour = client.get("/api/diary").json()
    assert jour["totals"]["kcal"] == 290.0
    assert jour["totals"]["prot"] == 0


def test_corriger_la_quantite_recalcule(client):
    entree = client.post("/api/diary", json=saisie(grams=100)).json()
    corrigee = client.patch(f"/api/diary/{entree['id']}", json={"grams": 300}).json()
    assert corrigee["kcal"] == 435.0


def test_supprimer_une_entree(client):
    entree = client.post("/api/diary", json=saisie()).json()
    client.delete(f"/api/diary/{entree['id']}")
    assert client.get("/api/diary").json()["entries"] == []


def test_valeurs_figees_au_moment_de_la_saisie(client):
    """Corriger une fiche produit ne doit pas réécrire les jours passés."""
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/diary", json=saisie(source="catalogue", ref=NUTELLA, label="Nutella",
                                          grams=20, kcal_100g=539))
    client.patch(f"/api/products/{NUTELLA}", json={"name": "Autre chose"})
    entree = client.get("/api/diary").json()["entries"][0]
    assert entree["label"] == "Nutella"
    assert entree["kcal"] == pytest.approx(107.8, abs=0.1)


def test_quantite_nulle_refusee(client):
    assert client.post("/api/diary", json=saisie(grams=0)).status_code == 422


def test_repas_inconnu_refuse(client):
    assert client.post("/api/diary", json=saisie(meal="gouter_royal")).status_code == 422


# --- Objectif ------------------------------------------------------------------------------


def test_objectif_calorique(client):
    assert client.get("/api/diary/settings").json()["goal_kcal"] is None
    client.put("/api/diary/settings", json={"goal_kcal": 2100})
    assert client.get("/api/diary").json()["goal_kcal"] == 2100
    client.put("/api/diary/settings", json={"goal_kcal": None})
    assert client.get("/api/diary/settings").json()["goal_kcal"] is None


def test_objectif_absurde_refuse(client):
    assert client.put("/api/diary/settings", json={"goal_kcal": 50}).status_code == 422


# --- Aliments récents ----------------------------------------------------------------------


def test_recents_sans_doublon_et_avec_la_derniere_quantite(client):
    client.post("/api/diary", json=saisie(label="Skyr", ref="A", grams=150))
    client.post("/api/diary", json=saisie(label="Riz", ref="B", grams=200))
    client.post("/api/diary", json=saisie(label="Skyr", ref="A", grams=170))

    recents = client.get("/api/diary/recent").json()
    assert [r["name"] for r in recents] == ["Skyr", "Riz"]
    assert recents[0]["portion_g"] == 170


# --- Le seul pont avec le stock : « j'ai fini le paquet » -----------------------------


def test_par_defaut_le_journal_ne_touche_pas_au_stock(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 2})
    client.post("/api/diary", json=saisie(source="catalogue", ref=NUTELLA, label="Nutella",
                                          grams=20, kcal_100g=539))
    assert client.get("/api/stock").json()[0]["total"] == 2


def test_paquet_fini_retire_une_unite(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 2})
    client.post("/api/diary", json=saisie(source="catalogue", ref=NUTELLA, label="Nutella",
                                          grams=20, kcal_100g=539, finished_pack=True))
    assert client.get("/api/stock").json()[0]["total"] == 1


def test_paquet_fini_alimente_les_courses_et_le_journal_des_sorties(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/diary", json=saisie(source="catalogue", ref=NUTELLA, label="Nutella",
                                          grams=20, kcal_100g=539, finished_pack=True))
    assert any(i["barcode"] == NUTELLA for i in client.get("/api/shopping").json())
    sorties = client.get("/api/history", params={"kind": "out"}).json()
    assert sorties[0]["barcode"] == NUTELLA


def test_paquet_fini_refuse_hors_stock(client):
    reponse = client.post("/api/diary", json=saisie(finished_pack=True))
    assert reponse.status_code == 400
    assert client.get("/api/diary").json()["entries"] == []  # rien n'est écrit


def test_paquet_fini_refuse_sur_stock_vide(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/stock/out", json={"barcode": NUTELLA})
    reponse = client.post("/api/diary", json=saisie(source="catalogue", ref=NUTELLA,
                                                     label="Nutella", finished_pack=True))
    assert reponse.status_code == 409
    assert client.get("/api/diary").json()["entries"] == []


# --- Rafraîchir une fiche depuis Open Food Facts ------------------------------------


def test_un_produit_scanne_recupere_ses_valeurs_nutritionnelles(client):
    produit = client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1}).json()["product"]
    assert produit["kcal_100g"] == 539.0
    assert produit["portion_g"] == 15.0


def test_rafraichir_complete_une_fiche_sans_valeurs(client, db):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    db.execute("UPDATE products SET kcal_100g = NULL, categories = 'Nutella' WHERE barcode = ?",
               (NUTELLA,))
    db.commit()

    produit = client.post(f"/api/products/{NUTELLA}/refresh").json()
    assert produit["kcal_100g"] == 539.0
    assert produit["categories"] == "pâtes à tartiner"


def test_rafraichir_ne_touche_pas_aux_corrections_manuelles(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.patch(f"/api/products/{NUTELLA}", json={"name": "Le pot du petit-déj", "brand": "Maison"})
    produit = client.post(f"/api/products/{NUTELLA}/refresh").json()
    assert produit["name"] == "Le pot du petit-déj"
    assert produit["brand"] == "Maison"


def test_rafraichir_un_produit_inconnu(client):
    assert client.post("/api/products/0000000000000/refresh").status_code == 404


def test_pas_de_double_arrondi(client):
    """5,46 g doit rester 5,46 côté serveur : arrondi au dixième (5,5) puis à
    l'unité à l'affichage, il devenait 6 alors que la feuille d'ajout disait 5."""
    entree = client.post("/api/diary", json=saisie(grams=140, gluc_100g=3.9)).json()
    assert entree["gluc"] == pytest.approx(5.46, abs=0.001)
    assert round(entree["gluc"]) == 5
    assert round(client.get("/api/diary").json()["totals"]["gluc"]) == 5


def test_pluriel_et_feminin_trouvent_le_singulier():
    """« complètes » doit trouver « complet » : le français fléchit."""
    assert pertinence("Pâtes au blé complet, cuites", mots("pates completes")) is not None
    assert pertinence("Pomme, crue", mots("pommes")) is not None
    assert pertinence("Carotte, cuite", mots("carottes cuites")) is not None


def test_la_flexion_ne_devient_pas_une_racine_trop_large():
    """« laitière » ne doit pas tout ramasser parce que « lait » en est le début."""
    assert pertinence("Lait demi-écrémé", mots("laitiere")) is None


def test_le_pluriel_garde_le_produit_de_base_en_tete():
    """« pommes » ne doit pas faire passer le chausson aux pommes devant le fruit."""
    fruit = pertinence("Pomme, crue", mots("pommes"))
    chausson = pertinence("Chausson aux pommes", mots("pommes"))
    assert fruit > chausson
    assert pertinence("Poulet, viande, crue", mots("poulets")) > pertinence(
        "Burger au poulet", mots("poulets")
    )


def test_poulets_trouve_le_poulet_et_non_la_poule():
    """« poulets » n'est pas « poule » + une flexion : c'est un autre mot."""
    assert not __import__("miamstock.nutrition", fromlist=["meme_mot"]).meme_mot("poule", "poulets")
    premier = chercher_ciqual("poulets", 1)[0]
    assert premier.nom.lower().startswith("poulet")


# --- Saisie rapide -------------------------------------------------------------------


def rapide(**champs):
    base = {"day": AUJOURDHUI, "meal": "diner", "label": "Restaurant", "source": "rapide",
            "kcal_100g": 900}
    base.update(champs)
    return base


def test_saisie_rapide_compte_ses_calories_telles_quelles(client):
    entree = client.post("/api/diary", json=rapide()).json()
    assert entree["kcal"] == 900
    assert entree["grams"] == 100
    assert client.get("/api/diary").json()["totals"]["kcal"] == 900


def test_saisie_rapide_ignore_un_poids_envoye(client):
    entree = client.post("/api/diary", json=rapide(grams=350)).json()
    assert entree["grams"] == 100
    assert entree["kcal"] == 900


def test_saisie_rapide_depasse_1000_kcal(client):
    assert client.post("/api/diary", json=rapide(kcal_100g=1800)).status_code == 201
    assert client.post("/api/diary", json=rapide(kcal_100g=9000)).status_code == 422


def test_un_aliment_pese_reste_borne_a_1000_kcal_pour_100g(client):
    assert client.post("/api/diary", json=saisie(kcal_100g=1800)).status_code == 422
    assert client.post("/api/diary", json=saisie(prot_100g=150)).status_code == 422


def test_saisie_rapide_avec_macros(client):
    entree = client.post("/api/diary", json=rapide(prot_100g=45, gluc_100g=90, lip_100g=38)).json()
    assert (entree["prot"], entree["gluc"], entree["lip"]) == (45, 90, 38)


def test_saisie_rapide_se_corrige_en_calories_pas_en_grammes(client):
    entree = client.post("/api/diary", json=rapide()).json()
    assert client.patch(f"/api/diary/{entree['id']}", json={"grams": 50}).status_code == 400
    corrigee = client.patch(f"/api/diary/{entree['id']}", json={"kcal_100g": 750}).json()
    assert corrigee["kcal"] == 750


def test_un_aliment_pese_ne_se_corrige_pas_en_calories(client):
    entree = client.post("/api/diary", json=saisie()).json()
    assert client.patch(f"/api/diary/{entree['id']}", json={"kcal_100g": 10}).status_code == 400


def test_saisie_rapide_dans_les_recents(client):
    client.post("/api/diary", json=rapide(label="Kebab", kcal_100g=800))
    recent = client.get("/api/diary/recent").json()[0]
    assert (recent["source"], recent["name"], recent["kcal_100g"]) == ("rapide", "Kebab", 800)


def test_saisie_rapide_ne_peut_pas_vider_un_paquet(client):
    reponse = client.post("/api/diary", json=rapide(finished_pack=True))
    assert reponse.status_code == 400


# --- « Comme hier » ------------------------------------------------------------------


HIER = (date.today() - timedelta(days=1)).isoformat()


def test_un_repas_vide_propose_la_derniere_fois(client):
    client.post("/api/diary", json=saisie(day=HIER, meal="petit_dejeuner", label="Skyr",
                                          grams=150, kcal_100g=60))
    client.post("/api/diary", json=saisie(day=HIER, meal="petit_dejeuner", label="Muesli",
                                          grams=50, kcal_100g=380))
    suggestions = client.get("/api/diary").json()["suggestions"]
    assert suggestions == [{
        "meal": "petit_dejeuner", "from_day": HIER, "count": 2, "kcal": 280,
        "labels": ["Skyr", "Muesli"],
    }]


def test_pas_de_suggestion_pour_un_repas_deja_rempli(client):
    client.post("/api/diary", json=saisie(day=HIER, meal="dejeuner"))
    client.post("/api/diary", json=saisie(meal="dejeuner"))
    assert client.get("/api/diary").json()["suggestions"] == []


def test_la_suggestion_prend_le_jour_le_plus_recent(client):
    avant_hier = (date.today() - timedelta(days=2)).isoformat()
    client.post("/api/diary", json=saisie(day=avant_hier, meal="diner", label="Soupe"))
    client.post("/api/diary", json=saisie(day=HIER, meal="diner", label="Pâtes"))
    suggestion = client.get("/api/diary").json()["suggestions"][0]
    assert (suggestion["from_day"], suggestion["labels"]) == (HIER, ["Pâtes"])


def test_pas_de_suggestion_au_dela_de_deux_semaines(client):
    lointain = (date.today() - timedelta(days=20)).isoformat()
    client.post("/api/diary", json=saisie(day=lointain, meal="diner"))
    assert client.get("/api/diary").json()["suggestions"] == []


def test_reprendre_un_repas_le_recopie(client):
    client.post("/api/diary", json=saisie(day=HIER, meal="petit_dejeuner", label="Skyr",
                                          grams=150, kcal_100g=60))
    jour = client.post("/api/diary/repeat", json={
        "day": AUJOURDHUI, "meal": "petit_dejeuner", "from_day": HIER,
    }).json()
    assert [(e["label"], e["grams"]) for e in jour["entries"]] == [("Skyr", 150)]
    assert jour["totals"]["kcal"] == 90
    assert jour["suggestions"] == []
    # La veille reste intacte.
    assert len(client.get(f"/api/diary?day={HIER}").json()["entries"]) == 1


def test_reprendre_un_repas_vide_echoue(client):
    reponse = client.post("/api/diary/repeat", json={
        "day": AUJOURDHUI, "meal": "diner", "from_day": HIER,
    })
    assert reponse.status_code == 404


def test_reprendre_ne_touche_pas_au_stock(client, locations):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "location_id": locations["pantry"]})
    client.post("/api/diary", json=saisie(day=HIER, source="catalogue", ref=NUTELLA,
                                          label="Nutella", grams=15, kcal_100g=539,
                                          finished_pack=True))
    client.post("/api/stock/in", json={"barcode": NUTELLA, "location_id": locations["pantry"]})
    client.post("/api/diary/repeat", json={"day": AUJOURDHUI, "meal": "dejeuner", "from_day": HIER})
    assert client.get(f"/api/lookup/{NUTELLA}").json()["in_stock"] == 1


# --- Repas favoris ---------------------------------------------------------------


def petit_dej(client, jour=AUJOURDHUI):
    client.post("/api/diary", json=saisie(day=jour, meal="petit_dejeuner", label="Skyr",
                                          grams=150, kcal_100g=60, prot_100g=10))
    client.post("/api/diary", json=saisie(day=jour, meal="petit_dejeuner", label="Banane",
                                          grams=120, kcal_100g=90, prot_100g=1))


def test_enregistrer_un_repas_favori(client):
    petit_dej(client)
    favori = client.post("/api/diary/templates", json={
        "name": "Petit-déj habituel", "day": AUJOURDHUI, "meal": "petit_dejeuner",
    })
    assert favori.status_code == 201
    assert favori.json() == {
        "id": favori.json()["id"], "name": "Petit-déj habituel", "count": 2, "kcal": 198,
        "labels": ["Skyr", "Banane"],
    }
    assert [f["name"] for f in client.get("/api/diary/templates").json()] == ["Petit-déj habituel"]


def test_un_favori_vide_est_refuse(client):
    reponse = client.post("/api/diary/templates", json={
        "name": "Rien", "day": AUJOURDHUI, "meal": "diner",
    })
    assert reponse.status_code == 400


def test_deux_favoris_du_meme_nom_refuses(client):
    petit_dej(client)
    corps = {"name": "Matin", "day": AUJOURDHUI, "meal": "petit_dejeuner"}
    assert client.post("/api/diary/templates", json=corps).status_code == 201
    corps["name"] = "matin"
    assert client.post("/api/diary/templates", json=corps).status_code == 409


def test_appliquer_un_favori_a_un_autre_repas(client):
    petit_dej(client, HIER)
    favori = client.post("/api/diary/templates", json={
        "name": "Matin", "day": HIER, "meal": "petit_dejeuner",
    }).json()
    jour = client.post(f"/api/diary/templates/{favori['id']}/apply", json={
        "day": AUJOURDHUI, "meal": "collation",
    }).json()
    assert [(e["meal"], e["label"]) for e in jour["entries"]] == [
        ("collation", "Skyr"), ("collation", "Banane"),
    ]
    assert jour["totals"]["prot"] == pytest.approx(16.2)


def test_le_favori_survit_a_la_suppression_du_jour(client):
    petit_dej(client)
    favori = client.post("/api/diary/templates", json={
        "name": "Matin", "day": AUJOURDHUI, "meal": "petit_dejeuner",
    }).json()
    for entree in client.get("/api/diary").json()["entries"]:
        client.delete(f"/api/diary/{entree['id']}")
    assert client.get("/api/diary/templates").json()[0]["count"] == 2
    assert client.post(f"/api/diary/templates/{favori['id']}/apply", json={
        "day": AUJOURDHUI, "meal": "petit_dejeuner",
    }).status_code == 200


def test_supprimer_un_favori(client, db):
    petit_dej(client)
    favori = client.post("/api/diary/templates", json={
        "name": "Matin", "day": AUJOURDHUI, "meal": "petit_dejeuner",
    }).json()
    assert client.delete(f"/api/diary/templates/{favori['id']}").status_code == 204
    assert client.get("/api/diary/templates").json() == []
    # Les aliments du favori partent avec lui.
    assert db.execute("SELECT COUNT(*) FROM meal_template_items").fetchone()[0] == 0
    assert client.post(f"/api/diary/templates/{favori['id']}/apply", json={
        "day": AUJOURDHUI, "meal": "petit_dejeuner",
    }).status_code == 404
