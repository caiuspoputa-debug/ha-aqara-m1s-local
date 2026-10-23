# Aqara M1S Local 0.6.4 - STOCK LAB TEST

Integrare locala pentru M1S stock cu acces Telnet deja autorizat.
Nu este firmware si nu transforma hubul intr-un coordonator ZoH.
Pachet local de test: nu este instalat sau publicat automat.

## Corectii 0.6.4

Welcome 1..10 foloseau incorect indicii 1..10 ai bancii combinate stock,
care selecteaza alarme. Acum comenzile welcome folosesc 21..30. Numele,
caile WAV si identificatorii butoanelor existente raman neschimbate.
Contractul a fost verificat in aplicatia stock din backup, iar hashurile
aplicatiilor corespund celor citite de pe hubul autorizat. Nu am pornit
sunete sau alarme pe hub in aceasta verificare.

Catalogul audio/limbilor, ultima cerere audio si ultimul cod al butonului
sunt acum diagnostice active implicit. Migrarea 1.1 -> 1.2 reactiveaza doar
aceste patru entitati daca vechea integrare le dezactivase implicit; nu
reactiveaza entitati dezactivate de utilizator/dispozitiv. Se adauga modul
tinta al alarmei, read-only. MAPARE_ENTITATI.md arata unde este fiecare functie.
Controalele native deja implementate nu sunt declarate reparate in instalarea
HA existenta doar pentru ca testele locale le creeaza; versiunea incarcata si
jurnalul HA trebuie verificate daca lipsesc si dupa actualizare.

## Functii

- Inel RGB: pornire/oprire, culoare si luminozitate, cu stare recitita
  prin get_properties, nu dedusa din ultima comanda.
- Volum sistem nativ 0..100% si limba, folosind proprietatile hubului.
- Sonerii locale din catalog: doorbell/welcome/alarm, once prin serviciul
  stock, fara transfer WAV, FFmpeg sau Aplay. Repetare si Stop native audio.
- Mod de paza nativ, mod tinta, starea alarmei, intarziere, durata, volum si sonerie
  pentru basic/home/away/sleep. Sase switch-uri de paza personalizate,
  avansate si dezactivate initial in registrul HA.
- Suprimarea indicatorului noaptea si interval HH:MM-HH:MM.
- Protectie la stergere accidentala, fara comanda de stergere/reset.
- Conexiune la API-ul nativ si IP-ul endpointului autentificat.
- Inventar Zigbee si evenimente/masuratori model-specific pastrate.
- Curatarea implicita a entitatilor vechi este limitata la aceasta intrare.
  Indisponibilitatea nu sterge copii: doua inventare valide consecutive
  trebuie sa confirme disparitia lor; o eroare intrerupe numaratoarea.

Nu creeaza temperatura cipului, luxul nevalidat al hubului, HomeKit sau
entitati AC/priza/consum din modele generice. Senzorii reali copil de
temperatura/lumina nu sunt eliminati.

## Citire si comenzi

39 proprietati selectate au fost citite pe hubul autorizat folosind
clientul livrat. Polling nativ 15 secunde; eroarea invalideaza disponibilitatea,
iar valorile expira dupa 45 secunde fara citire reusita. Conexiunea API nu
certifica sanatatea radio sau prezenta live a copiilor. IP-ul este diagnostic:
integrarea nu schimba adresa ori reteaua hubului.

Scrierile sunt limitate la proprietati/valori cunoscute, trimise o singura
data. ACK-ul individual este verificat, apoi starea este recitita.
La timeout nu exista retry de scriere sau fallback catre alt player.
Readback pending/unavailable nu reprezinta efect fizic confirmat.
Stop native audio si Stop alarm preview sunt comenzi distincte; niciuna
nu este prezentata ca oprire universala a tuturor alarmelor.

Hub system volume scrie proprietatea 5/2. Next sound request volume pastreaza
vechiul identificator si limita per cerere (implicit 5%) pentru urmatoarea
sonerie CLI. Sunt mecanisme diferite, nu un mixer hardware global. Nivelurile
mari pot fi puternice; nicio valoare nu este aplicata automat la pornire.

