# Aqara M1S Local 0.6.2 - STOCK LAB TEST

Pachet privat de test, construit din baza 0.5.9 si contractele/probele
.109 lab din 21-22 octombrie 2026. **Nu este o versiune instalata sau
validata fizic integral.** Livrarea este locala, fara publicare automata.
Arhiva REPOSITORY contine numai integrarea si documentatia necesara.
Arhiva SOURCE_TESTS_PRIVAT si cercetarea privata raman separate.

## Corectie HACS 0.6.1

HACS descarca fisierele integrarii din repository. Nu exista zip_release
sau filename in hacs.json, deci nu mai este obligatoriu un asset ZIP.
In repository trebuie sa existe hacs.json in radacina si folderul
custom_components/aqara_m1s_local cu toate fisierele din arhiva REPOSITORY.
Se foloseste un release/tag nou v0.6.2, nu se modifica tagurile vechi.
ZIP-ul REPOSITORY se extrage pentru a obtine fisierele de repository;
nu este un asset pe care HACS trebuie sa il descarce.
Detalii: HACS_FIX.md.

## Ce face

- Controleaza inelul prin serviciul logic stock Aqara: OFF, culoare ARGB,
  ON. Nu foloseste vechiul RGB direct care ocolea cache-ul logic stock.
- Descopera catalogul stock de pe fiecare hub si expune soneriile 1..4,
  welcome 1..10 si alarm 1..9 numai daca fisierele corespunzatoare exista.
  Fiecare comanda cere o singura redare locala, cu volum per cerere.
  Numai doorbell/1 are si confirmare auditiva in laborator; celelalte
  mapari folosesc familiile CLI stock si nu sunt probate fizic individual.
  Nu transfera WAV-ul la Home Assistant si nu porneste FFmpeg sau Aplay.
- Citeste inventarul stock, creeaza dispozitive copil distincte si expune
  rapoarte de temperatura, umiditate, presiune, tensiune baterie, contact,
  inundatie, miscare, iluminare, putere si energie, potrivit modelului.
- Expune evenimente single, double, hold, release; un raport de
  buton nu trebuie sa contina si tensiunea bateriei.
- Ofera comenzi pentru prize/relee/intrerupatoare mapate, experimental:
  implicit dezactivate in optiuni **si** in registrul entitatilor.
- Include inventar prezent, ultimul raport primit, conexiune MQTT,
  resurse gateway raportate si diagnostice sistem doar-citire.
- Foloseste brokerul intern 127.0.0.1:1883 prin accesul Telnet deja
  autorizat. Nu presupune ca un hub stock are port LAN MQTT 1884.
  Comenzile MQTT sunt transportate in inregistrari ASCII codate pentru
  a evita alterarea octetilor de control in terminalul stock.
- Elimina implicit entitatile obsolete ale acestei intrari, inclusiv
  HomeKit Process si butoanele vechi fara mapare stock. Nu sterge
  entitati doar pentru ca sunt unavailable. Nu atinge alte integrari.
- Modelele necunoscute apar in inventar. Resursele lor raportate sunt
  senzori raw, doar-citire, implicit dezactivati, nu comenzi inventate.

Detaliile si limitele sunt in CAPABILITATI.md; provenienta detaliata
si testele sunt in pachetul privat de verificare.

## Ce NU pretinde

Un ACK inseamna acceptare RPC, nu efect fizic sau sfarsit de redare.
O intrare in inventar, un ping MQTT sau un proces prezent nu inseamna
dispozitiv Zigbee online ori radio sanatos. radio_ready ramane
not_proven. Starea inelului este ultima cerere acceptata, cu
assumed_state si indicator de cache stale; nu este citire hardware.

Nu include pairing/reset, butonul fizic local, mute/stop audio generic,
volum hardware global, restaurare automata a luminii, capturi RF,
UART/Spinel/ZoH sau un coordonator universal. Nu preia UART-ul stock.
Nu instaleaza executabile, servicii, tuneluri ori pornire automata pe hub.
Nu modifica firmware, boot, Zigbee, reteaua sau datele de autentificare.

## Atentie la migrarea de la 0.5.9

Aceasta este adaptarea **stock**, nu extensia integrarii media sincronizate
aqara_m1s_zigbee_router din seria 0.37. Aceea nu este modificata.

Vechiul radio FFmpeg/Aplay, redarea arbitrara WAV prin transfer dus-intors,
serviciile play_url si run_command nu sunt preluate in profilul stock:
nu au un contract nativ validat pentru proprietatea audio stock.
Sunt mapate numai scenele numerotate din familiile stock descoperite;
alte WAV-uri, inclusiv mesajele vocale CH/US, nu pornesc o ruta ascunsa.
Inelul, selectia si volumul cererii native pastreaza identificatorii
de entitate de baza. Butoanele vechi pentru scene mapate isi pastreaza
unique_id-ul, dar folosesc acum redarea nativa. Curatarea automata,
activata implicit, elimina doar inregistrarile obsolete ale acestei
intrari, dupa citiri valide. Copiii disparuti necesita doua inventare
valide consecutive; erorile intrerup numaratoarea. Datele istorice nu
sunt purjate si dispozitivele nu sunt sterse din reteaua Zigbee.
Automatizarile care refera entitati eliminate trebuie revizuite.

## Instalare manuala, doar cand este ceruta

Necesita Home Assistant Core **2026.10.1 sau mai nou**. Foloseste
probatio, biblioteca deja inclusa in acea versiune HA.

