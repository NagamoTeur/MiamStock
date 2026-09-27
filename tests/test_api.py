"""Tests de bout en bout de l'API : bips, FIFO, alertes DLC, courses, auth."""

from __future__ import annotations

import pytest
from datetime import date, timedelta

NUTELLA = "3017620422003"
YAOURT = "3033490004743"


def in_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


# --- Authentification --------------------------------------------------------


def test_api_refuse_sans_session(anon_client):
    assert anon_client.get("/api/stock").status_code == 401


def test_mauvais_pin_refuse(anon_client):
    assert anon_client.post("/api/session", json={"pin": "0000"}).status_code == 401


def test_bon_pin_ouvre_la_session(anon_client):
    assert anon_client.post("/api/session", json={"pin": "1234"}).json()["authenticated"] is True
    assert anon_client.get("/api/stock").status_code == 200


# --- Recherche de code-barres ------------------------------------------------


def test_lookup_produit_connu_dopenfoodfacts(client):
    body = client.get(f"/api/lookup/{NUTELLA}").json()
    assert body["found"] is True
    assert body["known_locally"] is False
    assert body["product"]["name"] == "Nutella"
    assert body["product"]["net_quantity"] == "400 g"


def test_lookup_ninscrit_rien_en_base(client):
    client.get(f"/api/lookup/{NUTELLA}")
    assert client.get(f"/api/products/{NUTELLA}").status_code == 404


def test_lookup_code_inconnu(client):
    body = client.get("/api/lookup/0000000000000").json()
    assert body["found"] is False
    assert body["product"] is None


# --- Bip d'entrée ------------------------------------------------------------


def test_bip_entree_cree_produit_et_lot(client, locations):
    line = client.post(
        "/api/stock/in",
        json={"barcode": NUTELLA, "quantity": 2, "expires_on": in_days(200),
              "location_id": locations["pantry"]},
    ).json()
    assert line["product"]["name"] == "Nutella"
    assert line["total"] == 2
    assert len(line["lots"]) == 1
    assert line["lots"][0]["location_name"] == "Placard"


def test_produit_inconnu_exige_un_nom(client):
    refus = client.post("/api/stock/in", json={"barcode": "0000000000000"})
    assert refus.status_code == 404

    accepte = client.post(
        "/api/stock/in", json={"barcode": "0000000000000", "name": "Pommes du jardin"}
    )
    assert accepte.status_code == 201
    assert accepte.json()["product"]["name"] == "Pommes du jardin"
    assert accepte.json()["product"]["source"] == "manual"


def test_deux_bips_creent_deux_lots_distincts(client, locations):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 4,
                                       "expires_on": in_days(10),
                                       "location_id": locations["fridge"]})
    line = client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 4,
                                              "expires_on": in_days(2),
                                              "location_id": locations["fridge"]}).json()
    assert line["total"] == 8
    assert len(line["lots"]) == 2
    # Le lot le plus urgent est présenté en premier.
    assert line["lots"][0]["expires_on"] == in_days(2)


def test_emplacement_et_duree_memorises_pour_le_prochain_scan(client, locations):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1,
                                       "expires_on": in_days(12),
                                       "location_id": locations["fridge"]})
    suggestion = client.get(f"/api/lookup/{YAOURT}").json()
    assert suggestion["known_locally"] is True
    assert suggestion["suggested_location_id"] == locations["fridge"]
    assert suggestion["suggested_shelf_life_days"] == 12
    assert suggestion["in_stock"] == 1


def test_emplacement_inexistant_refuse(client):
    response = client.post("/api/stock/in", json={"barcode": NUTELLA, "location_id": 9999})
    assert response.status_code == 400


# --- Bip de sortie et FIFO ---------------------------------------------------


def test_sortie_consomme_le_lot_le_plus_urgent(client, locations):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 2,
                                       "expires_on": in_days(30),
                                       "location_id": locations["fridge"]})
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 2,
                                       "expires_on": in_days(1),
                                       "location_id": locations["fridge"]})

    result = client.post("/api/stock/out", json={"barcode": YAOURT, "quantity": 1}).json()
    assert result["consumed"] == 1
    assert result["remaining_total"] == 3
    assert result["consumed_lots"][0]["expires_on"] == in_days(1)


