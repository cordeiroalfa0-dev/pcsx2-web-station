# PCSX2 Web Station & Bridge 🎮

Interface moderna e servidor Bridge local para conectar o emulador **PCSX2** ao seu navegador e ao app web.

## 🚀 Recursos
- **Launcher Web Moderno**: Catálogo visual estilo Steam/Big Picture com busca instantânea e capas automáticas.
- **API Bridge com CORS**: Permite que o app web (hospedado no Lovable ou local) acione jogos e verifique o status do emulador.
- **Autodetecção do PCSX2**: Suporte a Windows (.exe padrão) e Linux (binário nativo ou Flatpak).
- **Download Integrado**: Suporte a links diretos de ISO (ex: Internet Archive) e integração com Google Drive via .
- **Estatísticas e Saves**: Acompanhamento de tempo de jogo, data de última execução e compatibilidade com cartões de memória.

## 📦 Instalação e Requisitos

1. Certifique-se de ter o **Python 3.8+** instalado.
2. Instale as dependências recomendadas:

*(Nota:  e  são opcionais, mas recomendados para busca de capas e downloads do Drive).*

## 🛠️ Como Executar

Execute o script no terminal ou prompt de comando:


O servidor iniciará em .
- Se você acessar direto pelo navegador no PC, terá a interface local completa.
- Se você estiver usando o app online no Lovable, vá até a aba **Bridge** no app web e configure:
  - **URL do Bridge**: 
  - **Token**: 

## ⚙️ Variáveis de Ambiente & Configurações

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| Porta |  | Porta local do servidor HTTP |
| Token |  | Token de autenticação da API Bridge |
| Diretório de Jogos |  | Pasta onde as ISOs/CHDs são lidas |

---
Criado para uso conjunto com o ecossistema Lovable & PCSX2.
