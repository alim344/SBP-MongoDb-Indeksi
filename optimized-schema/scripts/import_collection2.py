import csv
from pathlib import Path
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from tqdm import tqdm

CONNECTION_STRING = "mongodb://localhost:27017/"
DATABASE_NAME = "fraud_detection"
CSV_DIR = Path("./csv_files")
CHUNK_SIZE = 5000  # Veličina paketa za Bulk operacije


def open_csv(path):
    f = open(path, newline="", encoding="utf-8")
    reader = csv.DictReader(f)
    return f, reader


def cast(value):
    if value == "" or value is None:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def main():
    client = MongoClient(CONNECTION_STRING)
    db = client[DATABASE_NAME]
    
    # Kolekcija koju pravimo po Šablonu proračunate vrednosti (Computed Pattern)
    summary_col = db["receivers_summary"]  

    f1, tx_reader = open_csv(CSV_DIR / "transactions.csv")
    f2, temp_reader = open_csv(CSV_DIR / "temporal_features.csv")
    f3, sr_reader = open_csv(CSV_DIR / "sender_receiver_features.csv")
    f4, behav_reader = open_csv(CSV_DIR / "sender_behavior_features.csv")
    f5, risk_reader = open_csv(CSV_DIR / "risk_features.csv")
    f6, net_reader = open_csv(CSV_DIR / "network_features.csv")
    f7, fraud_reader = open_csv(CSV_DIR / "fraud_scenario_labels.csv")
    f8, bal_reader = open_csv(CSV_DIR / "balance_features.csv")

    ops = []
    processed = 0

    total = sum(1 for _ in open(CSV_DIR / "transactions.csv")) - 1

    print("Pokrećem uvoz i inkrementalno računanje za receivers_summary...")

    with tqdm(total=total, desc="Computed Pattern Import", unit=" tx") as pbar:
        for tx, temp, sr, behav, risk, net, fraud, bal in zip(
            tx_reader, temp_reader, sr_reader, behav_reader,
            risk_reader, net_reader, fraud_reader, bal_reader
        ):
            assert tx["transaction_id"] == temp["transaction_id"] == sr["transaction_id"] == \
                   behav["transaction_id"] == risk["transaction_id"] == net["transaction_id"] == \
                   fraud["transaction_id"] == bal["transaction_id"], \
                   f"Redovi se ne poklapaju!"

            receiver_name = tx["nameDest"]
            sender_name = tx["nameOrig"]
            is_fraud_val = 1 if cast(tx["isFraud"]) == 1 else 0

            # --- ŠABLON PRORAČUNATE VREDNOSTI (Computed Pattern) ---
            # Umesto InsertOne, pravimo UpdateOne sa upsert=True.
            # Ako primalac ne postoji, Mongo ga pravi. Ako postoji, samo ažurira brojače.
            op = UpdateOne(
                {"_id": receiver_name},  # Ime primaoca je jedinstveni ključ dokumenta
                {
                    "$inc": {
                        "total_transactions": 1,        # Uvećaj ukupan broj transakcija za 1
                        "fraud_count": is_fraud_val     # Uvećaj broj prevara ako je isFraud=1
                    },
                    "$addToSet": {
                        "senders": sender_name          # Dodaj pošiljaoca u skup (izbacuje duplikate)
                    }
                },
                upsert=True
            )
            ops.append(op)

            # Slanje paketa u bazu radi brzine
            if len(ops) >= CHUNK_SIZE:
                try:
                    summary_col.bulk_write(ops, ordered=False)
                    processed += len(ops)
                except BulkWriteError as e:
                    print(f"Greška pri bulk upisu: {e.details}")
                ops = []

            pbar.update(1)

    # Upiši preostale operacije
    if ops:
        summary_col.bulk_write(ops, ordered=False)
        processed += len(ops)

    # --- ZAVRŠNI KORAK ŠABLONA: Proračun dužine niza (unique_senders_count) ---
    print("\nSvi podaci su uvezeni. Pokrećem finalno računanje unique_senders_count...")
    
    # Pošto imamo niz jedinstvenih pošiljalaca "senders", sada jednim brzim upitom 
    # dodajemo polje "unique_senders_count" koje predstavlja veličinu ($size) tog niza.
    summary_col.update_many(
        {},
        [
            {
                "$set": {
                    "unique_senders_count": {"$size": "$senders"}
                }
            }
        ]
    )

    # Zatvaranje fajlova i konekcije
    for f in [f1, f2, f3, f4, f5, f6, f7, f8]:
        f.close()
    client.close()

    print(f"\nGotovo!")
    print(f"Obrađeno transakcija: {processed:,}")
    print(f"Kreirano sumarnih profila primalaca u 'receivers_summary': {summary_col.count_documents({})}")


if __name__ == "__main__":
    main()