---
name: cred-analise-hashes
description: Use when auditing password strength, weak defaults and hash quality.
version: 1.0.0
metadata:
  hermes:
    tags: [pentest, hashcat, john, password, creds]
---

# Analise de credenciais

Escopo: medir **forca** de senha e politica. Quebrar hash de sistema do cliente so
com autorizacao explicita e com o hash exposto pelo proprio cliente.

## Analise de politica (o deliverable principal)

Sem quebrar nada:
- `crunch` para gerar casos base: `crunch 8 12 -o ~/work/<alvo>/base.txt`
- Contar variacao: `hashcat --example-hashes` mostra o custo por modo.
- Politica observavel: longueur minima aceita, historico, lockout. Medir isso e
  relatar e mais util que quebrar uma senha.

## O que funciona NESTA VM: john, nao hashcat

`hashcat -I` responde `CL_PLATFORM_NOT_FOUND_KHR / No OpenCL, HIP or CUDA
compatible platform found`. **hashcat esta instalado e nao roda** — a VM nao tem
runtime OpenCL. Verificado em 2026-10-04.

- rockyou.txt.gz existe (53 MB) mas precisa de `sudo gunzip` e o sudo desta VM
  pede senha → ver `kali-exec`.
- `best64.rule` nao esta em `/usr/share/rules/`; o path real e
  `/usr/share/john/rules/best64.rule` (empacotado com o john).

**Use john.** Medido aqui: 76.800 p/s em raw-MD5, ~1s por wordlist pequena.

```
ssh kali-vm 'echo <hash> > ~/work/<alvo>/h.txt
  john --format=Raw-MD5 --wordlist=/usr/share/dirb/wordlists/small.txt ~/work/<alvo>/h.txt
  john --show --format=Raw-MD5 ~/work/<alvo>/h.txt'
```

Detalhe que custa tempo: o `--format` e **case-sensitive** e john sugere o
nome proprio (`--show --format=Raw-MD5`, com R e M maiusculos). `--format=raw-md5`
falha em silencio. `john --list=formats` tem 416 formatos.

Rockyou via john: `sudo gunzip -k /usr/share/wordlists/rockyou.txt.gz` e
`john --format=NT --wordlist=/usr/share/wordlists/rockyou.txt h.txt`.
Modos hashcat equivalentes quando rodar em host com GPU: NTLM `1000`,
NetNTLMv2 `2100`, md5 `0`.

Instalar OpenCL na VM (faca voce, precisa de sudo):
`ssh kali-vm` e `sudo apt install -y pocl-opencl-icd` → `hashcat -I` volta a
responder. Faca isso se a auditoria depender de hashcat; senao john basta.

## Achado vs baseline

Senha quebrada no RockYou = **senha trivial em uso** (critico, com evidencia).
Senha quebrada em 40 min com GPU = senha fraca (media). Nao quebrar = descreva
o custo medido e pare. Isso e um resultado legitimo e reportavel.

## Saida de relatorio

Nunca incluir a senha em claro no relatorio. Use `****` e cite o arquivo de
evidencia protegido. Dado de credencial vazando para o cliente sem canal seguro
e vazamento seu, nao deles.

## Pitfalls

- Speed medido aqui (Vega iGPU, sem OpenCL) **nao** representa a capacidade de um
  atacante com GPU NVIDIA. No relatorio, o numero honesto e "quebrada em X min em
  hardware de atacante classe RTX", nunca o tempo desta VM.
- `hashcat` e `john` sem wordlist valida processam 0 linhas e saem com 0 —
  sucesso vazio, nao falha. Confira contagem de linhas antes de concluir.
- Nunca pegue arquivo de hash de terceiros achado "por acaso" na internet.
