# Play! — proveniência dos arquivos incorporados

Este diretório contém arquivos do projeto open source **Play!**, usado como núcleo experimental de emulação PS2 no navegador.

## Fontes oficiais

- Repositório: https://github.com/jpd002/play-
- Site da versão web: https://playjs.purei.org/
- Commit upstream consultado: `83700b2c31e593bc94e845b4b31b797be84dda59`
- Licença: [`LICENSE.txt`](./LICENSE.txt)

## Arquivos incorporados

Os arquivos abaixo foram obtidos da versão web pública oficial em 2026-10-04 e são servidos localmente pela aplicação:

| Arquivo | SHA-256 |
|---|---|
| `Play.js` | `5599ff16ae5e3534f9b779736aedfa20661821d57be7f03e587e31ef8d090317` |
| `Play.wasm` | `5c6ace637a23f3416a8105d1a07786631994e8dfe34d603a9f62c3b47c47f1a2` |
| `vendor/playjs/main.js` | `a1e02dc43527f92cfc8bc99831027647053ddfe64f903b5a9b746cefaac04180` |
| `vendor/playjs/main.css` | `105036c0e8a13b39a811506e499363c0bea1aa2325a0104b237bd9a9d8cafeb8` |

## Verificação local

Linux/macOS:

```bash
./scripts/verify-play-assets.sh
```

Windows PowerShell:

```powershell
(Get-FileHash .\Play.js -Algorithm SHA256).Hash
(Get-FileHash .\Play.wasm -Algorithm SHA256).Hash
```

A verificação confirma a integridade dos arquivos distribuídos pelo repositório. Ela não garante que todos os jogos sejam compatíveis; Play!.js continua sendo uma versão experimental.
