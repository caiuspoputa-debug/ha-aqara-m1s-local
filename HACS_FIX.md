# Corectie HACS - versiunea 0.6.1

## Cauza

Configuratia precedenta impunea zip_release=true si un filename fix.
HACS incerca sa descarce un asset de release numit exact
Aqara_M1S_Local_v0.6.0_STOCK_LAB_TEST.zip. Serverul a raspuns 404.
Erorile ulterioare update.install si WebSocket sunt consecintele acelui
esec, nu erori suplimentare ale hubului sau ale codului Zigbee.

## Corectie

In 0.6.1 am eliminat zip_release si filename din hacs.json. HACS poate folosi
fisierele integrarii din repository, fara un ZIP de release separat.
Nu s-a modificat logica de control stock.

Pentru aceasta ruta, repository-ul trebuie sa contina efectiv:

~~~
hacs.json
custom_components/aqara_m1s_local/__init__.py
custom_components/aqara_m1s_local/manifest.json
custom_components/aqara_m1s_local/... restul fisierelor integrarii
~~~

Un ZIP atasat pe GitHub sau fisierele automate Source code nu inlocuiesc
aceasta structura. Corectia trebuie sa ajunga pe GitHub in versiunea/ref-ul
folosit de HACS; modificarea numai a arhivei locale nu repara downloadul.
Nu declara content_in_root=true pentru structura de mai sus.

Se pastreaza tagul v0.6.0 nemodificat. Fisierele corectate, inclusiv
manifest.json cu 0.6.4, trebuie sa fie in commitul noului release v0.6.4.
HACS va putea instala 0.6.4 numai dupa ce versiunea exista efectiv pe
GitHub. Arhiva REPOSITORY ofera structura de extras in repository;
atasarea ei ca simplu asset ZIP nu inlocuieste fisierele din repository.

Arhiva corectata este livrata numai local; nu am facut push, release,
upload de asset, instalare sau restart Home Assistant.
Arhiva anterioara si copiile de siguranta nu au fost sterse.

Documentatie oficiala:
https://www.hacs.xyz/docs/publish/start/#hacsjson
https://www.hacs.xyz/docs/publish/integration/#repository-structure
