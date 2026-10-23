# Acoperire stock 0.6.3

| Functie | Implementare | Validare si limita |
|---|---|---|
| Inel RGB | 2/1 on, 2/3 brightness, 2/4 color; set + readback | Citire reala; scriere noua simulata |
| Volum sistem, limba | 5/2 number, 5/1 select din catalog | Nu este mixer pentru vechiul radio/Aplay |
| Sonerii | Catalog local, select/butoane once prin CLI stock | Ruta anterioara pastrata; nu toate fisierele probate auditiv |
| Repetare si Stop audio | 9/3 switch, 9/4 comanda | Scriere simulata; ACK nu certifica oprirea fizica |
| Paza si alarma | 3/1 select numeric, 3/22 sensor + binary | 0 nu promite dezarmare totala; fara armare automata |
| Config paza | 3/9..20 delay/duration/volume, 3/24..27 sound | Intervalele si catalogul sunt validate |
| Moduri personalizate | 3/3..8 switch-uri avansate | Dezactivate initial; comportament fizic nevalidat |
| Stop preview | 3/28 buton separat | Nu este oprire universala a alarmei |
| Indicator nocturn | 6/1 suprimare, 6/2 interval text | Program validat; nu simplu LED on/off |
| Protectie stergere | 7/1 switch | Nu sterge/disociaza dispozitive |
| Asociere meteo | 16/1 read-only | Fara format de asociere ghicit |
| Buton fizic hub | 4/1 ultimul cod, diagnostic opt-in | Nu emite click-uri din cache |
| Conexiune si IP | Citire autentificata; endpoint verificat | Nu inseamna radio/copii online; nu schimba IP |
| Copii Zigbee | Inventar si evenimente/masuratori 0.6.2 | Control copii mapati opt-in |
| Curatare registru | Numai intrarea proprie, absenta confirmata | Nu sterge la timeout/unavailable |
| Temperatura/lux hub | Nu sunt expuse | Excludere ceruta, masuratori nevalidate |
| Modele AC/priza/consum generice | Nu sunt expuse | Getter-ul implicit nu confirma hardware existent |
| Radio/grup sincronizat | Proiect separat, nemodificat | Fara FFmpeg/Aplay sau transfer WAV |

38 proprietati citite cu succes pe dispozitivul autorizat la 23.10.2026.
Tokenul este numai in memorie. Nicio scriere nu este reluata automat.
Raspunsurile incomplete sau gresite nu devin stari confirmate. Starea
logica stock poate fi memorata de hub; nu este masurare fizica independenta.
In acest build hubul a fost folosit numai pentru verificari read-only.
