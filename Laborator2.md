# Laboratorul 2: Cuantifică citirile Dashboard-ului

## Personal Investment Dashboard

### Context

În Laboratorul 1 am definit un Dashboard care ajută utilizatorul să urmărească acțiuni și informații de piață. În acest laborator transformăm acea idee în valori măsurabile.

Prima versiune are următoarele citiri:

- Overview;
- Filter;
- Stock price;
- History;
- Watchlist;
- Search.

Utilizatorul este autentificat. Market Data Provider este sistemul extern care furnizează datele de piață.

Pentru acest laborator folosesc următoarele decizii:

- piața acceptată: SUA;
- burse: Nasdaq și NYSE;
- instrumente: common stocks și ADR-uri;
- ETF-urile, fondurile, preferred stocks și crypto nu intră în prima versiune;
- instrumentele delistate rămân disponibile pentru consultarea istoricului, dar nu mai pot fi adăugate ca instrumente active în Watchlist;
- istoricul de preț este păstrat la interval de 1 minut timp de un an.

---

# 1. Cerințe de calitate

## 1.1 Latența citirilor

Clientul spune că prețurile trebuie să pară imediate și că majoritatea citirilor trebuie să se încheie în cel mult 2 secunde în perioadele aglomerate.

Pentru a putea măsura acest lucru, definesc timpul de răspuns de la momentul în care Dashboard-ul primește cererea până când răspunsul complet părăsește limita Dashboard-ului.

Țintele sunt:

| Citire | Măsură | Țintă | Condiție |
|---|---|---|---|
| Stock price | latență p95 | ≤ 1 secundă | în timpul orelor de tranzacționare, inclusiv în perioade aglomerate |
| Toate citirile corecte | latență p95 | ≤ 2 secunde | în regim normal și la deschiderea pieței |

`p95 ≤ 2 secunde` înseamnă că cel puțin 95% dintre citirile corecte trebuie să se termine în maximum 2 secunde.

O citire care trece de 2 secunde reprezintă o încălcare a țintei de latență, chiar dacă rezultatul final este corect.

Un răspuns `Unavailable` poate fi livrat rapid și poate respecta ținta de latență. Acest lucru nu înseamnă însă că cerința privind actualitatea datelor este respectată.

---

## 1.2 Disponibilitate

Pentru prima versiune aleg o disponibilitate de **99%**, adică „doi de 9”, atât în trading hours, cât și în restul zilei.

Dashboard-ul este considerat disponibil dacă utilizatorul autentificat poate efectua citirile suportate și primește un rezultat conform contractului produsului. Un rezultat explicit `Unavailable` nu este ascuns sau transformat într-o valoare falsă.

Orele normale de tranzacționare pentru NYSE și Nasdaq sunt 09:30–16:00 Eastern Time, adică 6,5 ore pe zi de tranzacționare.

Pentru calcul folosesc intervalul de 30 de zile **1–30 septembrie 2026**. În această perioadă sunt 21 de zile de tranzacționare, deoarece 7 septembrie 2026 este Labor Day și piața este închisă.

### Trading hours

21 zile × 6,5 ore = **136,5 ore**

La disponibilitate de 99%:

136,5 h × 1% = **1,365 ore indisponibilitate**

adică:

**81,9 minute în 30 de zile**

### Restul zilei

30 zile × 24 h = 720 h

720 − 136,5 = **583,5 ore**

583,5 h × 1% = **5,835 ore indisponibilitate**

adică:

**350,1 minute în 30 de zile**

| Interval | Disponibilitate | Timp măsurat în 30 zile | Buget maxim de indisponibilitate |
|---|---:|---:|---:|
| Trading hours | 99% | 136,5 h | 81,9 min |
| Restul zilei | 99% | 583,5 h | 350,1 min |

Am ales aceeași țintă de 99% pentru ambele perioade deoarece prima versiune este un produs informativ. Dashboard-ul nu execută tranzacții și nu trebuie tratat ca un sistem de trading critic.

Totuși, cele două intervale se măsoară separat. O indisponibilitate în timpul pieței deschise este mai vizibilă pentru utilizator chiar dacă ținta procentuală este aceeași.

---

## 1.3 Consistența și actualitatea Stock price

Clientul spune că întârzierea normală a furnizorului este de aproximativ 15 minute.

