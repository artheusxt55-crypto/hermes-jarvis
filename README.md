# JARVIS — skills e identidade

Repositório próprio de skills e personalidade do JARVIS, construído sobre o
Hermes Agent. Separado das 64 skills que vêm com o Hermes (`skills.external_dirs`),
então dá pra versionar, revisar e portar pra outra máquina com um clone.

## Layout

```
skills/          suas skills — cada uma numa pasta com SKILL.md
SOUL.md          personalidade do JARVIS (prompt base, lido em toda sessão)
```

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