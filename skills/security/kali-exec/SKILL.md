---
name: kali-exec
description: Use to run any Kali tool on the Kali VM over SSH. Base layer.
version: 1.0.0
metadata:
  hermes:
    tags: [kali, ssh, exec, pentest]
---

# Executando ferramentas Kali

Toda ferramenta Kali roda na VM, nunca neste host Windows. Este e o verbete base:
qualquer outra skill de pentest herda daqui.

## Regra

Comandos nao interativos sao feitos por `ssh kali-vm "<cmd>"` a partir do host
Windows. Alias `kali-vm` ja esta em `~/.ssh/config` (porta 2222, usuario kali,
chave `id_ed25519`). **Nunca** usar `ssh -p 2222` em script.

## Padrao de execucao segura

```
ssh kali-vm "<comando>"            # stdout direto, termina
ssh kali-vm "<cmd> 2>&1 | tail -50"
```

Para comando longo ou interativo (msfconsole, wireshark, gdb, burp): usar PTY via
o `terminal` do host com `ssh -tt kali-vm`, e mandar Enter com CR, nunca `\n`
solto. Sesao precisa sobreviver entre turnos -> subir com
`ssh -f -N kali-vm` e usar `ssh -S` socket, ou `tmux new -d -s nome` **dentro**
da VM (preferido: `ssh kali-vm "tmux new -d -s pentest"` / `tmux attach -t pentest`).

## Onde ficam as saidas

Trabalhe num diretorio de trabalho por alvo, dentro da VM, para nao sujar o host:

```
ssh kali-vm "mkdir -p ~/work/<alvo> && echo ~/work/<alvo>"
```

Toda evidencia vai para `~/work/<alvo>/` com nome `.txt` e data. Trazer de volta
so o necessario com `scp` — nunca `cat` de arquivo binario no terminal.

## Inventario real da VM

`references/kali-inventory.txt` (na raiz do repo, 2890 pacotes com versao) e a
fonte de verdade do que existe. Antes de recomendar uma ferramenta, verifique
nela. Estado em 2026-10-04:

Presentes e usaveis: nmap, masscan, nikto, nuclei, sqlmap, whatweb, sslscan,
tshark, tcpdump, wireshark, ffuf, gobuster, dirbuster, wfuzz, amass, dnsrecon,
fierce, dnsenum, enum4linux, smbclient, rpcclient, smbmap, netexec, evil-winrm,
responder, impacket-scripts, msfconsole, msfvenom, searchsploit, john, hashcat,
hydra, medusa, crunch, radare2, binwalk, exiftool, nc, netcat.

Ausentes (nao prometer): subfinder, ghidra, gdb, foremost, steghide,
zaproxy, crackmapexec (usar `netexec`), testssl.sh, gitleaks.

### sudo NAO e passwordless nesta VM

`ssh kali-vm "sudo -n true"` → `sudo: a password is required`. Consequencias
praticas, todas ja_sendas durante a construcao das skills:

- Nao da para `apt install`, `gunzip` de rockyou, nem criar regra de sudo
  remotamente. O usuario precisa rodar o `sudo` no terminal dele (ou
  `ssh -tt` + `process(submit)` com a senha na UI). **Nao tente contornar**:
  piped `sudo -S` por stdin e justamente o vetor de ataque que a tool bloqueia.
- `amass` e o caso mais visivel: `/usr/bin/amass` e um wrapper que chama
  `sudo libpostal_data download` antes de rodar. Sem sudo, **todo `amass` falha**.
  Use `/usr/lib/amass/amass` direto (ver `recon-externo-osint`).

Para instalar tool faltando: peça ao usuario para rodar
`ssh kali-vm "sudo apt install -y <pkg>"`. Confirme depois com
`command -v <tool>`.

## Pitfalls

- **Aspas: a ordem importa.** `ssh kali-vm "awk '{print $1}' f"` expande `$1` no
  shell **local** e quebra com `syntax error`. Use aspas simples no remote:
  `ssh kali-vm 'awk '{print $1}' f'`. Para inventariar pacotes:
  `ssh kali-vm 'dpkg-query -W -f=${Package} | sort -u'` (2890 pacotes aqui).
- **`$(...)` tambem expande localmente.** `ssh kali-vm "ls $(command -v amass)"`
  lista o home **local**. Todo `$(...)` precisa ficar dentro das aspas simples
  do remote, ou ser escapado.
- `zsh` e o shell da VM (usuario kali) e `===` sem espaco em volta vira comando
  inexistente. Use `echo ---` como separador.
- Amass 5.1.1: `-passive` e deprecated (passivo e o default) e `-o` nao existe;
  saida vai para stdout ou `-df <arquivo>`.
- Ferramenta Kali em Windows: nunca tentar rodar `nmap.exe` daqui. A VM existe
  exatamente para isso.
- Saida longa estoura o contexto: sempre `| head`/`| tail` no comando remoto e
  leia o arquivo remoto com `ssh kali-vm "grep ... ~/work/<alvo>/x.txt"`.
