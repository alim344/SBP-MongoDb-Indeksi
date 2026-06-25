### Upiti

## Prvi upit

Koji tipovi transakcija ka novim primaocima (is_new_receiver_for_sender = 1) najčešće rezultuju prevarama i kako se prosečan risk_score razlikuje u zavisnosti od toga da li je primalac merchant ili customer?



```javascript
db.getCollection('transactions').aggregate([
  { 
    $match: { 
      "sender_receiver_relation.is_new_receiver_for_sender": 1 
    } 
  },

  {
    $lookup: {
      from: "risk_profiles",
      localField: "_id",
      foreignField: "_id",
      as: "risk_data"
    }
  },

  { 
    $unwind: "$risk_data" 
  },

  {
    $group: {
      _id: {
        type: "$type",
        is_merchant: "$receiver.is_merchant_dest"
      },
      total_transactions: { $sum: 1 },
      fraud_count: { $sum: "$risk_data.fraud_label.isFraud" },
      avg_risk_score: { $avg: "$risk_data.risk.risk_score_rule_based" }
    }
  },

  {
    $addFields: {
      fraud_rate_pct: {
        $round: [
          { $multiply: [{ $divide: ["$fraud_count", "$total_transactions"] }, 100] },
          2
        ]
      },
      avg_risk_score: { $round: ["$avg_risk_score", 2] },
      receiver_type: {
        $cond: { if: { $eq: ["$_id.is_merchant", 1] }, then: "merchant", else: "customer" }
      }
    }
  },

  { 
    $sort: { fraud_count: -1 } 
  },

  {
    $project: {
      _id: 0,
      transaction_type: "$_id.type",
      receiver_type: 1,
      total_transactions: 1,
      fraud_count: 1,
      fraud_rate_pct: 1,
      avg_risk_score: 1
    }
  }
], { allowDiskUse: true })

```

### Rezultat upita:

![](prviupit.png)

Vreme izvrsavanja: 14 min 26 sek

Transfer - customer je najopasniji tip. Ima 4097 prevara na 532000 transkacija. Cash-Out ima najveci broj prevara ali ima i najveci broj transakcija pa je fraud_rate mnogo nizi. Po avg_risk_score vidimo da sistem mnogo bolje detektuje TRANSFER prevare nego CASH_OUT prevare.