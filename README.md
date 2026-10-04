# Play! Web Station

Um emulador experimental de PlayStation 2 que roda diretamente no navegador usando **Play!.js** e WebAssembly.

## Como usar

1. Abra o site publicado.
2. Clique em **Escolher ISO**.
3. Selecione uma imagem de jogo que você possui ou tem autorização para usar.
4. Aguarde o carregamento e clique no quadro do jogo para capturar os controles.

Também é possível arrastar o arquivo para a área indicada abaixo do quadro.

## Arquivos do emulador

O núcleo web está armazenado no próprio repositório para que o site não dependa de downloads externos:

- `Play.js`
- `Play.wasm`
- `vendor/playjs/`

O deploy estático é configurado em `vercel.json`. O Service Worker mantém os assets do emulador disponíveis para uso posterior.

## Formatos aceitos

ISO, CHD, CSO, ISZ, BIN e ELF.

O arquivo escolhido permanece no navegador e não é enviado para o GitHub ou para um servidor do projeto.

## Limitações

Play!.js é uma versão experimental para navegador. A compatibilidade varia por jogo e navegador; Chrome ou Firefox atualizado é recomendado. O Play!.js usa BIOS HLE integrada e não aceita BIOS externa.

Este projeto **não inclui ISOs, BIOS ou conteúdo protegido por direitos autorais**.

## Licença e origem

Play!.js é um projeto open source. Consulte [`third_party/play/LICENSE.txt`](third_party/play/LICENSE.txt) e [`third_party/play/SOURCE-VERIFICATION.md`](third_party/play/SOURCE-VERIFICATION.md).

Projeto original: [jpd002/Play-](https://github.com/jpd002/Play-).

## Validação dos assets

```bash
sh scripts/verify-play-assets.sh
```
