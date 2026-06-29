import csv
from pathlib import Path
from pymongo import MongoClient, InsertOne
from pymongo.errors import BulkWriteError
from tqdm import tqdm

CONNECTION_STRING = "mongodb://localhost:27017/"
DATABASE_NAME = "fraud_detection"
CSV_DIR = Path("./csv_files")
CHUNK_SIZE = 5000


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


def build_doc(tx, temp, sr, behav, net, bal, risk, fraud):
    tid = tx["transaction_id"]

    # --- ŠABLON ATRIBUTA (Attribute Pattern) ---
    # Mapiramo nazive flegova iz CSV-a i proveravamo koji su aktivni (imaju vrednost 1)
    flag_mappings = {
        "high_amount_flag": "high_amount",
        "high_velocity_flag": "high_velocity",
        "new_receiver_flag": "new_receiver",
        "many_to_one_receiver_flag": "many_to_one",
        "suspicious_cashout_flag": "suspicious_cashout",
        "large_transfer_flag": "large_transfer"
    }
    
    active_flags = []
    for csv_key, clean_name in flag_mappings.items():
        if cast(risk.get(csv_key)) == 1:
            active_flags.append(clean_name)
    # -------------------------------------------

    doc = {
        "_id": tid,
        "type": tx["type"],
        "amount": cast(tx["amount"]),
        "sender": {
            "nameOrig": tx["nameOrig"],
            "oldbalanceOrg": cast(tx["oldbalanceOrg"]),
            "newbalanceOrig": cast(tx["newbalanceOrig"]),
            "behavior": {
                "sender_tx_count_total_so_far": cast(behav["sender_tx_count_total_so_far"]),
                "sender_tx_count_1h": cast(behav["sender_tx_count_1h"]),
                "sender_tx_count_24h": cast(behav["sender_tx_count_24h"]),
                "sender_total_amount_24h": cast(behav["sender_total_amount_24h"]),
                "sender_avg_amount_24h": cast(behav["sender_avg_amount_24h"]),
                "amount_to_sender_avg_ratio": cast(behav["amount_to_sender_avg_ratio"]),
                "sender_unique_receivers_24h": cast(behav["sender_unique_receivers_24h"]),
            },
            "network": {
                "sender_out_degree_so_far": cast(net["sender_out_degree_so_far"]),
            }
        },
        "receiver": {
            "nameDest": tx["nameDest"],
            "oldbalanceDest": cast(tx["oldbalanceDest"]),
            "newbalanceDest": cast(tx["newbalanceDest"]),
            "is_merchant_dest": cast(tx["is_merchant_dest"]),
            "is_customer_dest": cast(tx["is_customer_dest"]),
            "network": {
                "receiver_in_degree_so_far": cast(net["receiver_in_degree_so_far"]),
                "receiver_tx_count_so_far": cast(net["receiver_tx_count_so_far"]),
                "receiver_received_amount_so_far": cast(net["receiver_received_amount_so_far"]),
            }
        },
        "sender_receiver_relation": {
            "same_receiver_count_24h": cast(sr["same_receiver_count_24h"]),
            "sender_receiver_tx_count_so_far": cast(sr["sender_receiver_tx_count_so_far"]),
            "is_new_receiver_for_sender": cast(sr["is_new_receiver_for_sender"]),
            "sender_receiver_network_count_so_far": cast(net["sender_receiver_network_count_so_far"]),
        },
        "temporal": {
            "day": cast(temp["day"]),
            "hour": cast(temp["hour"]),
            "period_of_day": temp["period_of_day"],
            "is_night": cast(temp["is_night"]),
            "is_first_week": cast(temp["is_first_week"]),
            "is_first_half_month": cast(temp["is_first_half_month"]),
        },
        "balance_analysis": {
            "balance_diff_orig": cast(bal["balance_diff_orig"]),
            "balance_diff_dest": cast(bal["balance_diff_dest"]),
            "expected_newbalanceOrig": cast(bal["expected_newbalanceOrig"]),
            "expected_newbalanceDest": cast(bal["expected_newbalanceDest"]),
            "orig_balance_error": cast(bal["orig_balance_error"]),
            "dest_balance_error": cast(bal["dest_balance_error"]),
            "is_sender_balance_zero_after": cast(bal["is_sender_balance_zero_after"]),
            "is_dest_balance_zero_before": cast(bal["is_dest_balance_zero_before"]),
            "is_dest_balance_missing": cast(bal["is_dest_balance_missing"]),
            "leakage_warning": cast(bal["leakage_warning"]),
        },
        "risk": {
            "risk_score_rule_based": cast(risk["risk_score_rule_based"]),
            "risk_level": risk["risk_level"],
            "risk_reason_count": cast(risk["risk_reason_count"]),
            "active_flags": active_flags  # <-- Novi niz koji menja stari objekat sa 6 flegova
        },
        "fraud_label": {
            "isFraud": cast(tx["isFraud"]),
            "isFlaggedFraud": cast(tx["isFlaggedFraud"]),
            "fraud_scenario": fraud["fraud_scenario"],
            "scenario_group": fraud["scenario_group"],
            "is_original_fraud_label": cast(fraud["is_original_fraud_label"]),
            "is_engineered_scenario": cast(fraud["is_engineered_scenario"]),
        }
    }

    return doc


def main():
    client = MongoClient(CONNECTION_STRING)
    db = client[DATABASE_NAME]
    col = db["transactions_v2"]  

    f1, tx_reader    = open_csv(CSV_DIR / "transactions.csv")
    f2, temp_reader  = open_csv(CSV_DIR / "temporal_features.csv")
    f3, sr_reader    = open_csv(CSV_DIR / "sender_receiver_features.csv")
    f4, behav_reader = open_csv(CSV_DIR / "sender_behavior_features.csv")
    f5, risk_reader  = open_csv(CSV_DIR / "risk_features.csv")
    f6, net_reader   = open_csv(CSV_DIR / "network_features.csv")
    f7, fraud_reader = open_csv(CSV_DIR / "fraud_scenario_labels.csv")
    f8, bal_reader   = open_csv(CSV_DIR / "balance_features.csv")

    ops = []
    inserted = 0

    total = sum(1 for _ in open(CSV_DIR / "transactions.csv")) - 1

    with tqdm(total=total, desc="Import v2", unit=" tx") as pbar:
        for tx, temp, sr, behav, risk, net, fraud, bal in zip(
            tx_reader, temp_reader, sr_reader, behav_reader,
            risk_reader, net_reader, fraud_reader, bal_reader
        ):
            assert tx["transaction_id"] == temp["transaction_id"] == sr["transaction_id"] == \
                   behav["transaction_id"] == risk["transaction_id"] == net["transaction_id"] == \
                   fraud["transaction_id"] == bal["transaction_id"], \
                   f"Redovi se ne poklapaju! tx={tx['transaction_id']} temp={temp['transaction_id']}"

            doc = build_doc(tx, temp, sr, behav, net, bal, risk, fraud)
            ops.append(InsertOne(doc))

            if len(ops) >= CHUNK_SIZE:
                try:
                    col.bulk_write(ops, ordered=False)
                    inserted += len(ops)
                except BulkWriteError as e:
                    print(f"Greska pri insertu: {e.details}")
                ops = []

            pbar.update(1)

    if ops:
        col.bulk_write(ops, ordered=False)
        inserted += len(ops)

    for f in [f1, f2, f3, f4, f5, f6, f7, f8]:
        f.close()

    client.close()

    print(f"\nGotovo!")
    print(f"transactions_v2 ubaceno: {inserted:,}")


if __name__ == "__main__":
    main()