def test_sortie_deborde_sur_le_lot_suivant(client, locations):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 2,
                                       "expires_on": in_days(30)})
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 2,
                                       "expires_on": in_days(1)})

    result = client.post("/api/stock/out", json={"barcode": YAOURT, "quantity": 3}).json()
    assert result["consumed"] == 3
    assert [lot["expires_on"] for lot in result["consumed_lots"]] == [in_days(1), in_days(30)]
    assert result["remaining_total"] == 1


def test_lots_sans_dlc_consommes_en_dernier(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1,
                                       "expires_on": in_days(60)})
    result = client.post("/api/stock/out", json={"barcode": NUTELLA, "quantity": 1}).json()
    assert result["consumed_lots"][0]["expires_on"] == in_days(60)


def test_sortie_plus_que_le_stock_ne_descend_pas_sous_zero(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    result = client.post("/api/stock/out", json={"barcode": NUTELLA, "quantity": 5}).json()
    assert result["requested"] == 5
    assert result["consumed"] == 1
    assert result["remaining_total"] == 0
    assert client.get("/api/stock").json() == []


def test_sortie_sur_stock_vide_refusee(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/stock/out", json={"barcode": NUTELLA, "quantity": 1})
    assert client.post("/api/stock/out", json={"barcode": NUTELLA}).status_code == 409


def test_sortie_produit_jamais_scanne_refusee(client):
    assert client.post("/api/stock/out", json={"barcode": NUTELLA}).status_code == 404


# --- Statuts de DLC ----------------------------------------------------------


def test_statuts_selon_lecheance(client, locations):
    fridge = locations["fridge"]
    for days in (-1, 2, 5, 40):
        client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1,
                                           "expires_on": in_days(days),
                                           "location_id": fridge})
    statuses = {lot["expires_on"]: lot["status"]
                for lot in client.get("/api/stock").json()[0]["lots"]}
    assert statuses[in_days(-1)] == "expired"
    assert statuses[in_days(2)] == "urgent"
    assert statuses[in_days(5)] == "soon"
    assert statuses[in_days(40)] == "ok"


def test_congelateur_nalerte_pas_avant_la_date(client, locations):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1,
                                       "expires_on": in_days(2),
                                       "location_id": locations["freezer"]})
    assert client.get("/api/stock").json()[0]["lots"][0]["status"] == "ok"
    assert client.get("/api/expiring").json() == []


def test_congelateur_alerte_quand_la_date_est_passee(client, locations):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1,
                                       "expires_on": in_days(-3),
                                       "location_id": locations["freezer"]})
    assert client.get("/api/stock").json()[0]["lots"][0]["status"] == "expired"


def test_onglet_a_consommer_ne_garde_que_lurgent(client, locations):
    fridge = locations["fridge"]
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 3,
                                       "expires_on": in_days(1), "location_id": fridge})
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 5,
                                       "expires_on": in_days(90), "location_id": fridge})
    lines = client.get("/api/expiring").json()
    assert len(lines) == 1
    # Le lot lointain est exclu, et le total reflète uniquement ce qui est à consommer.
    assert lines[0]["total"] == 3
    assert len(lines[0]["lots"]) == 1


def test_resume_compte_les_alertes(client, locations):
    fridge = locations["fridge"]
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1,
                                       "expires_on": in_days(-1), "location_id": fridge})
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 2,
                                       "expires_on": in_days(1), "location_id": fridge})
    summary = client.get("/api/summary").json()
    assert summary["expired"] == 1
    assert summary["urgent"] == 1
    assert summary["distinct_products"] == 2
    assert summary["total_items"] == 3


# --- Liste de courses --------------------------------------------------------


def test_stock_epuise_bascule_en_courses(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    result = client.post("/api/stock/out", json={"barcode": NUTELLA}).json()
    assert result["added_to_shopping"] is True
    items = client.get("/api/shopping").json()
    assert [item["label"] for item in items] == ["Nutella"]
    assert items[0]["auto"] is True


def test_option_permet_de_ne_pas_ajouter_aux_courses(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    result = client.post(
        "/api/stock/out", json={"barcode": NUTELLA, "add_to_shopping": False}
    ).json()
    assert result["added_to_shopping"] is False
    assert client.get("/api/shopping").json() == []


def test_seuil_mini_declenche_avant_epuisement(client):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 4})
    client.patch(f"/api/products/{YAOURT}", json={"min_quantity": 2})
    # Le seuil est déjà respecté (4 > 2) : rien ne doit apparaître.
    assert client.get("/api/shopping").json() == []

    result = client.post("/api/stock/out", json={"barcode": YAOURT, "quantity": 2}).json()
    assert result["remaining_total"] == 2
    assert result["added_to_shopping"] is True


