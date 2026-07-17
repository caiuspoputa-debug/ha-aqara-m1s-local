# Extracting the MiIO Token for Aqara Hub M1S

This document describes the method used to obtain the MiIO token of an Aqara M1S hub directly from Home Assistant with the **Xiaomi Gateway 3** integration.

> The MiIO token is sensitive information. Do not publish it or include it in screenshots.

## Requirements

- Aqara M1S hub added to a Xiaomi / Mi Home account.
- A working Home Assistant installation.
- HACS installed.
- The custom **Xiaomi Gateway 3** integration by AlexxIT installed.

## 1. Install the Xiaomi Gateway 3 integration

In Home Assistant:

1. Open **HACS**.
2. Go to **Integrations**.
3. Search for **Xiaomi Gateway 3**.
4. Install the integration.
5. Restart Home Assistant if requested.

## 2. Add the integration

In Home Assistant:

1. Open **Settings**.
2. Go to **Devices & services**.
3. Select **Add integration**.
4. Search for **Xiaomi Gateway 3**.
5. Sign in with the same Xiaomi account used in the Mi Home app.
6. Select the correct Mi Home account region.

## 3. Find the Aqara M1S hub

After authentication, the integration displays the devices associated with the Xiaomi account.

Identify the hub using one or more of the following:

- model: `lumi.gateway.aeu01`
- the name assigned in Mi Home
- local IP address
- MAC address

The IP address used for the new hub during testing was:

```text
192.168.0.104
```

## 4. Copy the MiIO token

The device information includes a field named:

```text
Token
```

A valid MiIO token has:

- exactly 32 characters;
- hexadecimal characters only: `0-9` and `a-f`.

Fictitious example:

```text
0123456789abcdef0123456789abcdef
```

Do not store the real token in documentation, GitHub, screenshots, or public conversations.

## 5. Verify the token in PowerShell

After installing `python-miio`, verify the token on Windows with:

```powershell
python -m miio.cli device --ip 192.168.0.104 --token MIIO_TOKEN info
```

Replace `MIIO_TOKEN` with the actual 32-character token.

If the IP address and token are correct, the command returns information about the hub.

## 6. Use the token to enable Telnet

After verification, the token can be used with the separate Aqara M1S Telnet/root activation procedure.

See:

```text
aqara_m1s_telnet_root_persistent_tutorial_EN.txt
```

## Common problems

### `Token length != 32 chars`

The command contains an incomplete value, a placeholder such as `TOKEN`, or the wrong token.

### The hub does not appear in the device list

Check:

- the Xiaomi account being used;
- the selected region;
- whether the hub appears in the Mi Home app;
- whether Xiaomi Gateway 3 authenticated successfully.

### The token starts with `gho_`, `github_`, or another prefix

It is not a MiIO token. It probably belongs to another service.

## Security note

If the MiIO token is accidentally published, treat it as an exposed local credential. Avoid publishing the IP address, token, and other access details together.
