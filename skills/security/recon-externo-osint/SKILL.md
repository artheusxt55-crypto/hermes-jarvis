---
name: recon-externo-osint
description: Use when mapping a domain's external surface - subdomains, DNS, hosts.
version: 1.0.0
metadata:
  hermes:
    tags: [pentest, recon, osint, dns, amass]
---

# Recon externo e OSINT

Mapeamento de superficie **fora** do host, sem tocar em servico. E a primeira
fase de qualquer auditoria e a unica que voce pode rodar antes de escopo por IP.

## Pre-condicao

Passa por `pentest-authorization-gate`. Se o alvo e dominio de terceiros, a
resposta e nao.

## Ordem das fases

1. **DNS e subdominios.** Amass 5.1.1 mudou: `-passive` e deprecated
   (passivo e o default) e `-o` nao existe mais; a saida vai para stdout e
   `-df <arquivo>` grava. **Use o binario direto**, nao o wrapper:
   ```
   ssh kali-vm '/usr/lib/amass/amass enum -d <dominio> -df ~/work/<alvo>/amass.txt'
   ```
   Por que: `/usr/bin/amass` e um wrapper `sh` que roda
   `sudo libpostal_data download` antes de qualquer coisa. Como o sudo desta VM
   pede senha e nao ha terminal, **todo comando `amass` falha com
   "sudo: a password is required"** — foi exatamente o que aconteceu em
   2026-10-04. `/usr/lib/amass/amass` funciona direto.
   `-active` so depois, e nunca sem o usuario pedir.

2. **Resolucao.** `dnsrecon -d <dominio> -n` para NS, MX, SPF, e zone transfer.
   Teste de AXFR: `dig axfr <dominio> @<ns>`. Zone transfer aberta e achado
   critico e vem antes de qualquer scan.

3. **Cross-check de subdominios.** `subfinder` NAO esta instalado (ver
   `references/kali-inventory.txt`); use `amass` + resolvers publicos
   (`crt.sh`: `curl -s "https://crt.sh/?q=%25.<dominio>&output=json"`) e
   deduplique. Saldo: `sort -u`.

4. **Servicos expostos na web, sem invadir.** Para cada subdominio, so
   `curl -sSI` e `whatweb -a 3`. Nada de fuzz aqui.

5. **Historico.** Shodan/censys por API se o usuario tiver chave; Wayback
   Machine (`web_extract` nao serve, use curl) para URLs antigas que apontam
   para endpoints esquecidos — achado classico de auditoria.

## Entrega

Tabela: subdominio | IP | porta aberta confirmada | tech | observacao.
Nunca "possivelmente" na coluna de IP: so o que `dig`/`nmap` resolveram.

## Armadilhas

- Subdominio que resolve para IP de cloudflare nao e alvo seu: auditar ele e
  auditar a Cloudflare. Marque como `CDN/terceiro — fora de escopo`.
- `amass` passivo as vezes leva minutos. Lance em background com `-timeout` e
  siga outras fases em paralelo.
- Alvo com DNSSEC/Wildcard: subdominio inventado tambem resolve. Teste
  `dig x9q2-nonexistente.<dominio>` antes de confiar na lista.
