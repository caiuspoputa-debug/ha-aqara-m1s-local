# Extragerea tokenului MiIO pentru Aqara Hub M1S

Acest document descrie metoda folosită pentru a obține tokenul MiIO al unui hub Aqara M1S direct din Home Assistant, cu ajutorul integrării **Xiaomi Gateway 3**.

> Tokenul MiIO este o informație sensibilă. Nu îl publica și nu îl include în capturi de ecran.

## Cerințe

- Hub Aqara M1S adăugat în contul Xiaomi / Mi Home.
- Home Assistant funcțional.
- HACS instalat.
- Integrarea custom **Xiaomi Gateway 3** de la AlexxIT instalată.

## 1. Instalarea integrării Xiaomi Gateway 3

În Home Assistant:

1. Deschide **HACS**.
2. Intră la **Integrations**.
3. Caută **Xiaomi Gateway 3**.
4. Instalează integrarea.
5. Repornește Home Assistant dacă este cerut.

## 2. Adăugarea integrării

În Home Assistant:

1. Deschide **Setări**.
2. Intră la **Dispozitive și servicii**.
3. Apasă **Adaugă integrare**.
4. Caută **Xiaomi Gateway 3**.
5. Autentifică-te cu același cont Xiaomi folosit în aplicația Mi Home.
6. Selectează regiunea corectă a contului Mi Home.

## 3. Găsirea hubului Aqara M1S

După autentificare, integrarea afișează dispozitivele asociate contului Xiaomi.

Identifică hubul după una sau mai multe dintre următoarele date:

- model: `lumi.gateway.aeu01`
- numele setat în Mi Home
- adresa IP locală
- adresa MAC

Pentru hubul nou, IP-ul folosit în test a fost:

```text
192.168.0.104
```

## 4. Copierea tokenului MiIO

În informațiile dispozitivului apare câmpul:

```text
Token
```

Tokenul MiIO valid are:

- exact 32 de caractere;
- numai caractere hexazecimale: `0-9` și `a-f`.

Exemplu fictiv:

```text
0123456789abcdef0123456789abcdef
```

Nu copia tokenul real în documentație, GitHub, capturi de ecran sau conversații publice.

## 5. Verificarea tokenului din PowerShell

Pe Windows, după instalarea `python-miio`, verificarea se face astfel:

```powershell
python -m miio.cli device --ip 192.168.0.104 --token TOKENUL_MIIO info
```

Înlocuiește `TOKENUL_MIIO` cu tokenul real de 32 de caractere.

Dacă tokenul și IP-ul sunt corecte, comanda va returna informații despre hub.

## 6. Utilizarea tokenului pentru activarea Telnet

După verificarea tokenului, acesta poate fi folosit în procedura separată de activare Telnet/root pentru Aqara M1S.

Vezi documentația proiectului:

```text
aqara_m1s_telnet_root_persistent_tutorial_RO.txt
```

## Probleme frecvente

### `Token length != 32 chars`

În comandă a fost introdus un text incomplet, un placeholder precum `TOKEN` sau un token greșit.

### Hubul nu apare în lista dispozitivelor

Verifică:

- contul Xiaomi folosit;
- regiunea selectată;
- dacă hubul apare în aplicația Mi Home;
- dacă integrarea Xiaomi Gateway 3 s-a autentificat corect.

### Tokenul începe cu `gho_`, `github_` sau alt prefix

Nu este token MiIO. Este probabil un token pentru alt serviciu.

## Notă de securitate

Dacă tokenul MiIO a fost publicat accidental, tratează-l ca pe o credențială locală expusă. Evită să publici IP-ul, tokenul și alte date de acces împreună.
