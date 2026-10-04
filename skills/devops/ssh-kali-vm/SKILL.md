---
name: ssh-kali-vm
description: Use to SSH from this Windows host into the Kali VM.
---

# Conectando no Kali VM a partir do Windows

A VM `kali-linux-2026.2-virtualbox-amd64` roda em **NAT**, entao nunca aparece
na varredura da LAN 192.168.1.0/24. Sem encaminhamento de porta, nao ha como
alcanca-la. IP interno dela e `10.0.2.15` (so alcancavel de dentro do NAT).

## 1. Garantir o encaminhamento NAT (a VM pode estar ligada)

```
cd "C:/Program Files/Oracle/VirtualBox"
./VBoxManage.exe list runningvms
./VBoxManage.exe controlvm kali-linux-2026.2-virtualbox-amd64 natpf1 "ssh,tcp,127.0.0.1,2222,,22"
```

Erros previsiveis:
- `Missing or invalid argument to 'natpf1'` ao passar `add` como argumento
  separado — a sintaxe aceita e `natpf1 "nome,proto,hostip,hostport,,guestport"`.
- A regra nao aparece em `showvminfo` se a VM estiver desligada; nesse caso
  usar `VBoxManage modifyvm <vm> --natpf1 "..."`.
- Para remover: `natpf1 delete <rulename>`.

## 2. Descobrir o IP interno (so util para diagnostico)

```
./VBoxManage.exe guestproperty enumerate   # vazio se Guest Additions nao instalada
```
Sem Guest Additions o unico metodo e ler o banner SSH em 127.0.0.1:2222.

## 3. Conectar

Credenciais: `kali` / `kali` (padrao da imagem Kali — trocar em uso real).
Alias ja gravado em `~/.ssh/config` deste host:

```
Host kali-vm
    HostName 127.0.0.1
    Port 2222
    User kali
    IdentityFile ~/.ssh/id_ed25519
```

Entao basta `ssh kali-vm` ou `ssh kali-vm "comando"` para execucao nao
interativa. **Nunca** usar `ssh -p 2222` sem o alias em script.

## 4. Chave publica instalada (feito em 2026-10-04)

Copiar a chave deste host para a VM habilita login sem senha:
`echo "$(cat id_ed25519.pub)" >> ~/.ssh/authorized_keys` — feito, mas se a VM
for recriada/resetada o passo precisa ser repetido.

## Pitfalls ja vistos

- Varredura de portas na LAN nao acha a VM (e NAT). Nao concluir "Linux
  inacessivel" a partir disso.
- `ssh -tt` em PTY: a senha precisa ser enviada com `process(action='submit')`,
  nunca `write` com `\n` solto (o Enter do PTY Windows e CR).
- `VBoxManage.exe` e programa nativo: passar caminho com barras normais,
  `C:/Program Files/...`, nunca `/c/...`.