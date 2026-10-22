# 0.6.0 STOCK LAB TEST

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
