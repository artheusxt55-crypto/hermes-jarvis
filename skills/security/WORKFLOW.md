# Fluxo completo de auditoria

Uso: `recon-externo-osint` -> `enum-rede-servicos` -> `enum-web-diretorios` /
`enum-ad-smb` / `vuln-scan-web-tls` -> `cred-analise-hashes` ->
`relatorio-pentest`.

## 0. Autorizacao (gate)

Escreva `~/work/<alvo>/SCOPE.md` na VM antes do primeiro pacote. Sem alvo e sem
declaracao de propriedade, o processo para aqui.

## 1. Recon sem tocar no alvo

```
ssh kali-vm 'mkdir -p ~/work/<alvo>'
ssh kali-vm '/usr/lib/amass/amass enum -d <dominio> -df ~/work/<alvo>/amass.txt'
ssh kali-vm 'dnsrecon -d <dominio> -n | tee ~/work/<alvo>/dnsrecon.txt'
```

## 2. Superficie

```
ssh kali-vm 'nmap -sV -sC --top-ports 1000 -oA ~/work/<alvo>/nmap <alvo>'
ssh kali-vm 'whatweb -a 3 <alvo> | tee ~/work/<alvo>/whatweb.txt'
```

## 3. Profundidade por servico

- HTTP: `ffuf` + `nuclei -tags cve,exposure` + `sqlmap` (so com parametro
  confirmado) + TLS via `sslscan`/`openssl`.
- SMB/LDAP: `enum4linux -A`, `netexec smb ... --shares`, `impacket-GetUserSPNs`.
- Credencial: `john` (hashcat precisa de `pocl-opencl-icd`, ver skill).

## 4. Relatorio

`relatorio-pentest`, com a secao "nao foi testado" obrigatoria.

## Ordem que economiza tempo

Nao comeca exploit antes de mapear tudo: e o erro classico de alarmar o WAF e de gerar
falso positivo que o cliente vai usar contra o relatório. Recon completo
primeiro, entao ataque dirigido.

## Entregaveis no repo

Copie de `~/work/<alvo>/`: o `.md` do relatorio para
`relatorios/<alvo>-<data>.md`, e as saidas brutas para `evidence/<alvo>/`
**somente se nao contiverem dado sensivel** (hash, senha, PII).
