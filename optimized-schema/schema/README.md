# Druga verzija šeme baza podataka

### Druga verzija šeme baze podataka sastoji se iz 2 stare kolekcije i 1 nove denormalizovane kolekcije koja je napravljena radi bržeg izvršavanja upita.


## Nova kolekcija transactions_v2

![](collection1.png)

Kolekcija sadrži podatke neophodne za izvršavanje osmišljenih upita bez lookupa i unwind funkcija. 