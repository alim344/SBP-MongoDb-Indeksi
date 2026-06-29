# Uputstvo za pokretanje ovog dela projekta



Pre pokretanja skripte import_v2.py sve isto kao i za inicijalni projekat, potrebno je obezbediti podatke sa Kaggle-a i instalirati potrebne Python biblioteke.

### Podaci
* **Izvor:** [Mobile Money Fraud Detection Dataset na Kaggle-u](https://www.kaggle.com/datasets/harrachimustapha/mobile-money-fraud-detection-dataset) (Veličina: 2.7GB, preko 6.3 miliona transakcija).
* **Uputstvo:** Sve preuzete `.csv` datoteke smestite u folder `csv_files/` unutar projekta.

### Potrebne Python biblioteke
Instalirajte biblioteke pokretanjem sledećih komandi u terminalu:

```bash
pip install pandas
pip install pymongo
pip install tqdm
```
1. Pokrenite skriptu `import_v2.py`. (podaci su vec ocisceni, samo ubacujemo u bazu)
2. Sačekajte da se podaci učitaju u MongoDB bazu.
3. Indeksi se dodaju nad novom kolekcijom 


```javascript
   
db.getCollection('transactions_v2').createIndex({ "sender_receiver_relation.is_new_receiver_for_sender": 1 })


db.getCollection('transactions_v2').createIndex({ "fraud_label.isFraud": 1, "risk.risk_level": 1 })


db.getCollection('transactions_v2').createIndex({ "balance_analysis.is_sender_balance_zero_after": 1, "type": 1 })
```
