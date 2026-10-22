# Provenienta si separarea dovezilor

## Surse locale

- Baza nemodificata: Desktop/M1S/aqara_m1s_local_v0_5_9.
- Lucrarea .109: proiectul 2026-10-15/15-10-2026-08-34-46,
  work/m1s_native_controller_v030_20261021.
- Contract inel: protocol/STOCK_LOGICAL_LIGHT_CONTRACT.txt.
- Module si limite: protocol/CONTRACT_MODULES.txt.
- Validare cerere/ACK: stock/m1s_stock_cli.c.
- Proba fizica: outputs/M1S_Controller_v0.2.0-lab_Proba_hub_2026-10-21.txt.
- MQTT copii: outputs/M1S109_Interfete_stock_2026-10-21/Contracte_MQTT_stock.txt.
- Mapari model/resursa: tabelul AqaraGateway din copia research locala,
  commit 1a868ff7876a3bed74c59ed7d21a9d5d3883540e.
  Nu importam sau redistribuim utilitarele de acces, exploit, patch,
  firmware ori modulul upstream complet. Retinem fapte de protocol
  intr-un registru mic scris separat.

Hashurile surselor utilizate sunt in SOURCE_EVIDENCE.json. Fisierele
brute de cercetare, configuratiile private si capturile originale nu sunt
incluse in arhiva integrarii.

## API Home Assistant

Compatibilitatea de schema a fost verificata cu probatio==0.13.0,
din cerintele oficiale Core 2026.10.1. Au fost consultate sursele oficiale:

- https://github.com/home-assistant/core/blob/2026.10.1/requirements.txt
- https://github.com/home-assistant/core/blob/2026.10.1/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.10.1/homeassistant/components/event/__init__.py

Testele locale de adaptor folosesc dubluri HA, nu intregul Core.
Nu revendicam un boot HA, test fizic sau stabilitate de lunga durata
pe baza acestor teste.

## Lucrari excluse

Etapele ulterioare ale cercetarii universale RX/ROM/firmware nu reprezinta
un contract HA gata de utilizare. Ele nu sunt integrate sau executate.
Arhiva privata mare a proiectului ramane separata, nemodificata si
nepublicata. Automatizarile personale nu sunt incluse in acest pachet.
