# security — auditoria e pentest

Fluxo de trabalho, na ordem em que as skills se chamam:

```
pentest-authorization-gate   <- sempre primeiro, sem excecao
        |
        v
kali-exec                    <- como rodar qualquer tool (ssh, sudo, paths)
        |
   +----+----+----+
   |         |    |
   v         v    v
recon-      enum-  enum-
externo-    rede-  web-
osint       servicos diretorios
   |         |    |
   +----+----+----+
        v
   vuln-scan-web-tls      enum-ad-smb     cred-analise-hashes
        |                  |                    |
        +------------------+--------------------+
                           v
                  relatorio-pentest
```

Todas as skills nesta pasta foram smoke-testadas contra a VM Kali real em
2026-10-04. Os caminhos, flags e limitacoes documentados sao os observados
naquele dia — `kali-exec` e o verbete que registra o que diverge.