Pentru Dashboard folosesc următoarea regulă:

| Vechimea prețului | Rezultat |
|---|---|
| ≤ 15 minute | preț acceptat; se afișează timpul furnizorului / întârzierea |
| > 15 și ≤ 30 minute | `Stale` – poate fi afișat ca informație veche, dar nu ca preț curent |
| > 30 minute sau fără preț valid | `Unavailable` |

Ținta este ca **100% dintre Stock price results să fie clasificate conform timestamp-ului furnizorului**.

Dashboard-ul nu înlocuiește niciodată un preț lipsă cu zero.

Astfel, valoarea `0 USD` poate exista doar dacă acesta este un rezultat real al datelor, nu ca substitut pentru lipsa informației.

---

## 1.4 Consistența Watchlist-ului

Pentru Watchlist folosesc regula **read-your-writes**.

După ce Dashboard-ul confirmă că un utilizator a adăugat sau a eliminat un simbol, următoarea citire a Watchlist-ului făcută de același utilizator trebuie să reflecte modificarea.

Ținta este:

**100% din următoarele citiri ale aceluiași utilizator trebuie să vadă modificarea deja confirmată.**

În plus, un utilizator poate citi sau modifica doar propriul Watchlist.

---

## 1.5 Debit și capacitate

Ținta de debit va fi stabilită din calculele RPS.

Pentru cel mai mare nivel analizat, sistemul trebuie să poată susține ținta calculată pentru **30.000 de utilizatori concurenți la deschiderea pieței**, inclusiv marja de capacitate de 10%.

Rezultatul calculat mai jos este:

**10.296 RPS**

Ținta de capacitate nu înlocuiește ținta de latență. Dashboard-ul trebuie să poată procesa acest trafic păstrând în același timp valorile de latență stabilite mai sus.

---

# 2. Estimări RPS în regim stabil

Formula folosită este:

```text
RPS = utilizatori concurenți × pondere participanți × acțiuni per utilizator / secunde
```

Comportamentul primit de la client este păstrat fără modificări.

## Overview

70% dintre utilizatori fac refresh o dată la 30 secunde.

- 300 × 0,70 / 30 = **7 RPS**
- 3.000 × 0,70 / 30 = **70 RPS**
- 30.000 × 0,70 / 30 = **700 RPS**

## Filter

50% dintre utilizatori schimbă filtrul de 3 ori pe minut.

- 300 × 0,50 × 3 / 60 = **7,5 RPS**
- 3.000 × 0,50 × 3 / 60 = **75 RPS**
- 30.000 × 0,50 × 3 / 60 = **750 RPS**

## Stock price

20% dintre utilizatori solicită un preț o dată pe secundă.

- 300 × 0,20 × 1 = **60 RPS**
- 3.000 × 0,20 × 1 = **600 RPS**
- 30.000 × 0,20 × 1 = **6.000 RPS**

## History

20% dintre utilizatori solicită istoricul o dată la 5 minute.

5 minute = 300 secunde.

- 300 × 0,20 / 300 = **0,2 RPS**
- 3.000 × 0,20 / 300 = **2 RPS**
- 30.000 × 0,20 / 300 = **20 RPS**

## Watchlist

60% dintre utilizatori fac refresh o dată pe minut.

- 300 × 0,60 / 60 = **3 RPS**
- 3.000 × 0,60 / 60 = **30 RPS**
- 30.000 × 0,60 / 60 = **300 RPS**

## Search

10% dintre utilizatori caută de 3 ori pe minut.

- 300 × 0,10 × 3 / 60 = **1,5 RPS**
- 3.000 × 0,10 × 3 / 60 = **15 RPS**
- 30.000 × 0,10 × 3 / 60 = **150 RPS**

## Rezultat

| Citire | 300 utilizatori | 3.000 utilizatori | 30.000 utilizatori |
|---|---:|---:|---:|
| Overview | 7 RPS | 70 RPS | 700 RPS |
| Filter | 7,5 RPS | 75 RPS | 750 RPS |
| Stock price | 60 RPS | 600 RPS | 6.000 RPS |
| History | 0,2 RPS | 2 RPS | 20 RPS |
| Watchlist | 3 RPS | 30 RPS | 300 RPS |
| Search | 1,5 RPS | 15 RPS | 150 RPS |
| **Total în regim stabil** | **79,2 RPS** | **792 RPS** | **7.920 RPS** |

