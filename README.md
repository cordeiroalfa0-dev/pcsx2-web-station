# PCSX2 Web Station & Bridge

Launcher web local e Bridge para conectar um site ao emulador **PCSX2** instalado no computador.

## O que foi adicionado

- **Bridge portátil em Node.js**, sem dependências npm.
- Compatível com Windows, Linux e macOS, desde que Node.js 18+ esteja instalado.
- Detecção automática do PCSX2 em caminhos comuns.
- API local compatível com o site: estado, configuração, biblioteca, varredura e inicialização de jogos.
- CORS habilitado para o site Lovable acessar o Bridge local.
- Busca local de jogos e links salvos pelo usuário.
- Página `index.html` com o emulador Play!.js dentro do navegador via WebAssembly.
- Não inclui BIOS, ISOs ou conteúdo protegido por direitos autorais.

## Emulador dentro da página web

Ao publicar este repositório na Vercel, o arquivo `index.html` mostra o **Play!.js** dentro da página. Os arquivos WebAssembly públicos do Play!.js são hospedados localmente em `vendor/playjs/` e os módulos de execução ficam na raiz para o carregamento correto na Vercel. Play!.js é a versão web experimental do projeto open source [Play!](https://github.com/jpd002/Play-), carregada dentro do navegador com WebAssembly.

O emulador aceita ISO, CSO, CHD, ISZ, BIN e ELF. O arquivo do jogo é escolhido pelo usuário no próprio quadro do emulador e não é enviado para este repositório. O Play!.js usa BIOS HLE integrada e não aceita BIOS externa; para usar uma BIOS própria, continue usando o PCSX2 desktop pelo Bridge.

O emulador web é experimental e pode não executar todos os jogos compatíveis com PCSX2. Chrome ou Firefox recente é recomendado. Os arquivos redistribuídos seguem a licença do Play! em `third_party/play/LICENSE.txt`.

## Como iniciar o Bridge portátil

1. Instale [Node.js 18 ou superior](https://nodejs.org/).
2. Baixe o projeto pelo GitHub e extraia o ZIP.
3. Execute um dos arquivos dentro da pasta `bridge/`.

### Windows

Dê duplo clique em:

```text
bridge/run-bridge.bat
```

### Linux ou macOS

```bash
chmod +x bridge/run-bridge.sh
./bridge/run-bridge.sh
```

Também é possível iniciar diretamente:

```bash
cd bridge
node bridge.mjs
```

O Bridge ficará disponível em `http://127.0.0.1:8765`.

## Conectar ao site Lovable

Na aba **Bridge** do site, informe:

| Campo | Valor |
|---|---|
| URL do Bridge | `http://127.0.0.1:8765` |
| Token | `pcsx2-token` |

O token pode ser alterado com `PCSX2_BRIDGE_TOKEN`. A porta pode ser alterada com `PCSX2_BRIDGE_PORT`.

Exemplo no Windows PowerShell:

```powershell
$env:PCSX2_BRIDGE_TOKEN = "meu-token-local"
$env:PCSX2_BRIDGE_PORT = "8765"
node bridge/bridge.mjs
```

## Observações importantes

O Bridge apenas conecta o site ao PCSX2 instalado localmente. O navegador não pode iniciar um `.exe` diretamente. O PCSX2, o BIOS e os jogos continuam sendo executados/fornecidos pelo computador do usuário.

A barra de busca pesquisa a biblioteca local e os links cadastrados em **Links salvos**. Links `http(s)`, `magnet:` e `.torrent` são tratados apenas como marcadores fornecidos pelo usuário; o Bridge Node não pesquisa sites externos nem baixa torrents automaticamente.

## Bridge Python legado

O arquivo `pcsx2_web.py` continua no repositório para compatibilidade com a versão anterior. Para novas instalações, prefira o Bridge Node em `bridge/`, que não exige `pip` nem pacotes Python.

## Licença e conteúdo

Este projeto é distribuído sob a licença MIT. Ele não distribui o PCSX2, BIOS, ISOs, CHDs ou outros arquivos de jogos. Use somente software e conteúdo que você possui ou tem autorização para utilizar.


## Melhorias recentes

- Acesso rápido à pasta pública `isogames` do Google Drive.
- Botão para copiar o link da pasta.
- Área de arrastar e soltar para ISO, CHD, CSO, ISZ, BIN e ELF.
- Validação de extensão antes de carregar o jogo.
- Indicadores de carregamento, privacidade e erro.
- O arquivo continua local no navegador; não há upload automático.

A listagem automática dos arquivos do Google Drive ainda depende da Google Drive API. Sem uma API key, o botão abre a pasta pública para o usuário selecionar o arquivo manualmente.
