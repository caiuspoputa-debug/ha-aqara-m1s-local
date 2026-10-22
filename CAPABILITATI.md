# Acoperire stock 0.6.2

Adaptare la serviciile reale stock. Nu include o proba fizica noua
pentru fiecare copil sau fiecare sunet si nu pretinde suport universal.

| Functie descoperita | Implementare 0.6.2 | Dovada si limita |
|---|---|---|
| Inel RGB, on/off, luminozitate | basis_cli logic, OFF-COLOR-ON, ARGB procentual | Efecte vizuale probate in sesiunea 21.10; nu exista readback fizic validat |
| Sunete locale | Catalog numerotat doorbell/welcome/alarm, numai fisiere existente, once | Doorbell/1 auzit in laborator; celelalte mapari CLI nu sunt probate auditiv individual; ACK nu inseamna finalul WAV-ului |
| Volum sonerie | Valoare per cerere, limita implicita 5 | Niveluri 1..5 probate; fara volum global/mute/restaurare |
| Inventar Zigbee | Citire device.info, validare atomica, refresh 60 s | Prezenta nu inseamna online; doua absente valide consecutive permit curatarea entitatilor copilului |
| MQTT stock | Broker intern prin Telnet autorizat sau endpoint LAN existent explicit | CONNACK, SUBACK, PUBLISH, PINGRESP verificate pe hub; fara listener LAN nou |
| Curatare entitati | Optiune activata implicit; numai platforma si config entry proprii | Inventar/catalog valide obligatorii; erorile si unavailable nu sunt criterii de stergere |
| HomeKit si butoane vocale CH/US nemapate | Nu sunt create; vechile inregistrari sunt curatate | Prezenta unui proces/fisier nu devine un control functional inventat |
| Buton WXKG11LM | EventEntity si event bus pentru 1/2/16/17 | Rapoarte fizice observate; fara dependenta de raportul bateriei |
| Alte butoane simple/duble | Profil model-specific si canale separate | Mapari upstream pinned; nevalidate fizic pe .109 |
| TH, meteo, contact, inundatie | Sensor/BinarySensor dupa rapoarte | Mapari upstream, nevalidate fizic in acest build; fara procent fictiv baterie |
| Miscare si iluminare copil | Rapoarte 3.1.85 si 0.4.85 conform modelului | Fara clear temporizat inventat; vezi README |
| Prize, relee, intrerupatoare | Stare raportata, putere/energie unde sunt mapate; comenzi opt-in | Comenzile nu sunt probate fizic pe .109; nici ACK-ul nu confirma efectul |
| Modele necunoscute | Inventar, ultimul raport, raw read-only dezactivat implicit | Nu pretindem suport universal sau actuatoare generic functionale |
| ALS hub | Valoare bruta 0.3.85 | Nu o etichetam lux calibrat |
| Canal/versiune/pairing status | Numai resursele raportate | Nu modificam canalul, reteaua sau permit-join |
| Uptime/load/memorie/Wi-Fi/process presence | Snapshot fix read-only, la 60 s | Procese prezente/carrier nu dovedesc radio/audio sanatos |
| Pierdere conexiune | Reconnect MQTT, invalidare sesiune, fara replay comenzi | Inventar corupt/lipsa dezactiveaza procesarea/controlul copiilor |
| Diagnostice descarcabile | Allowlist de contoare/modele/status | Fara DID, host, parole, payload brut sau nume personale |
| Audio radio/streaming, grup sincronizat | Nu este implementat in profilul stock 0.6.0 | Proiectul media 0.37 ramane separat si neatins |
| Orice WAV arbitrar | Nu este promis | Catalogul numeric stock este expus; mesajele vocale CH/US si alte WAV-uri nu au o ruta nativa validata |
| Stop/mute global, restaurare lumina/audio | Neimplementat | Nu exista contract complet probat de oprire/readback/restaurare |
| Buton local event0, gesturi noi, pairing/delete/reset, transmisie putere | Numai documentat/amanat | Nu inventam coduri si nu pornim modificari de retea |
| Firmware/boot/UART/radio brut/controler universal | Exclus | Nicio scriere de firmware, capturare RF sau al doilea proprietar UART |

## Limite de resurse

JSON maxim 65536, pachet MQTT maxim 131072 octeti, inventar maxim 256
dispozitive, cache de inventar maxim 512 intrari inclusiv cele disparute.
Resurse necunoscute: maxim 16 per copil; descoperire maxim 4096 entitati
de camp pe intrare/sesiune. Payload-urile se valideaza inainte de utilizare.
Nu se genereaza entitati din identitati arbitrare primite numai prin MQTT.

## Diferenta fata de o integrare completa pentru orice dispozitiv

0.6.2 implementeaza contractele de control stock confirmate si o baza
model-specifica pentru dispozitivele copil. Nu transforma cercetarea
radio experimentala sau un tabel upstream in functionalitate certificata
pentru toate dispozitivele. Controlul fizic al fiecarui model ramas trebuie
confirmat separat, inainte de folosirea in automatizari importante.
