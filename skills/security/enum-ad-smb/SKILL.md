---
name: enum-ad-smb
description: Use when auditing Windows/Samba - SMB, LDAP, shares, AD enumeration.
version: 1.0.0
metadata:
  hermes:
    tags: [pentest, smb, ldap, active-directory, enum4linux, netexec]
---

# Enumeracao Windows/Samba/AD

Roda dentro do escopo. Em rede corporativa, **esta e a fase onde o dano real
acontece**: share aberto com credencial, LDAP sem filtro, bloodhound. Trate a
enumeracao como leitura de metadados, nao como movacao lateral.

## Ferramentas (todas presentes na VM)

- `enum4linux` — SMB/LDAP/NTLM automatizado
- `smbclient`, `rpcclient`, `smbmap` — manual, mais controle
- `netexec` — **substitui o crackmapexec** (nao instalado); tem BloodHound,
  sharp, spraybuilt-in
- `impacket-scripts` — `GetUserSPNs`, `secretsdump.py`, `mimikatz`-free
- `responder` — LLMNR/NBT-NS poisoning, so em lab

## Ordem

1. **Enum passiva primeiro.**
   ```
   ssh kali-vm 'enum4linux -A <alvo> > ~/work/<alvo>/enum4linux.txt 2>&1'
   ```
   `-A` = tudo com menos agressividade. Comece por aqui.
   enum4linux 0.9.1 confirmado e funcional (2026-10-04).

2. **Shares.**
   `smbclient -L //<alvo> -N` (lista anonima). Achado critico: share
   `IPC$`/`ADMIN$`/`C$` aberto **anonimamente** — anote e pare nesse host.

3. **SMB signing e versao.** `nmap --script smb2-security-mode,smb2-vuln-ms17-010 -p445`.
   SMB signing desabilitado e o que permite relay — media/alta conforme contexto.

4. **LDAP.** `ldapsearch -x -H ldap://<alvo> -b "DC=<dominio>,DC=com" '(objectClass=*)'`.
   `anonymous bind` habilitado e achado. `-z 100` limite para nao entupir.

5. **Contas Kerberos (privilegio).**
   ```
   ssh kali-vm 'netexec smb <dominio>/<alvo> -u users.txt -p "" --no-bruteforce --sam'
   ssh kali-vm 'impacket-GetUserSPNs <dominio>/<alvo> -request'
   ```
   SPN com conta de servico e hash mais fraco e o caminho classico. **Nao**
   quebrar o hash no mesmo passo: enumere, reporte, deixe a quebra separada e
   autorizada.

6. **Sessoes, shares ePrivilegio.** netexec 1.5.1 usa **subcomando de
   protocolo**, nao flag global — `netexec smb ...`, `netexec ldap ...`,
   `netexec winrm ...`. `netexec --shares <alvo>` (a forma antiga) falha.
   Flags verificadas: `--shares`, `--sam`, `--lsa`, `--ntds`, `--users`,
   `--groups`, `--sessions`, `--loggedon-users`, `--local-auth`, `--no-bruteforce`,
   `--pass-pol`, `--kerberos-keys`, `--gen-relay-list`, `--dpapi`, `--sid-brute`
   via `--rid-brute`.

   bloodhound foi removido do netexec 1.5.1: **nao existe** `--bloodhound` nesta
   versao. Para coleta de grafo use `impacket-bloodhound -np` (impacket-scripts
   instalado) ou netexec `--sam --lsa --ntds` e monte o BloodHound do lado do
   cliente.

## Limites que voce respeita

- Nao fazer brute force de senha em conta corporativa com lockout policy ativa:
  isso e denuncio, nao auditoria. `netexec --spray` so com pedido explicito e
  alvo de lab.
- Nao habilitar relay/poisoning/LSASS em maquina de terceiro. `responder` e
  acucar-sino: nunca.
- LDAP/`--sam` extrai dados de outros usuarios. Em dado real isso e tratamento de
  informacao pessoal — minimize, guarde cifrado, apague ao fim.

## Entrega

Achado = servico + evidencia + conta ou share afetado + impacto. "Share ADMIN$
acessivel sem credencial em DC01" e achado. Enum de contas e inventario, nao
vulnerabilidade — separe as secoes do relatorio.