def test_seuil_deja_franchi_alimente_la_liste_immediatement(client):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1})
    client.patch(f"/api/products/{YAOURT}", json={"min_quantity": 3})
    items = client.get("/api/shopping").json()
    assert len(items) == 1
    assert items[0]["quantity"] == 2  # il manque 2 exemplaires pour atteindre le seuil


def test_rentrer_le_produit_le_sort_de_la_liste(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/stock/out", json={"barcode": NUTELLA})
    assert len(client.get("/api/shopping").json()) == 1

    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    assert client.get("/api/shopping").json() == []


def test_ligne_libre_et_nettoyage_des_coches(client):
    item = client.post("/api/shopping", json={"label": "Pain", "quantity": 2}).json()
    assert item["label"] == "Pain"
    assert item["auto"] is False

    client.patch(f"/api/shopping/{item['id']}", json={"checked": True})
    assert client.request("DELETE", "/api/shopping/checked/all").json()["removed"] == 1
    assert client.get("/api/shopping").json() == []


def test_ajout_sans_libelle_ni_code_refuse(client):
    assert client.post("/api/shopping", json={}).status_code == 400


def test_ajout_double_cumule_les_quantites(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/shopping", json={"barcode": NUTELLA, "quantity": 1})
    item = client.post("/api/shopping", json={"barcode": NUTELLA, "quantity": 2}).json()
    assert item["quantity"] == 3
    assert len(client.get("/api/shopping").json()) == 1


# --- Édition des lots --------------------------------------------------------


def test_corriger_la_dlc_dun_lot(client, locations):
    line = client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 2,
                                              "expires_on": in_days(30),
                                              "location_id": locations["fridge"]}).json()
    lot_id = line["lots"][0]["id"]
    updated = client.patch(f"/api/lots/{lot_id}", json={"expires_on": in_days(1)}).json()
    assert updated["lots"][0]["status"] == "urgent"


def test_vider_un_lot_le_supprime(client):
    line = client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1}).json()
    updated = client.patch(f"/api/lots/{line['lots'][0]['id']}", json={"quantity": 0}).json()
    assert updated["total"] == 0
    assert updated["lots"] == []


def test_jeter_un_lot_alimente_les_courses(client):
    line = client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1,
                                              "expires_on": in_days(-2)}).json()
    assert client.delete(f"/api/lots/{line['lots'][0]['id']}").status_code == 204
    assert client.get("/api/stock").json() == []
    assert len(client.get("/api/shopping").json()) == 1


def test_recherche_dans_le_stock(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1})
    assert len(client.get("/api/stock", params={"q": "nut"}).json()) == 1
    assert len(client.get("/api/stock", params={"q": "danone"}).json()) == 1
    assert client.get("/api/stock", params={"q": "zzz"}).json() == []


def test_filtre_par_emplacement(client, locations):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1,
                                       "location_id": locations["pantry"]})
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1,
                                       "location_id": locations["fridge"]})
    lines = client.get("/api/stock", params={"location_id": locations["fridge"]}).json()
    assert [line["product"]["barcode"] for line in lines] == [YAOURT]


def test_historique_journalise_les_bips(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 2})
    client.post("/api/stock/out", json={"barcode": NUTELLA, "quantity": 1})
    kinds = [event["kind"] for event in client.get("/api/history").json()]
    assert "in" in kinds and "out" in kinds


# --- Fiche produit et saisie manuelle enrichie --------------------------------


def test_produit_inconnu_accepte_ses_propres_valeurs(client):
    line = client.post(
        "/api/stock/in",
        json={
            "barcode": "2000000000012",
            "quantity": 3,
            "name": "Confiture de mirabelles",
            "brand": "Mamie",
            "net_quantity": "350 g",
        },
    ).json()
    product = line["product"]
    assert product["name"] == "Confiture de mirabelles"
    assert product["brand"] == "Mamie"
    assert product["net_quantity"] == "350 g"
    assert product["source"] == "manual"


