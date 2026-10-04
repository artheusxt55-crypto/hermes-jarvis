---
name: vuln-scan-web-tls
description: Use for automated web vuln scanning and TLS/SSL configuration audit.
version: 1.0.0
metadata:
  hermes:
    tags: [pentest, nuclei, nikto, tls, sslscan, web]
---

# Scan automatizado e auditoria de TLS

Fase de cobertura ampla depois do reconhecimento detalhado. Ferramenta
automatizada aqui serve para **cobrir**, nao para **concluir**.

## nuclei (padrao)

```
ssh kali-vm 'nuclei -u https://<alvo> -severity info,low,medium,high,critical \
  -rate-limit 50 -c 5 -o ~/work/<alvo>/nuclei.txt -json-export ~/work/<alvo>/nuclei.json'
```

- Comecar em `info,low` e subir. `critical` primeiro queima o alvo e gera WAF.
- `-rate-limit` sempre. `-c 5` evita parecer DoS.
- Tags uteis: `cve`, `misconfig`, `exposure`, `tech`. Rodar `-tags cve,exposure`
  primeiro e o que rende relatorio.

## nikto

`nikto -h <alvo> -maxtime 5m -o ~/work/<alvo>/nikto.txt`
Lento e cheio de falso positivo (acha "erro de banco de dados" em qualquer
PHP). Use para headers inseguros e arquivos conhecidos, e **confirme com curl**.

## TLS/SSL

```
ssh kali-vm 'sslscan --show-certificate <host:port> > ~/work/<alvo>/ssl.txt'
ssh kali-vm 'echo | openssl s_client -connect <host:port> -servername <host> -tls1_1 2>/dev/null | head -5'
```

Checklist manual do resultado (isto e o que vai no relatorio):

| Achado | Como confirmar | Gravidade |
|---|---|---|
| TLS 1.0/1.1 habilitado | `openssl s_client -tls1` conecta? | media |
| Suite fraca (RC4, 3DES, export) | `sslscan` lista em `VULNERABLE` | media |
| Cadeado sem CA / expirado | `openssl s_client` mostra verify error | **alta** |
| Sem HSTS | header `Strict-Transport-Security` ausente | baixa |
| Sem `secure` em cookie | `Set-Cookie` sem flag em app https | media |

`testssl.sh` nao esta instalado nesta VM (confirme em
`references/kali-inventory.txt`); `sslscan` + `openssl` cobrem o essencial.
Instalar: `ssh kali-vm "sudo apt install -y testssl.sh"`.

## Regra de severidade

Nuclei classifica por template, nao por impacto no SEU alvo. Um "critical" que
requer autenticacao de admin e um "info" no seu contexto. Reclassifique sempre
com base em: exposicao (anonima?) + impacto real + dado alcancado. Dizer isso no
relatorio.
