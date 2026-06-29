# Druga verzija šeme baza podataka

### Druga verzija šeme baze podataka sastoji se iz 2 stare kolekcije i 1 nove denormalizovane kolekcije koja je napravljena radi bržeg izvršavanja upita.


## Nova kolekcija transactions_v2

![](collection1.png)

Kolekcija sadrži podatke neophodne za izvršavanje osmišljenih upita bez lookupa i unwind funkcija. 

U okviru poddokumenta risk, umesto inicijalnog čuvanja 6 pojedinačnih flagova (gde bi se za svaku transakciju čuvale vrednosti 0 ili 1), primenjen je šablon atributa. Svi aktivni indikatori prevare preformulisani su u dinamički niz stringova pod nazivom active_flags.