Se observă că Stock price generează de departe cel mai mult trafic. Pentru 30.000 de utilizatori, 6.000 din cele 7.920 RPS provin doar din această citire.

---

# 3. Estimări RPS la deschiderea pieței

La deschiderea pieței apare trafic suplimentar.

30% dintre utilizatori fac refresh la Overview într-un interval de 10 secunde.

### Refresh suplimentar Overview

Pentru 300 utilizatori:

300 × 0,30 / 10 = **9 RPS**

Pentru 3.000:

3.000 × 0,30 / 10 = **90 RPS**

Pentru 30.000:

30.000 × 0,30 / 10 = **900 RPS**

Din acest grup, 60% fac refresh și la Watchlist.

### Refresh suplimentar Watchlist

Pentru 300 utilizatori:

300 × 0,30 × 0,60 / 10 = **5,4 RPS**

Pentru 3.000:

3.000 × 0,30 × 0,60 / 10 = **54 RPS**

Pentru 30.000:

30.000 × 0,30 × 0,60 / 10 = **540 RPS**

Traficul suplimentar se adaugă la traficul stabil. Nu înlocuiește și nu dublează calculele deja făcute.

| Calcul la deschiderea pieței | 300 utilizatori | 3.000 utilizatori | 30.000 utilizatori |
|---|---:|---:|---:|
| Trafic stabil | 79,2 | 792 | 7.920 |
| Refresh suplimentar Overview | 9 | 90 | 900 |
| Refresh suplimentar Watchlist | 5,4 | 54 | 540 |
| **Subtotal** | **93,6** | **936** | **9.360** |
| Marjă de capacitate 10% | 9,36 | 93,6 | 936 |
| Total cu marjă, înainte de rotunjire | 102,96 | 1.029,6 | 10.296 |
| **Țintă finală rotunjită în sus** | **103 RPS** | **1.030 RPS** | **10.296 RPS** |

Rotunjirea este aplicată doar rezultatului final.

Pentru nivelul maxim al laboratorului, Dashboard-ul trebuie deci dimensionat pentru o țintă de cel puțin:

**10.296 RPS la deschiderea pieței.**

---

# 4. Estimarea stocării

## 4.1 Ce înseamnă „Stock” pentru acest Dashboard

Investor.gov definește stock-ul ca un instrument care reprezintă o poziție de proprietate într-o companie. Common stock oferă în mod obișnuit drept de vot și posibilitatea de a primi dividende.

Un ADR reprezintă acțiuni ale unei companii din afara SUA printr-un instrument tranzacționat pe piața americană. Un ADR poate reprezenta o acțiune, mai multe acțiuni sau o fracțiune dintr-o acțiune străină.

Pentru acest Dashboard, termenul **Stock** înseamnă:

**un common stock sau un ADR listat pe Nasdaq sau NYSE.**

Nu includ:

- preferred stock;
- ETF;
- mutual fund;
- bond;
- option;
- futures;
- crypto;
- alte instrumente care nu sunt common stock sau ADR.

Motivul este simplu: prima versiune trebuie să rămână suficient de mică pentru a putea defini clar Search, Filter, Stock price și History.

---

## 4.2 Bursele acceptate

Prima versiune acceptă:

**Nasdaq și New York Stock Exchange (NYSE).**

Nu includ NYSE American sau alte piețe americane în această etapă.

La 30 septembrie 2026, lista StockAnalysis arată aproximativ:

- **3.427 stocks pe Nasdaq**;
- **1.957 stocks pe NYSE**.

Pentru estimarea de capacitate folosesc:

3.427 + 1.957 = **5.384 Stocks**

Aceasta este o estimare de planificare, nu o valoare permanentă. Numărul instrumentelor listate se modifică în timp.

În implementarea reală, lista furnizorului trebuie filtrată după tipul instrumentului. Nasdaq publică directoare de simboluri actualizate pe parcursul zilei și identifică inclusiv bursa, numele instrumentului și dacă un instrument este ETF.

---

## 4.3 Instrumente inactive și delistate

Un instrument care devine inactiv sau este delistat nu dispare imediat din Dashboard.

