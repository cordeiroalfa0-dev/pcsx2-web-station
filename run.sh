#!/usr/bin/env bash
echo "Iniciando PCSX2 Web Station..."
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python 3 não encontrado. Instale o Python para continuar."
    exit 1
fi
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
clear
echo "========================================================"
echo "  PCSX2 Web Station & Bridge rodando com sucesso!"
echo "  Acesse no navegador: http://127.0.0.1:8765"
echo "  Token padrão: pcsx2-token"
echo "========================================================"
python3 pcsx2_web.py
