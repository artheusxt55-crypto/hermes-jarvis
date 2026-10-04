---
name: enum-rede-servicos
description: Use when scanning hosts, ports and services on an authorized range.
version: 1.0.0
metadata:
  hermes:
    tags: [pentest, nmap, enum, network]
---

# Enum de rede e servicos

## Pre-condicao

`pentest-authorization-gate`. Escopo tem que citar host ou CIDR.

## Escada de ruido

1. **Ping/host discovery.** `nmap -sn <cidr> -oA ~/work/<alvo>/hosts`
   Em rede com NAT/ firewall, `-sn` falha: caia para `nmap -Pn`.

2. **Portas.** `-sV -sC --top-ports 1000` primeiro. So `-p-` quando o
   usuario quiser cobertura total — e lento e rumoroso.
   Anote a raza: varredura rapida demais pode parecer ataque na deteccao do
   cliente. `--max-rate 500` em rede de terceiros.

3. **Velocidade em rede grande.** `masscan -p1-65535 --max-rate 1000 <cidr>`
   e ordens de grandeza mais rapido, mas so com as portas (sem `-sV`).
   Pipeline classico: masscan discoverre portas -> nmap confirma com `-sV`.

4. **Servicos, um por um.** Para cada porta aberta: `nmap -sV -sC -p<PORTA>
   --script=<familia> <alvo>`. Famílias uteis:
   - SMB: `smb-vuln*, smb2-*` (o que importa: versao + signing)
   - HTTP: `http-title, http-headers, http-methods, http-enum`
   - Enumera: `vuln`, `vulners` (exige `-sV`)

5. **Metadados em servicos diferentes.** SSH banner, versao FTP, versao SMTP,
   `whatweb` no http. Versao e *fingerprint*, nao vuln — ver regra abaixo.

## Diff e registro

```
ssh kali-vm "nmap ... -oA ~/work/<alvo>/scan-1"
```
`-oA` gera os tres formatos (normal/xml/grepable); **use o xml** para processar
depois. Compare scans com `diff` entre rodadas para achar porta nova — drift de
superficie e um achado em si.

## Regras de honestidade

- Versao antiga nao e vulnerabilidade. Sem CVE confirmada e sem teste, escreva
  "versao X — nao verificada".
- `vuln` scripts do nmapFalham em servico custom. Resultado falso positivo e
  pior que sem dado. Confirme sempre com request real antes de reportar.
- Cada porta aberta no relatorio precisa de evidencia: linha do nmap + saida do
  script. Sem os dois, nao entra.

## Entrega

Tabela ordenada por risco (nao por porta): porta | servico | versao | script
que disparou | confirmacao manual | risco. Chefia de "observacao" curta.
