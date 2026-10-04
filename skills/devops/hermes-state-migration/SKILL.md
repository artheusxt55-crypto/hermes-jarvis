---
name: hermes-state-migration
description: Use to port a Hermes install or session to another host.
version: 1.0.0
author: curator
license: MIT
metadata:
  hermes:
    tags: [hermes, migration, state.db, auth, vagrant, ssh]
    related_skills: [ssh-kali-vm, hermes-agent]
---

# Migrando instalacao e sessao do Hermes entre maquinas

Cobre levar um Hermes Agent para outro host (VM, container, outra maquina) de
forma que a sessao existente continue legivel la. Quando a outra maquina e
alcancavel por SSH, ver `ssh-kali-vm` para o tunel/encaminhamento de porta.

## Quando usar

O usuario diz "quero que voce funcione la tambem", "manda essa sessao pro
Linux", "roda o Hermes dentro da VM".

## Regra de ouro: executar, nao oferecer menu

Pedido de migracao e pedido de **execucao**, nao de opcoes. O caminho tecnico
existe e tem Steps; apresente alternativas, trade-offs de armazenamento e
"talvez seja melhor voce rodar manualmente" antes de ter executado e verificado
que funciona — e o modo de perder o pedido. Justifique os trade-offs *depois*,
em uma linha, com o trabalho ja feito.

Excecao: quando a acao for destrutiva e nao reversivel, ou quando houver uma
decisao de arquitetura que o usuario de fato precisa tomar, pergunte antes.

## Steps, nesta ordem

1. **Instalar o Hermes no host de destino.** O `install.sh` oficial e
   suficiente; precisa so de rede + git + toolchain de compilacao.
   ```
   ssh HOST "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
   ssh HOST "~/.local/bin/hermes --version"   # verificar, nao assumir
   ```
   Pode levar varios minutos. Se houver outras coisas a fazer no caminho, rode
   em background com `notify_on_complete` e siga.

2. **Transferir `auth.json`** — e onde vive a autenticacao da maioria dos
   providers. Confira antes o formato: em provedores com login OAuth (ex.
   Nous Portal) o arquivo traz `access_token` / `refresh_token` / `agent_key`
   e **nao existe chave `sk-...`**. O `.env` do host novo, recem-instalado, vem
   com dezenas de linhas comentadas de placeholders — isso nao e "credencial
   faltando" no sentido de bug, e apenas template.
   ```
   scp -P PORTA "$HERMES_HOME/auth.json" usuario@host:~/.hermes/auth.json
   ```
   Cuidado operacional: copiar `auth.json` faz o mesmo token existir em dois
   hosts; rotacionar o credencial no provider desconecta ambos. Refazer login
   OAuth no destino (`hermes setup`) e a alternativa mais limpa.

3. **Alinhar `config.yaml` — o passo que mais se esquece.** O host novo fica
   com o `model.default` de fabrica, que aponta para um provider cujas credenciais
   nao existem la. Sintoma: o portal responde "no active subscription or usable
   credits" **mesmo com o `auth.json` correto** — e a causa e modelo errado, nao
   saldo. Nao leia esse erro como problema de credencial.
   ```
   ssh HOST "hermes config set model.default '<modelo do host de origem>'"
   ssh HOST "hermes config set model.provider <provider>"
   ```
   Ao trocar o provider, a ferramenta pode limpar um `base_url` herdado que
   pertencia ao provider anterior; deixar por padrao, e so redefinir se a
   mensagem indicar que o endpoint era intencional.

4. **Transferir o `state.db` — via `VACUUM INTO`, nunca `scp` cru.** Copiar o
   arquivo enquanto o WAL ativo existe entrega banco malformado no destino
   ("database disk image is malformed"). Gere uma copia consolidada:
   ```python
   c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
   c.execute("VACUUM INTO ?", (destino,))
   ```
   Apague `state.db-wal` e `state.db-shm` no destino antes de testar. Valide com
   `PRAGMA integrity_check` **no destino** e confira a contagem de `sessions` /
   `messages` — e o que prova que a copia valeu.

5. **Copiar `memories/MEMORY.md` e `memories/USER.md`** para `~/.hermes/memories/`.
   Sem isso o agente no destino funciona mas perde todo o contexto acumulado.

6. **Matar processos Hermes orfaos no destino** antes de testar. Ver
   `references/session-store.md` — processo pendurado segura o banco e faz a
   retomada falhar.

7. **Verificar retomando a sessao de verdade** e perguntar algo cujo resposta
   so existe no transcript (ex.: qual foi o primeiro comando executado na
   sessao). Se responder corretamente, a migracao funcionou — nao afirme antes
   de ter essa prova.

## Concorrencia: uma sessao, um processo

Duas instancias do Hermes na **mesma** sessao nao sao "a mesma sessao
compartilhada": cada uma tem seu proprio estado em disco e ambas disputam o
lock, resultando em "Still waiting for the other Hermes process on this
session". Sem sincronizacao, o lado que escrever por ultimo sobrescreve o outro.

Se o destino e um host ao qual ainda se tem sessao aberta, avisar que as duas
nao podem ficar ativas ao mesmo tempo e deixar o usuario escolher qual encerra.
Nao vender "sessao compartilhada" — o que existe e copia divergente.

## O que fazer

- Perguntar o que quer migrar e executar Steps 1-7.
- Dizer no fim, em uma frase, o que ficou para tras: historico vai junto,
  arquivos de trabalho nao; credencial copiada e revogavel em um lugar so.