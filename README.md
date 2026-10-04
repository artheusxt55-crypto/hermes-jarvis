# JARVIS — skills e identidade

Repositório próprio de skills e personalidade do JARVIS, construído sobre o
Hermes Agent. Separado das 64 skills que vêm com o Hermes (`skills.external_dirs`),
então dá pra versionar, revisar e portar pra outra máquina com um clone.

## Layout

```
skills/          suas skills — cada uma numa pasta com SKILL.md
  security/      auditoria e pentest (fluxo próprio, ver skills/security/WORKFLOW.md)
references/      inventário real das ferramentas da VM Kali
SOUL.md          personalidade do JARVIS (prompt base, lido em toda sessão)
```

## Auditoria de segurança

`skills/security/` é o conjunto de skills de pentest. Todas foram smoke-testadas
contra a VM Kali real (2890 pacotes, `ssh kali-vm`) em 2026-10-04 — os paths,
flags e limitações documentados são os observados, não os da documentação upstream.

```
pentest-authorization-gate   sempre primeiro: confirma alvo e autorização
kali-exec                    como rodar qualquer tool (ssh, sudo, paths)
recon-externo-osint          subdomínios, DNS, superfície externa
enum-rede-servicos           nmap/masscan, portas, scripts por família
enum-web-diretorios          ffuf/gobuster/dirb, vhosts, parâmetros
vuln-scan-web-tls            nuclei, nikto, sslscan/openssl
enum-ad-smb                  SMB, LDAP, shares, Kerberos SPN
cred-analise-hashes          john/hashcat, força de senha, wordlists
relatorio-pentest            severidade, evidência, relatório
```

`references/kali-inventory.txt` é a fonte de verdade do que existe na VM.
Antes de documentar uma ferramenta, confirme nela — o conjunto instalado, a
versão e os flags mudam entre imagens do Kali.

Três coisas quebradas nesta VM, registradas em `kali-exec`: `sudo` pede senha
(nada de `apt install` remoto), `hashcat` não roda (sem OpenCL — use `john`), e
`amass` é um wrapper que chama `sudo` (use `/usr/lib/amass/amass`).

## Como o Hermes descobre isto

Duas chaves no `~/.hermes/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/Documents/hermes-jarvis/skills   # lê daqui, além das upstream
  create_dir: ~/Documents/hermes-jarvis/skills   # onde o skill_manage cria
```

`external_dirs` só soma: as 64 skills upstream continuam disponíveis, estas
entram por cima. Para desligar as upstream e usar só as suas, desabilite por
nome em `skills.disabled`.

## Uso

Criar skill nova: peça ao Hermes em conversa, ou escreva `SKILL.md` à mão.
Instalar em outra máquina: clone este repo e aponte `external_dirs` para ele.

Personalidade: editar `SOUL.md` e abrir nova sessão. Vem no system prompt.