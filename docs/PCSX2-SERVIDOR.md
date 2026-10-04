# PCSX2 hospedado no servidor

Esta configuração muda o fluxo principal: o PCSX2 roda no servidor e o navegador recebe a sessão gráfica. O computador do usuário não precisa ter PCSX2 instalado.

## Como funciona

O contêiner `lscr.io/linuxserver/pcsx2:latest` mantém o PCSX2 e suas configurações no servidor. A pasta `games/` recebe somente ISOs, CHDs e outros arquivos que você possui ou está autorizado a usar. O navegador acessa a sessão por HTTPS, envia teclado/gamepad e recebe vídeo e áudio.

```text
Navegador → HTTPS/WebSocket → PCSX2 no servidor → /games/arquivo.iso
```

## Inicialização

No servidor que tenha Docker e Docker Compose:

```bash
cd deploy/pcsx2-server
cp .env.example .env
# Edite .env e troque a senha
mkdir -p config games
# Coloque em games somente arquivos autorizados

docker compose up -d
```

Abra `https://SEU_SERVIDOR:3001/` no navegador. A porta 3001 é HTTPS e pode usar um certificado autoassinado na primeira abertura. Faça a configuração inicial do PCSX2 dentro da sessão web, selecione OpenGL ou outra opção suportada explicitamente pelo servidor e escolha os arquivos em `/games`.

Se o servidor Linux tiver uma GPU Intel ou AMD exposta em `/dev/dri`, inicie com o override opcional:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Para Nvidia, use a configuração oficial do runtime Nvidia e os requisitos do host antes de adicionar o contêiner. Não habilite GPU às cegas: confirme primeiro que `/dev/dri` ou o runtime correspondente existe no servidor.

## Segurança

A sessão web dá acesso ao PCSX2 e ao ambiente gráfico do contêiner. Não publique as portas diretamente na Internet sem autenticação, HTTPS válido e um firewall/reverse proxy. A senha do `.env` não deve ser commitada. O projeto inclui apenas `.env.example`, nunca credenciais.

Para acesso público, prefira colocar a porta HTTPS atrás de um domínio e proxy com TLS válido. Para uso doméstico, mantenha a porta limitada à rede privada ou use uma VPN.

## Integração com esta interface

A interface principal continuará contendo a biblioteca local e o Play!.js como fallback. O acesso server-side deve apontar para a URL HTTPS da sessão PCSX2, por exemplo `https://pcsx2.exemplo.com:3001`. Como a interface do contêiner é uma sessão gráfica completa, a primeira versão abre a sessão em uma nova aba; isso evita quebrar WebSocket, áudio, tela cheia e gamepads com um iframe cross-origin.

## Limitações desta sessão

O Sandbox usado para editar este repositório não é um host persistente de PCSX2 e não possui uma GPU dedicada disponível para validar uma sessão real. Por isso, os arquivos de deployment foram validados como configuração, mas a execução do emulador server-side precisa ser feita em um servidor Docker persistente com recursos gráficos adequados.