Îl păstrăm pentru:

- istoricul prețului;
- rezultatele Search pentru date istorice;
- explicarea intrărilor vechi din Watchlist.

Totuși, instrumentul nu mai poate fi adăugat ca Stock activ într-un Watchlist nou.

Datele sale de referință sunt păstrate, iar price history rămâne disponibil conform perioadei de retenție.

---

## 4.4 Date sincronizate

Dashboard-ul nu are nevoie de toate câmpurile oferite de Market Data Provider. Păstrează doar informația necesară funcțiilor din produs.

### Date de referință Stock

Pentru Search și Filter păstrăm:

`symbol`

`company_name`

`exchange`

`instrument_type`

`currency`

`country`

`status`

Aceste informații permit căutarea după simbol sau companie și filtrarea după bursă, tip și status.

### Latest price

Pentru Stock price și Overview păstrăm:

`symbol`

`latest_price`

`previous_close`

`provider_timestamp`

`price_state`

`previous_close` permite calcularea schimbării zilnice fără a introduce un set separat de date.

### Price history

Pentru History păstrăm:

`symbol`

`timestamp`

`price`

Am ales intervalul de **1 minut** în timpul orelor normale de tranzacționare.

Nasdaq folosește, de asemenea, date intraday la intervale de un minut pentru graficele sale de piață, ceea ce arată că această granularitate este rezonabilă pentru urmărirea mișcării intraday.

Perioada de retenție aleasă este:

**1 an**

O zi normală de tranzacționare are 6,5 ore:

6,5 × 60 = **390 puncte per Stock pe zi**

Pentru estimarea anuală folosesc **252 zile de tranzacționare** ca presupunere de dimensionare.

---

## 4.5 Dimensiunea unei înregistrări

Pentru calcul folosesc înregistrări simple serializate.

Exemplu pentru Stock reference:

```text
{"symbol":"AAPL","name":"Apple Inc.","exchange":"NASDAQ",
"type":"COMMON_STOCK","currency":"USD","country":"US","status":"ACTIVE"}
```

Un asemenea exemplu are aproximativ 140 bytes. Deoarece unele nume și simboluri sunt mai lungi, folosesc o medie conservatoare de:

**160 bytes / Stock reference record**

Pentru Latest price folosesc:

**120 bytes / record**

Pentru History:

**80 bytes / record**

Valorile includ o mică rezervă pentru variația lungimii câmpurilor.

---

## 4.6 Calculul stocării

### Stock reference

Număr înregistrări:

5.384

Calcul:

5.384 × 160 bytes = **861.440 bytes**

≈ **0,82 MiB**

### Latest prices

Un singur latest price pentru fiecare Stock:

5.384 × 120 bytes = **646.080 bytes**

≈ **0,62 MiB**

### Price history pe zi

5.384 Stocks × 390 puncte =

**2.099.760 history records / zi**

2.099.760 × 80 bytes =

**167.980.800 bytes / zi**

≈ **160,20 MiB / zi de tranzacționare**

### Price history pentru un an

Formula cerută este:

```text
history record count =
supported Stocks × history points per Stock per day × retained days
```

Prin urmare:

5.384 × 390 × 252 =

**529.139.520 history records**

Stocarea brută:

529.139.520 × 80 bytes =

**42.331.161.600 bytes**

≈ **39,42 GiB**

## Tabel final

| Set de date | Decizie și retenție | Număr înregistrări | Bytes / înregistrare | Stocare brută |
|---|---|---:|---:|---:|
| Stock reference | păstrat cât timp instrumentul există; identitatea delisted se păstrează | 5.384 | 160 B | 0,82 MiB |
| Latest prices | o valoare curentă per Stock | 5.384 | 120 B | 0,62 MiB |
| Price history | 1 minut, 1 an | 529.139.520 | 80 B | 39,42 GiB |
| Alte date separate | nu sunt necesare în V1 | 0 | — | 0 |
| **Total după un an** | | | | **≈ 39,43 GiB** |

Stocarea inițială pentru reference data + latest prices este de aproximativ:

**1,44 MiB**

Creșterea într-o zi normală de tranzacționare este de aproximativ:

**160,20 MiB**

După un an de history:

**aproximativ 39,43 GiB de raw market data**

