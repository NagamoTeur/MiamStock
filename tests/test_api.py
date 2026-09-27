"""Tests de bout en bout de l'API : bips, FIFO, alertes DLC, courses, auth."""

from __future__ import annotations

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