Modul de paza foloseste codurile native explicite 0/1/2/3. Nu afirmam ca
modul 0 opreste toate regulile de securitate. Codul raportat 4 este pastrat
in atributul native_mode, dar nu poate fi solicitat din select.
Duratele sunt valori native declarate in secunde; valorile stock mari nu
sunt reinterpretate ca minute sau ca dovada a unei durate probate.

Last hub button code este ultima valoare memorata, nu flux de click-uri.
Polling-ul ei nu genereaza evenimente. Asocierea meteo ramane diagnostic
read-only, deoarece formatul comenzii de asociere nu a fost verificat.

## Acces si instalare

Necesita Home Assistant Core 2026.10.1 sau mai nou, cu probatio inclus.
Manifestul cere python-miio==0.5.12 pentru codarea/validarea MiIO.
Telnet trebuie sa existe deja. Integrarea nu activeaza accesul, nu instaleaza
fisiere pe hub si nu creeaza porturi LAN sau servicii noi. Tokenul existent
este folosit numai in memorie, fara salvare in configuratie sau diagnostic.
Telnet nu este criptat: utilizati exclusiv reteaua locala de incredere.

1. Faceti backup Home Assistant si al integrarii anterioare.
2. Din arhiva REPOSITORY inlocuiti complet numai folderul
   config/custom_components/aqara_m1s_local, fara suprapunerea fisierelor vechi.
3. Reporniti HA cand acceptati intreruperea automatizarilor.
4. Configurati adresa si autentificarea existente. MQTT foloseste implicit
   o a doua sesiune Telnet catre brokerul stock intern 127.0.0.1:1883.
   Modul direct necesita un endpoint LAN deja existent, fara a-l crea.
5. Pornirea face doar citiri/abonari: fara sunete, lumini, armare sau
   restaurarea unor setari peste hub.

HACS foloseste fisierele repository-ului, fara filename/zip_release.
Arhiva REPOSITORY contine integrarea/documentatia, nu cercetarea privata.
Arhivele raman locale pana la o autorizare separata de publicare.

## Copii si servicii

Inventarul nu inseamna online. Copiii devin disponibili dupa raport in
sesiunea MQTT curenta. Retained nu declanseaza actiuni, iar duplicatele
identificabile sunt filtrate fara suprimarea a doua click-uri legitime.
Controlul releelor/prizelor mapate ramane experimental, implicit oprit in
optiuni si registru. Necunoscutele sunt numai raw read-only opt-in.

aqara_m1s_local.play_sound accepta entry_id sau host pentru un hub deja
configurat, sound_type, sound_id si volume. sound_path accepta numai o
cale exacta din catalogul mapat. Fara gazde sau cai arbitrare.
aqara_m1s_local.refresh_inventory reciteste inventarul, catalogul si
diagnosticele, inclusiv proprietatile native, fara pairing.
Entitatile event ale copiilor si evenimentul aqara_m1s_local_action raman
aceleasi. Nu publica actiuni sub zigbee2mqtt/... .

## Verificare si limite

Citirea celor 39 de proprietati si a doua citire autentificata au fost
verificate pe hub. Scrierile noi sunt testate cu transport criptat sintetic
si dubluri HA, NU prin schimbarea setarilor sau armarea dispozitivului real.
Nu a fost pornita o instalare HA completa pentru acest build.
0.6.4 ramane build de test, nu certificare fizica a tuturor controalelor.
TEST_RESULTS.json si LIVE_NATIVE_READ_VALIDATION.json din arhiva privata
separa testele sintetice de verificarile read-only pe dispozitiv.

Nu include capturi RF, UART, firmware/boot, reset, pairing/delete, comenzi
shell generale, radio sau streaming. Proiectul aqara_m1s_zigbee_router 0.37
si sincronizarea muzicii nu sunt modificate. Revenirea foloseste backup-ul HA.