Hubul trebuie sa aiba deja acces Telnet autorizat si brokerul stock
intern functional. Integrarea nu activeaza si nu configureaza acest acces.
Nu creeaza un listener LAN sau un serviciu persistent. Codarea ASCII
nu este criptare: utilizati doar reteaua locala de incredere, fara
expunerea Telnet/MQTT la internet. Modul direct ramane disponibil doar
pentru un endpoint MQTT LAN deja existent.

1. Faceti un backup Home Assistant si al folderului integrarii existente.
2. Inlocuiti complet numai config/custom_components/aqara_m1s_local
   cu folderul omonim din arhiva; nu suprapuneti peste fisiere vechi.
   Nu inlocuiti aqara_m1s_zigbee_router.
3. Reporniti Home Assistant cand acceptati intreruperea automatizarilor.
4. Configurati Aqara M1S Local cu adresa hubului de laborator, portul
   Telnet existent si utilizatorul/parola. MQTT foloseste implicit Telnet;
   campul port MQTT LAN conteaza numai daca alegeti ulterior modul direct.
   Nicio parola sau adresa concreta nu este inclusa in arhiva.
5. La prima pornire nu sunt trimise comenzi de lumina/sunet/catre copii.
   Se citesc numai inventarul si diagnosticele, apoi se asculta MQTT.

Nu schimbati firmware-ul si nu conectati un al doilea client UART
ZHA/Zigbee2MQTT/ZoH la coordonatorul folosit de mzigbee_agent.

## Optiuni

- Limita soneriei native: implicit 5%. In laborator au fost verificate
  fizic numai nivelurile 1..5. O limita mai mare, pana la 100, este opt-in
  si poate produce sunet puternic; nu este validata fizic in acest build.
- Control copii: implicit oprit. Necesita si activarea manuala a entitatii
  switch, model mapat, inventar valid si un raport in sesiunea curenta.
- Vechime maxima raport copil: implicit 86400 secunde, configurabil
  60..604800. Nu reprezinta polling sau dovada ca un dispozitiv doarme.
- Elimina automat entitatile vechi: implicit activat; poate fi dezactivat
  in optiunile intrarii inainte de o reincarcare ulterioara.
- Conexiune MQTT: implicit telnet, catre brokerul intern existent.
  direct foloseste portul MQTT LAN configurat, fara sa il creeze.

Modificarile de optiuni reincarca numai intrarea integrarii; nu repornesc HA.
Cursorul de volum seteaza **urmatoarea cerere de sonerie**, nu placa audio
globala, nu radioul si nu confirma o valoare stock citita.

## Servicii si evenimente

Serviciul aqara_m1s_local.play_sound:

~~~yaml
action: aqara_m1s_local.play_sound
data:
  entry_id: IDUL_INTRARII_CONFIGURATE
  sound_id: 1
  sound_type: doorbell
  volume: 2
~~~

entry_id sau host trebuie sa identifice exact un hub configurat;
daca exista un singur hub, selectorul poate lipsi. Nu se creeaza conexiuni
catre gazde neconfigurate din datele unui serviciu.
Pentru compatibilitate, sound_path accepta o cale exacta din catalogul
stock mapat si descoperit pe acel hub. Nu accepta cai arbitrare.
aqara_m1s_local.refresh_inventory reciteste inventarul, fara pairing.

Butoanele copil au entitati event, cu event_type single/double/hold/release,
si eveniment HA aqara_m1s_local_action cu entry_id, device_id,
channel, action. Nu se publica aceste actiuni sub zigbee2mqtt/...
Codurile de gest nevalidate nu sunt ghicite.

## Interpretarea starilor

- Present in stock inventory: numai prezenta in fisierul stock.
- Last stock report received: momentul receptionarii in sesiunea HA,
  nu timestamp de la senzor si nu confirmarea unei comenzi.
- Senzorii copil devin disponibili dupa raportul lor in sesiunea MQTT
  curenta; dupa reconectare, vechile valori nu sunt declarate live.
- Mesajele retained nu declanseaza actiuni. Duplicatele identificabile
  prin packet ID/DUP sau zseq sunt filtrate; doua single-uri legitime
  fara identificator nu sunt suprimate fiindca au acelasi continut.
- Switch-urile nu isi schimba optimist starea din propria comanda.
  sent_unconfirmed/outcome_unknown nu reprezinta livrare radio.
- Miscarea reflecta rapoartele stock 0/1. Nu inventam un mesaj de clear
  sau un timeout de ocupare; modelele care raporteaza numai 1 necesita
  validarea separata a politicii de reset, nu o presupunere ascunsa.
- Datele gateway vechi nu devin actuale doar fiindca a sosit alt atribut.

## Verificare

Testele din pachetul privat sunt sintetice: protocoale, framing, inventar, evenimente, rutare
multi-hub, lifecycle si broker MQTT local pe 127.0.0.1. Adaptorul HA este
testat cu dubluri API, nu cu o instalare completa Home Assistant.
Pe hubul stock a fost verificata conectarea si abonarea la brokerul
intern, receptia mesajelor si raspunsul la keepalive, fara comenzi
catre dispozitive. Nu s-a facut o proba noua de apasare sau de audio
pentru toate fisierele. Nu este o instalare/testare completa in HA.
TEST_RESULTS.json si BUILD_MANIFEST.json precizeaza acoperirea.

Originalul 0.5.9 si arhiva privata a cercetarii sunt pastrate separat.
Pentru revenire, restaurati folderul si configuratia HA salvate anterior.
