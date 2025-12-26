"""
This module matches a CV description embedding against job offers embeddings stored in a sqlite database.

"""
import sys
import numpy as np
import sqlalchemy as db
from sqlalchemy import create_engine, text
from pathlib import Path

# Import de la fonction de similarité depuis le shared module
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "shared" / "src"))
from shared.embeddings import TextSimilarity
from shared.embeddings.providers import create_sentence_transformers_embedder


SAMPLE_GOLD = Path(__file__).resolve().parents[1] / "sample_data" / "job_offers_gold.db"
SAMPLE_SILVER = Path(__file__).resolve().parents[1] / "sample_data" / "job_offers_silver.db"
SAMPLE_CV_DESCRIPTION_ENGINEER = "Ingénieur logiciel expérimenté avec une expertise en Python et apprentissage automatique."
SAMPLE_CV_DESCRIPTION_CARISTE = \
    """Cariste avec expérience en gestion de stocks et conduite de chariots élévateurs.
    Je suis certifié pour la conduite de chariots de catégorie 1, 3 et 5.
    J'ai travaillé dans des entrepôts à haut volume et je suis familier avec les systèmes de gestion d'inventaire.
    Rigoureux et soucieux de la sécurité, je cherche à contribuer à une équipe dynamique
    dans le secteur de la logistique. Je maitrise également les procédures de chargement et déchargement
    des marchandises, ainsi que les normes de sécurité en entrepôt: port des EPI, respect des consignes de sécurité.
    Je suis titulaire du CACES R489 et j'ai une bonne connaissance des règles de sécurité en milieu industriel"""
SAMPLE_CV_DESCRIPTION = SAMPLE_CV_DESCRIPTION_CARISTE


def load_dtb(db_path, mode="gold"):
    """
    Load job offers embeddings from a sqlite database.
    
    Args:
        db_path (str): Path to the sqlite database.
        mode (str): "gold" to load embeddings from gold database,
            
                    "silver" to load raw text from silver database.
    Returns:
        List of dicts with keys:
            - "id": offer id
            - "intitule_embedded" (if mode="gold"): numpy array of intitule embedding
            - "description_embedded" (if mode="gold"): numpy array of description embedding
            - "intitule" (if mode="silver"): raw intitule text
            - "description" (if mode="silver"): raw description text
    """
    engine = create_engine(f"sqlite:///{db_path}")
    conn = engine.connect()

    # Check tables
    inspector = db.inspect(engine)
    assert "offers" in inspector.get_table_names(), "Table 'offers' not found in database."

    if mode == "gold":
        query = text("SELECT id, intitule_embedded, description_embedded FROM offers")
    elif mode == "silver":
        query = text("SELECT id, intitule, description FROM offers")
    else:
        raise ValueError("mode must be 'gold' or 'silver'")

    result = conn.execute(query)
    offers = []
    for row in result:
        offer_id = row[0]
        if mode == "silver":
            offers.append({"id": offer_id,
                           "intitule": row[1],
                           "description": row[2]})
        elif mode == "gold":
            embedded_blob = row[1]
            i_embedded = np.frombuffer(embedded_blob, dtype=np.float64)
            embedded_blob = row[2]
            d_embedded = np.frombuffer(embedded_blob, dtype=np.float64)
            offers.append({"id": offer_id, "description_embedded": d_embedded,
                           "intitule_embedded": i_embedded})
        else:
            raise ValueError("mode must be 'gold' or 'silver'")

    conn.close()
    return offers


def main(cv_embedded, job_offers_db_path, method="description"):
    """
    Match a CV embedding against job offers embeddings stored in a sqlite database.

    Args:
        cv_embedded (np.ndarray): Embedding of the CV description.
        job_offers_db_path (str): Path to the job offers sqlite database.
        method (str): "intitule", "description" or "mix" to select matching method.
    Returns:
        
    """
    # load job offers embeddings sqlite database
    offers = load_dtb(job_offers_db_path, mode="gold")

    # compute similarities
    similarities = []
    for offer in offers:
        if method == "intitule":
            sim = TextSimilarity.cosine_similarity(cv_embedded, offer["intitule_embedded"])
        elif method == "description":
            sim = TextSimilarity.cosine_similarity(cv_embedded, offer["description_embedded"])
        elif method == "mix":
            # compute average embedding
            v1 = offer["intitule_embedded"]
            v2 = offer["description_embedded"]
            # avg_embarr = (v1 + v2) / 2
            sim1 = TextSimilarity.cosine_similarity(cv_embedded, v1)
            sim2 = TextSimilarity.cosine_similarity(cv_embedded, v2)
            sim = (sim1 + sim2) / 2

        similarities.append({"id": offer["id"], "similarity": sim})

    # sort by similarity descending
    similarities.sort(key=lambda x: x["similarity"], reverse=True)

    return similarities


