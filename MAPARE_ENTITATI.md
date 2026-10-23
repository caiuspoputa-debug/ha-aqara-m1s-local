# Mapare functii native - 0.6.4

Aceste entitati apartin dispozitivului HUB, nu butonului Zigbee copil.
In pagina hubului, verificati Controale, Configurare si Diagnostic, sau
Settings > Devices & services > Entities filtrat dupa integrare.
entity_id depinde de numele dat hubului si de redenumirile utilizatorului.
Cheile de mai jos sunt sufixe unique_id, NU entity_id-uri de copiat in YAML.

| Functie | Platforma / nume | Sufix unique_id | Proprietate |
|---|---|---|---|
| Inel pornit, luminozitate, RGB | light / Ring light | ring_light | 2/1, 2/3, 2/4 |
| Volum sistem stock | number / Hub system volume | native_system_volume | 5/2 |
| Limba | select / System language | native_system_language | 5/1 |
| Catalog audio | sensor / Native audio catalog | native_audio_catalog | 9/5 |
| Limbi disponibile | sensor / Native language catalog | native_language_catalog | 9/6 |
| Ultima cerere audio memorata | sensor / Last native audio request | native_last_audio_request | 9/1 |
| Repetare audio | switch / Native audio repeat | native_audio_repeat | 9/3 |
| Oprire audio | button / Stop native audio | native_stop_audio | 9/4 |
| Alegere sunet pentru butonul Play | select / Native stock sound | sound_select | catalog local |
| Redare selectie | button / Play selected native sound | play_selected_sound | comanda stock |
| Redare welcome | button / Play welcome/1..10 | play_music_scene_welcome_1_wav .. welcome_10_wav | CLI indici 21..30 |
| Volum urmatoarei sonerii | number / Next sound request volume | sound_playback_volume | limita locala per cerere |
| Mod curent | select / Native guard mode | native_guard_mode | 3/1 |
| Mod tinta (citire) | sensor / Native guard target mode | native_guard_target_mode | 3/21 |
| Starea alarmei | sensor / Native alarm status | native_alarm_status | 3/22 |
| Alarma activa | binary_sensor / Native alarm active | alarm_active | derivata din 3/22 |
| Intarziere, durata, volum pe mod | number / Basic, Home, Away, Sleep | native_basic_delay/duration/volume etc. | 3/9..20 |
| Sonerie de alarma pe mod | select / Basic, Home, Away, Sleep alarm sound | native_basic_sound, home_sound, away_sound, sleep_sound | 3/24..27 |
| Oprire preview alarma | button / Stop alarm preview | native_stop_alarm_preview | 3/28 |
| Suprimare indicator nocturn | switch / Night indicator suppression | native_indicator_night_off | 6/1 |
| Interval suprimare indicator | text / Indicator suppression schedule | native_indicator_schedule | 6/2 |
| Protectie stergere accidentala | switch / Accidental deletion protection | native_deletion_protection | 7/1 |
| Ultimul cod buton hub | sensor / Last hub button code | native_hub_button_code | 4/1 |
| Conexiune API hub | binary_sensor / Hub connection | native | citire autentificata |
| IP endpoint autentificat | sensor / Hub IP address | hub_ip_address | endpoint MiIO |

Catalogul audio expune numele in atributul available_sounds. Selectoarele
Basic/Home/Away/Sleep alarm sound contin intentionat numai familia alarm;
ele configureaza alarma, nu sunt selectoare pentru welcome/doorbell.

Ultimul cod buton este cache, nu inlocuieste evenimentele copilului Zigbee.
Ultima cerere audio este cache-ul API-ului stock; redarea CLI nu este
afirmata ca actualizand acest cache. Repetarea nativa si fiecare comanda
Play once sunt setari distincte. Indicatorul nocturn nu este ring light.

Toate entitatile din tabel sunt active implicit la o instalare noua.
Actualizarea reactiveaza cele patru diagnostice anterior dezactivate implicit,
dar nu anuleaza disabled_by=user/device/config_entry. Cele sase switch-uri
custom_guard si asocierea meteo raman avansate, dezactivate implicit.

Nu se schimba IP-ul hubului si nu se expun lux/temperatura nevalidate.
Inainte de instalarea versiunii noi, niciun fisier din arhiva nu poate adauga
entitati in instanta HA existenta. Daca lipsesc si dupa actualizare, verificati
versiunea efectiv incarcata si jurnalul custom_components.aqara_m1s_local.
