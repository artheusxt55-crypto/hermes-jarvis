---
name: recon-web-basico
description: Use when reconning or enumerating a web target.
version: 1.0.0
author: user
license: MIT
metadata:
  hermes:
    tags: [pentest, recon, web, nmap]
    related_skills: []
---

# Recon web básico

## When to Use

- O usuário pede para reconocer, enumerar ou mapear um alvo web, domínio,
  subdomínio, porta ou stack de tecnologia.
- O usuário pede "o que esse host roda", "descobre os serviços", "enumera
  diretórios".

NÃO use para: varredura de rede genérica, exploiting, ou quando o usuário só
está pedindo explicação conceitual de ferramenta.

Procedimento de reconhecimento web. Só execute contra alvos que o usuário
explicitamente declarou como seus ou autorizados. Se o alvo não for
identificado, peça o escopo antes de rodar qualquer comando de rede.

## Escopo primeiro

Antes de qualquer scan, confirme: alvo, e se há autorização. Registre em
`/tmp/recon-scope.txt` o que foi pedido. Se o usuário não disser, pergunte —
não assuma que um IP ou domínio é dele.

## Passos

1. **Resolução e portas.** `nmap -sV -Pn -p- --top-ports 1000 <alvo>`
   Comece com `--top-ports`. Varredura completa de porta é lenta e ruidosa;
   só justifique removendo o filtro se o usuário pedir cobertura total.

2. **Serviços web.** Extraia da saída do nmap quais portas são http/https.
   Para cada uma, `curl -sSI <url>` para capturar headers e seguir redirects.

3. **Tecnologias.** Olhe `Server`, `X-Powered-By`, `Set-Cookie` nos headers.
   Um `Set-Cookie` com `PHPSESSID` ou `JSESSIONID` identifica a stack sem
   precisar de ferramenta extra.

4. **Enumeração de diretórios só com wordlist pequena.** `ffuf` ou `gobuster`
   contra `common.txt`. Nunca wordlist gigante sem o usuário pedir — é ruído
   e tempo.

5. **Resumo em tabela.** Alvo, porta, serviço, versão, header relevante, e uma
   coluna de "observação" com o que for acionável. Sem interpretação
   especulativa: se não viu, não escreve.

## Regras

- Nunca diga que um achado é explorável sem evidência da resposta.
- Versão antiga não é vulnerabilidade. Se não checou a CVE, diz "versão X, não
  verificada".
- Salva a saída bruta em `/tmp/recon-<alvo>.txt` antes de resumir, e cita o
  caminho. Resumo sem o bruto é opinião.
- Escaneia um alvo por vez. Alvo em lote só com pedido explícito.