def test_user_input(cv_description=SAMPLE_CV_DESCRIPTION,
                    job_offers_gold_db_path=SAMPLE_GOLD,
                    job_offers_silver_db_path=SAMPLE_SILVER):
    """Test the matching function with a user-provided CV description."""
    # init embedder    
    embedder = create_sentence_transformers_embedder(model="all-MiniLM-L6-v2", normalize=True)

    # Compute embedding for the CV description
    cv_embedded = embedder([cv_description])
    cv_embedded = cv_embedded[0]
    # test the matching function

    similarites_mix = main(
        cv_embedded,
        job_offers_gold_db_path,
        method="mix"
    )
    top_matches_mix = similarites_mix[:5]
    bottom_matches_mix = similarites_mix[-5:]

    similarites_title = main(
        cv_embedded,
        job_offers_gold_db_path,
        method="intitule"
    )
    top_matches_title = similarites_title[:5]
    bottom_matches_title = similarites_title[-5:]

    similarites_description = main(
        cv_embedded,
        job_offers_gold_db_path,
        method="description"
    )
    top_matches_description = similarites_description[:5]
    bottom_matches_description = similarites_description[-5:]

    # load silver data for displaying the details of the matched offers
    silver_data = load_dtb(job_offers_silver_db_path, mode="silver")

    # print cv description inputted
    print(f"Input CV description: {cv_description}\n")

    print("\nDetails of bottom matched job offers from Silver database:")
    for i_m, (match_d, match_t, match_m) in enumerate(
        zip(bottom_matches_description, bottom_matches_title, bottom_matches_mix)):
        offer_id_d = match_d["id"]
        offer_id_t = match_t["id"]
        offer_id_m = match_m["id"]
        for offer_id, mode, match in zip([offer_id_d, offer_id_t, offer_id_m],
                                  ["description", "intitule", "mix"],
                                  [match_d, match_t, match_m]):
            for offer in silver_data:
                if offer["id"] == offer_id:
                    if mode == "description":
                        print(f"--- Bottom {i_m+1} ---")
                    print(f"[{mode}] Offer ID: {offer_id}, Similarity: {match['similarity']:.4f}")
                    print(f"[{mode}] Intitule: {offer.get('intitule', 'N/A')}")
                    #print(f"Description: {offer.get('description', 'N/A')}\n")
                    break

    
    print("\nDetails of top matched job offers from Silver database:")
    for i_m, (match_d, match_t, match_m) in enumerate(
        zip(top_matches_description, top_matches_title, top_matches_mix)):
        offer_id_d = match_d["id"]
        offer_id_t = match_t["id"]
        offer_id_m = match_m["id"]
        for offer_id, mode, match in zip([offer_id_d, offer_id_t, offer_id_m],
                                         ["description", "intitule", "mix"],
                                         [match_d, match_t, match_m]):
            for offer in silver_data:
                if offer["id"] == offer_id:
                    if mode == "description":
                        print(f"--- Top {i_m+1} ---")
                    print(f"[{mode}] Offer ID: {offer_id}, Similarity: {match['similarity']:.4f}")
                    print(f"[{mode}] Intitule: {offer.get('intitule', 'N/A')}")
                    #print(f"Description: {offer.get('description', 'N/A')}\n")
                    break


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Match CV description against job offers embeddings.")
    parser.add_argument(
        "--cv_description",
        type=str,
        default=SAMPLE_CV_DESCRIPTION,
        help="CV description text to embed and match.",
    )
    parser.add_argument(
        "--job_offers_gold_db_path",
        type=str,
        default=str(SAMPLE_GOLD),
        help="Path to the job offers gold embeddings database (sqlite).",
    )
    parser.add_argument(
        "--job_offers_silver_db_path",
        type=str,
        default=str(SAMPLE_SILVER),
        help="Path to the job offers silver database (sqlite).",
    )
    args = parser.parse_args() 
    print(args)
    test_user_input(cv_description=args.cv_description,
                    job_offers_gold_db_path=args.job_offers_gold_db_path,
                    job_offers_silver_db_path=args.job_offers_silver_db_path
                    )