def test_valeurs_saisies_priment_sur_openfoodfacts(client):
    # Open Food Facts nomme ce code « Nutella » ; l'utilisateur sait mieux.
    line = client.post(
        "/api/stock/in",
        json={"barcode": NUTELLA, "name": "Pâte à tartiner maison", "brand": "Maison"},
    ).json()
    assert line["product"]["name"] == "Pâte à tartiner maison"
    assert line["product"]["brand"] == "Maison"
    # Les champs non saisis restent ceux d'Open Food Facts.
    assert line["product"]["net_quantity"] == "400 g"


def test_corriger_un_produit_deja_en_base(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    product = client.patch(
        f"/api/products/{NUTELLA}",
        json={"name": "Nutella (grand pot)", "brand": "Ferrero", "net_quantity": "750 g"},
    ).json()
    assert product["name"] == "Nutella (grand pot)"
    assert product["brand"] == "Ferrero"
    assert product["net_quantity"] == "750 g"


def test_second_bip_nefface_pas_une_correction_manuelle(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.patch(f"/api/products/{NUTELLA}", json={"name": "Le pot du petit-déj"})
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    assert client.get(f"/api/products/{NUTELLA}").json()["name"] == "Le pot du petit-déj"


# --- Catalogue ----------------------------------------------------------------


def test_catalogue_garde_les_produits_a_zero(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/stock/out", json={"barcode": NUTELLA, "quantity": 1})

    # Le stock est vide, le catalogue non : c'est toute la différence.
    assert client.get("/api/stock").json() == []
    catalog = client.get("/api/products").json()
    assert len(catalog) == 1
    assert catalog[0]["in_stock"] == 0
    assert catalog[0]["on_shopping_list"] is True


def test_catalogue_compte_lots_et_prochaine_dlc(client, locations):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 2,
                                       "expires_on": in_days(20),
                                       "location_id": locations["fridge"]})
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 2,
                                       "expires_on": in_days(4),
                                       "location_id": locations["fridge"]})
    entry = client.get("/api/products").json()[0]
    assert entry["in_stock"] == 4
    assert entry["lot_count"] == 2
    assert entry["next_expiry"] == in_days(4)


def test_catalogue_filtre_et_recherche(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 1})
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1})
    client.post("/api/stock/out", json={"barcode": YAOURT, "quantity": 1})

    assert len(client.get("/api/products", params={"in_stock": True}).json()) == 1
    assert len(client.get("/api/products", params={"in_stock": False}).json()) == 1
    assert len(client.get("/api/products", params={"q": "nut"}).json()) == 1


# --- Historique ---------------------------------------------------------------


def test_historique_filtrable_par_produit_et_par_type(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 2})
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 2})
    client.post("/api/stock/out", json={"barcode": NUTELLA, "quantity": 1})

    par_produit = client.get("/api/history", params={"barcode": NUTELLA}).json()
    assert {event["kind"] for event in par_produit} == {"in", "out"}
    assert all(event["barcode"] == NUTELLA for event in par_produit)

    entrees = client.get("/api/history", params={"kind": "in"}).json()
    assert len(entrees) == 2
    assert entrees[0]["name"] is not None


# --- Statistiques -------------------------------------------------------------


def test_statistiques_calculent_le_gaspillage(client):
    line = client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 10}).json()
    client.post("/api/stock/out", json={"barcode": NUTELLA, "quantity": 3})
    client.delete(f"/api/lots/{line['lots'][0]['id']}")  # jette les 7 restants

    stats = client.get("/api/stats").json()
    assert stats["entered"] == 10
    assert stats["consumed"] == 3
    assert stats["discarded"] == 7
    assert stats["waste_ratio"] == 0.7
    assert stats["most_wasted"][0]["name"] == "Nutella"
    assert stats["most_wasted"][0]["quantity"] == 7


def test_statistiques_sans_donnees_ne_divisent_pas_par_zero(client):
    stats = client.get("/api/stats").json()
    assert stats["waste_ratio"] == 0.0
    assert stats["most_wasted"] == []


