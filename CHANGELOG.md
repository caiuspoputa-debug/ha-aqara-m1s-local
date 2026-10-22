# 0.6.1 - Corectie HACS

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