Estimarea nu include indexuri, copii de siguranță, replicare sau overhead intern. Laboratorul cere raw storage, deci acestea nu sunt adăugate.

---

# 5. Posibile blocaje

Valorile calculate nu demonstrează că există un blocaj. Ele arată unde merită făcute măsurători.

| Calitate | Posibil blocaj | Dovezi din laborator | Efect posibil | Ce trebuie măsurat |
|---|---|---|---|---|
| Latență | calea de citire Stock price | Stock price ajunge la 6.000 RPS la nivelul de 30.000 utilizatori | p95 poate trece de 1–2 secunde | p50, p95 și p99 pentru Stock price la creșterea RPS |
| Consistență | întârzierea dintre modificarea Watchlist și următoarea citire | cerința este read-your-writes pentru același utilizator | simbol adăugat sau șters poate apărea incorect la următoarea citire | timpul dintre confirmarea modificării și momentul când aceasta devine vizibilă |
| Debit | burst-ul de la deschiderea pieței | ținta crește de la 7.920 la 10.296 RPS | cererile se pot acumula și latența crește | RPS maxim sustenabil și latența la 8k, 9k, 10k și peste 10.296 RPS |
| Disponibilitate | o problemă pe o cale comună tuturor citirilor | toate cele șase fluxuri trec prin Dashboard, iar vârful ajunge la 10.296 RPS | mai multe funcții pot deveni simultan indisponibile | procentul de citiri utilizabile separat în trading hours și în restul zilei |

### Observație despre Market Data Provider

Market Data Provider este și el un risc important, dar trebuie separat de uptime-ul Dashboard-ului.

Dacă furnizorul nu oferă un preț nou, Dashboard-ul poate continua să funcționeze și să arate `Stale` sau `Unavailable`.

Problema este atunci actualitatea datelor, nu neapărat disponibilitatea întregului Dashboard.

Trebuie măsurate separat:

- vârsta datelor primite;
- procentul de Stocks fără preț utilizabil;
- timpul de la timestamp-ul furnizorului până la disponibilitatea datelor în Dashboard.

---

# Concluzie

Pentru prima versiune am limitat produsul la common stocks și ADR-uri de pe Nasdaq și NYSE. Estimarea de lucru este de aproximativ **5.384 Stocks**.

În regim stabil, nivelul maxim de 30.000 utilizatori generează:

**7.920 RPS**

La deschiderea pieței și cu marja de 10%, ținta devine:

**10.296 RPS**

Cea mai solicitată funcție este Stock price, cu aproximativ **6.000 RPS** în regim stabil.

Pentru datele de piață, istoricul de un minut este partea care ocupă aproape tot spațiul. Estimarea brută pentru un an este de aproximativ:

**39,43 GiB**

Țintele principale ale primei versiuni sunt:

- p95 ≤ 1 secundă pentru Stock price;
- p95 ≤ 2 secunde pentru restul citirilor corecte;
- 99% availability în trading hours;
- 99% availability în restul zilei;
- prețurile de până la 15 minute sunt acceptate ca date întârziate;
- după 15 minute sunt marcate `Stale`;
- după 30 minute fără un rezultat nou, Stock price devine `Unavailable`;
- următoarea citire Watchlist a aceluiași utilizator trebuie să vadă orice modificare deja confirmată.

Aceste valori oferă punctul de plecare pentru testarea capacității. Un calcul de RPS arată unde poate apărea presiune, dar un blocaj poate fi confirmat doar prin măsurători.

# Surse

**Investor.gov — Stocks / Common Stock.** Folosit pentru definiția Stock și diferența dintre common și preferred stock.

**Investor.gov — American Depositary Receipts.** Folosit pentru definirea ADR-urilor.

**StockAnalysis — Nasdaq Stocks.** 3.427 stocks observate la 30.09.2026.

**StockAnalysis — NYSE Stocks.** 1.957 stocks observate la 30.09.2026.

**Nasdaq Trader — Symbol Directory.** Folosit pentru structura și clasificarea instrumentelor listate.

**NYSE — Trading Hours and Calendar.** Folosit pentru programul 09:30–16:00 ET și calendarul bursier.

**Nasdaq — Market Activity.** Folosit pentru programul pieței și intervalele intraday de un minut.