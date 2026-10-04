---
name: enum-web-diretorios
description: Use when fuzzing web content, directories, params and hidden files.
version: 1.0.0
metadata:
  hermes:
    tags: [pentest, web, ffuf, gobuster, fuzzing]
---

# Fuzzing de conteudo web

## Pre-condicao

`pentest-authorization-gate`, com URL base confirmada. Fuzzing pesado (wordlist
grande) contra alvo sem autorizacao explicita: nao.

## Escolher a ferramenta certa

| Situacao | Ferramenta |
|---|---|
| diretorios/arquivos rapido, status code differential | `ffuf` |
| precisa de template e wildcard filter | `gobuster` |
| wordlist classica + rapidao | `dirb` |
| wordlist media + recursao | `dirbuster` |

`ffuf` e o padrao: ele tem o filtro de tamanho que evita os 200 falsos positivos
de pagina 404 custom.

## ffuf na pratica

```
ssh kali-vm 'ffuf -w /usr/share/dirb/wordlists/common.txt \
  -u http://<alvo>/FUZZ -mc all -fc 404 -t 40 -rate 100 \
  -o ~/work/<alvo>/ffuf-root.json -of json'
```

Validado nesta VM (ffuf 2.1.0): gera JSON parseavel e aceita `-o`/`-of`.
`-ac` (autocalibrar) so com 404 estavel — em 404 dinamico ele erra o filtro.

`-fc 404` e essencial: sem ele, tudo que retorna 404 entra como achado. Prefira
`-ac` (autocalibrar) quando a 404 nao for estavel.

**Wordlists: NAO existe `/usr/share/seclists` nesta VM** (verificado
2026-10-04; `find` nao acha `common.txt` em lugar nenhum). Os paths reais:

| Path | Conteudo |
|---|---|
| `/usr/share/dirb/wordlists/` | `common.txt` (~4.6k), `big.txt`, `small.txt`, `mutations_common.txt` |
| `/usr/share/wordlists/` | `rockyou.txt.gz`, `dirb/`, `dirbuster/`, `wfuzz`, `sqlmap.txt`, `nmap.lst`, `seclists/`? |

`seclists` esta instalado como **pacote**, mas o diretorio nao esta em
`/usr/share/seclists`. Localize antes de usar:
`ssh kali-vm 'find / -name common.txt -path "*Web-Content*" 2>/dev/null | head'`

Path errado faz o ffuf rodar 0 linhas e sair 0 — e parece "nada encontrado".
Sempre confira `wc -l` da wordlist e o `results:` do JSON antes de concluir que
o alvo esta limpo. Um JSON com `results: []` com wordlist vazia e falso
negativo, nao resultado.

## Parametros e virtual hosts

- Parametros: `ffuf -u "http://<alvo>/page?FUZZ=1" -w <wordlist>` ou
  `wfuzz -c` para validar valor.
- Vhosts: `ffuf -u http://<alvo>/ -H "Host: FUZZ.<dominio>" -w <subs>`.
  Achado classico: vhost de staging em producao.

## Filtragem e o que NAO fazer

- Size differential (`-fs`) em paginas com conteudo dinamico gera ruido: verifique
  manualmente os 200 maiores hits antes de reportar.
- Nunca reporte achado de fuzzer sem abrir a URL e ver o que retorna. Se 403 em
  tudo, o alvo esta atras de WAF — isso e um achado por si so, mas de
  "presenca de WAF", nao de "diretorio escondido".
- `nikto` e `nuclei` rodam em lote e produzem muito falso positivo. Use no fim,
  como checagem de cobertura, nunca como fonte de achado.

## Entrega

Achado = URL + status + tamanho + o que a pagina mostra. Um `200 OK` com a
pagina de login em `/admin` e achado de exposicao; um `302` para `/login` e
comportamento esperado.
