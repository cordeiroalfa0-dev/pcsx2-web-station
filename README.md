# PCSX2 Web Station & Bridge

Launcher web local e Bridge para conectar um site ao emulador **PCSX2** instalado no computador.

## O que foi adicionado

- **Bridge portátil em Node.js**, sem dependências npm.
- Compatível com Windows, Linux e macOS, desde que Node.js 18+ esteja instalado.
- Detecção automática do PCSX2 em caminhos comuns.
- API local compatível com o site: estado, configuração, biblioteca, varredura e inicialização de jogos.
- Abertura direta de uma ISO pelo PCSX2 com a sintaxe oficial `-batch -fullscreen -- caminho-da-iso`.
- Validação de extensão, existência e tipo de arquivo antes de iniciar o PCSX2.
- Retorno de erro quando o executável do PCSX2 não consegue iniciar.
- Interface no próprio `index.html` para testar o Bridge, escanear uma pasta e abrir ISO no PC.
- Assistente web de desempenho com diagnóstico de WebGL/WebGPU, perfil de desempenho/qualidade, tela cheia, gamepad e Wake Lock.
- CORS habilitado para o site acessar o Bridge local.
- Busca local de jogos e links salvos pelo usuário.
- Página `index.html` com o emulador open source Play!.js dentro do navegador via WebAssembly.
- Créditos e licença do núcleo Play! visíveis na interface.
- PWA instalável com cache local dos assets WebAssembly.
- Busca direta no tracker oficial de compatibilidade do Play! no GitHub.
- Não inclui BIOS, ISOs ou conteúdo protegido por direitos autorais.

## Abrir ISO no PCSX2 instalado no seu PC

1. Instale o PCSX2 e faça a configuração inicial, incluindo a BIOS que você possui legitimamente.
2. Instale o Node.js 18 ou superior.
3. Inicie o Bridge:

### Windows

Dê duplo clique em `bridge/run-bridge.bat`.

### Linux ou macOS

```bash
chmod +x bridge/run-bridge.sh
./bridge/run-bridge.sh
```

4. Abra o site no navegador **no mesmo computador** e, na seção **Abrir ISO no PCSX2 deste PC**, clique em **Testar conexão**.
5. Informe o caminho completo da ISO no computador, por exemplo:

```text
Windows: C:\Jogos\meu-jogo.iso
Linux: /home/seu-usuario/Jogos/meu-jogo.iso
macOS: /Users/seu-usuario/Jogos/meu-jogo.iso
```

6. Clique em **Abrir ISO no PCSX2**. O Bridge executará o PCSX2 com a ISO indicada.

O Bridge ficará disponível em `http://127.0.0.1:8765` e usa o token padrão `pcsx2-token`. Se você alterar `PCSX2_BRIDGE_TOKEN`, use o mesmo token na aplicação. A porta pode ser alterada com `PCSX2_BRIDGE_PORT`.

> Importante: um navegador comum não revela o caminho real de um arquivo local selecionado em `<input type="file">`. Por isso, para abrir o arquivo no PCSX2 desktop, informe o caminho local completo ou escaneie a pasta onde as suas ISOs estão armazenadas. O arquivo nunca é enviado ao servidor.

## Sintaxe oficial usada

O Bridge usa a sintaxe documentada pelo PCSX2:

```text
pcsx2-qt.exe -batch -fullscreen -- "C:\Jogos\meu-jogo.iso"
```

`--` informa ao PCSX2 que o argumento seguinte é o arquivo de boot, inclusive quando o caminho contém espaços.

## Emulador dentro da página web

Ao publicar este repositório na Vercel, o arquivo `index.html` mostra o **Play!.js** dentro da página. Os arquivos WebAssembly públicos do Play!.js são hospedados localmente em `vendor/playjs/` e os módulos de execução ficam na raiz para o carregamento correto na Vercel. Play!.js é a versão web experimental do projeto open source [Play!](https://github.com/jpd002/Play-), carregada dentro do navegador com WebAssembly.

O emulador aceita ISO, CSO, CHD, ISZ, BIN e ELF. O arquivo do jogo é escolhido pelo usuário no próprio quadro do emulador e não é enviado para este repositório. O Play!.js usa BIOS HLE integrada e não aceita BIOS externa; para usar uma BIOS própria, continue usando o PCSX2 desktop pelo Bridge.

O emulador web é experimental e pode não executar todos os jogos compatíveis com PCSX2. Chrome ou Firefox recente é recomendado. Os arquivos redistribuídos seguem a licença do Play! em `third_party/play/LICENSE.txt`.

## Assistente para jogos exigentes

Na seção **Assistente de desempenho**, a página:

- verifica se WebGL está disponível e sinaliza quando o navegador aparenta estar usando renderização por software;
- detecta WebGPU quando o navegador oferece essa API;
- oferece o perfil **Desempenho**, que reduz efeitos da interface e usa filtragem pixelada, ou **Qualidade**, que mantém a imagem suave;
- entra em tela cheia após a primeira interação permitida pelo navegador e também oferece o botão manual;
- detecta gamepads conectados e orienta o foco no quadro do jogo;
- pode manter a tela acordada durante a sessão usando Wake Lock.

Esses recursos ajudam o navegador, mas não substituem uma GPU. Se o diagnóstico indicar WebGL por software ou se o jogo exigir mais desempenho, use o botão **Abrir ISO no PCSX2** para executar o PCSX2 desktop, que tem acesso direto à placa de vídeo e às configurações de GPU do computador.

## Desenvolvimento e validação

```bash
node --check bridge/bridge.mjs
npm --prefix bridge start
```

O comparativo das soluções open source analisadas e os critérios adotados está em [`docs/COMPARATIVO-SISTEMAS.md`](docs/COMPARATIVO-SISTEMAS.md).

O projeto não inclui PCSX2, BIOS, ISOs, CHDs ou outros arquivos de jogos. Use somente software e conteúdo que você possui ou tem autorização para utilizar.
