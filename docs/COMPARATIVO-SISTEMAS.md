# Comparativo de sistemas semelhantes

A análise foi feita antes das alterações desta versão e comparou projetos open source publicados no GitHub com foco em frontend web, biblioteca local e lançamento de emuladores.

## Referências analisadas

### EmulatorJS

[EmulatorJS](https://github.com/EmulatorJS/EmulatorJS) é um frontend web auto-hospedado para RetroArch. O projeto separa o frontend dos cores, documenta versões estáveis e oferece configuração para integração por CDN. A principal lição aplicável aqui é manter o frontend responsável pela experiência de uso e deixar o núcleo do emulador isolado.

### RomM

[RomM](https://github.com/rommapp/romm) é um gerenciador auto-hospedado de bibliotecas. O projeto combina varredura, metadados, pesquisa e reprodução. Para este projeto, adotamos a parte que não exige serviços externos: biblioteca local pesquisável, favoritos e ordenação por uso recente.

### RomM Desktop

[RomM Desktop](https://github.com/rommapp/romm-desktop) carrega a interface web existente e acrescenta uma ponte para abrir o jogo em um emulador instalado localmente. A arquitetura confirma a decisão deste repositório de usar um Bridge local em vez de tentar iniciar um executável diretamente pelo navegador.

### linuxserver/docker-pcsx2

[linuxserver/docker-pcsx2](https://github.com/linuxserver/docker-pcsx2) oferece PCSX2 acessível pelo navegador por meio de uma sessão gráfica remota. A documentação destaca que a configuração de OpenGL precisa ser explícita, que a GPU montada pode acelerar a renderização e que a interface não deve ser exposta à Internet sem autenticação. Como este projeto é local, mantivemos o Bridge em `127.0.0.1` e o diagnóstico WebGL no navegador, sem transformar o PCSX2 em um serviço público.

## Melhorias adotadas

- Busca instantânea por nome ou caminho na biblioteca local.
- Favoritos persistentes no navegador.
- Ordenação com favoritos primeiro, depois jogos usados recentemente.
- Proteção contra inserção de nomes e caminhos da biblioteca diretamente como HTML.
- Interface mais adequada para gamepad e abertura rápida.
- Mantida a abertura local pelo PCSX2, sem pesquisa ou download de jogos de terceiros.

## O que não foi copiado

Não foram adicionados downloaders de ISOs, indexadores de torrents, scraping de Google Drive ou qualquer recurso para localizar jogos sem autorização. A biblioteca continua limitada aos arquivos existentes no computador do usuário e aos links que ele próprio cadastrar.

## Validação do repositório do usuário

Antes da implementação, a branch `main` publicada em `cordeiroalfa0-dev/pcsx2-web-station` foi consultada diretamente pela API do GitHub e confirmou o commit `57e61904be1669dc78ea7b2ad816a140db916556`, correspondente ao commit local. Não havia alterações locais pendentes naquele momento.
