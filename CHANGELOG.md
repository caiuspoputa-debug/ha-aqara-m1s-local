# 0.6.2 - Stock real, evenimente si curatarea entitatilor

- MQTT implicit prin sesiune Telnet autentificata spre brokerul intern;
  nu mai depinde de un port LAN 1884 absent pe hubul stock.
- Transport ASCII catre broker pentru a pastra octetii de control MQTT.
  CONNACK/SUBACK, mesaje si keepalive verificate pe hubul stock.
- Catalogul local descoperit: sonerii 1..4, welcome 1..10, alarm 1..9,
  numai unde fisierele native exista. Fara fallback Aplay/FFmpeg.
- Curatare automata activata implicit, strict pe intrarea integrarii.
  Inventarul/catalogul invalid si simpla indisponibilitate nu sterg entitati.
  Disparitia copiilor necesita doua inventare valide consecutive.
- HomeKit si vechile controale nemapate nu mai raman entitati orphan.
- Diagnostice sistem prin citire /proc; nu depind de pidof/cut inexistente
  pe hub. Memoria foloseste MemAvailable sau o estimare free+buffers+cached.
- Identitatile scenelor mapate sunt pastrate; fara publicare sau instalare.

## 0.6.1 - Corectie HACS

- Eliminat zip_release/filename: instalare din fisierele repository-ului.
- Versiune manifest, constante si diagnostice actualizata la 0.6.1.
- Arhiva REPOSITORY separata de SOURCE_TESTS_PRIVAT si cercetarea privata.
- Logica de control stock ramane cea din 0.6.0; nu sunt probe fizice noi.
- Nicio publicare, instalare sau repornire automata.

## 0.6.0 STOCK LAB TEST

- Baza 0.5.9 adaptata la serviciile stock descoperite in .109 lab.
- RGB direct inlocuit cu ruta logica stock si ACK corelat strict.
- Eliminat transferul WAV dus-intors pentru soneria nativa validata.
- Inventar, dispozitive copil, evenimente si stari model-specific.
- Conexiunea MQTT si inventarul nu mai implica disponibilitate radio.
- Reconnect fara replay, filtrare retained/duplicate, payload-uri limitate.
- Corectata rutarea multi-hub a serviciilor si curatarea la unload.
- Diagnostice fara identificatori privati si statusuri ambigue de online.
- Profilul stock nu preia vechiul radio/Aplay, comenzi shell generice,
  restaurare audio neverificata sau orice WAV fara mapare nativa.
- Livrare numai locala. Fara instalare pe hub/HA si fara publicare GitHub.