def test_produit_deja_perime_ne_fixe_pas_une_conservation_negative(client):
    """Rentrer un produit dont la DLC est passée ne dit rien de sa conservation."""
    client.post(
        "/api/stock/in",
        json={"barcode": YAOURT, "quantity": 1, "expires_on": in_days(-2)},
    )
    assert client.get(f"/api/products/{YAOURT}").json()["default_shelf_life_days"] is None


def test_conservation_deduite_dune_dlc_future(client):
    client.post(
        "/api/stock/in",
        json={"barcode": YAOURT, "quantity": 1, "expires_on": in_days(21)},
    )
    assert client.get(f"/api/products/{YAOURT}").json()["default_shelf_life_days"] == 21


# --- Rythme de consommation ---------------------------------------------------


def test_produit_sans_sortie_absent_du_rythme(client):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 5})
    assert client.get("/api/consumption").json() == []


def test_rythme_rapporte_a_la_periode_observee(client, journal):
    """Quatre unités sorties sur 28 jours font une par semaine, pas 4/90e."""
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 20})
    for age in (28, 21, 14, 7):
        journal(YAOURT, "out", 1, age)

    entry = client.get("/api/consumption").json()[0]
    assert entry["consumed"] == 4
    assert entry["per_week"] == 1.0
    assert entry["events"] == 4


def test_le_jete_compte_dans_ce_qui_vide_letagere(client, journal):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 20})
    journal(YAOURT, "out", 2, 21)
    journal(YAOURT, "discard", 2, 14)
    journal(YAOURT, "out", 3, 7)

    entry = client.get("/api/consumption").json()[0]
    assert entry["consumed"] == 5
    assert entry["discarded"] == 2
    # 7 unités sorties sur 21 jours observés.
    assert entry["per_week"] == pytest.approx(7 / 21 * 7, abs=0.05)


def test_historique_trop_maigre_nest_pas_presente_comme_mesure(client, journal):
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 5})
    journal(NUTELLA, "out", 1, 2)
    journal(NUTELLA, "out", 1, 1)

    entry = client.get("/api/consumption").json()[0]
    assert entry["reliable"] is False
    assert entry["suggested_min"] is None


def test_seuil_propose_couvre_une_semaine_de_consommation(client, journal):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 20})
    for age in (28, 21, 14, 7):
        journal(YAOURT, "out", 4, age)

    entry = client.get("/api/consumption").json()[0]
    assert entry["reliable"] is True
    assert entry["per_week"] == 4.0
    assert entry["suggested_min"] == 4


def test_duree_de_couverture_reglable(client, journal):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 20})
    for age in (28, 21, 14, 7):
        journal(YAOURT, "out", 4, age)

    quinzaine = client.get("/api/consumption", params={"cover_days": 14}).json()[0]
    assert quinzaine["suggested_min"] == 8


def test_jours_restants_et_tri_par_urgence(client, journal):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 2})
    client.post("/api/stock/in", json={"barcode": NUTELLA, "quantity": 20})
    for age in (28, 21, 14, 7):
        journal(YAOURT, "out", 4, age)
        journal(NUTELLA, "out", 1, age)

    entries = client.get("/api/consumption").json()
    # Le Skyr part à 4 par semaine avec 2 en stock : il s'épuise bien avant.
    assert entries[0]["barcode"] == YAOURT
    assert entries[0]["days_left"] == pytest.approx(3.5, abs=0.1)
    assert entries[1]["days_left"] > entries[0]["days_left"]


def test_fenetre_dobservation_exclut_les_vieux_mouvements(client, journal):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 20})
    journal(YAOURT, "out", 50, 200)  # hors fenêtre de 90 jours
    journal(YAOURT, "out", 1, 10)

    entry = client.get("/api/consumption", params={"days": 90}).json()[0]
    assert entry["consumed"] == 1


def test_ligne_de_courses_porte_de_quoi_deviner_son_rayon(client, locations):
    client.post("/api/stock/in", json={"barcode": YAOURT, "quantity": 1,
                                       "location_id": locations["fridge"]})
    client.post("/api/stock/out", json={"barcode": YAOURT, "quantity": 1})

    item = client.get("/api/shopping").json()[0]
    assert item["categories"] is not None
    assert item["location_kind"] == "fridge"
