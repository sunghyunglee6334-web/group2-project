#!/usr/bin/env bash
# WSL(Ubuntu)에서 처음 한 번만 실행한다.
#   bash setup_wsl.sh
# 필요한 프로그램 설치 -> 가상환경(.venv) -> 패키지 -> 연습용 데이터 -> 자동 테스트
set -e
cd "$(dirname "$0")"

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

echo "[1/5] 시스템 패키지 설치 (WSL 비밀번호를 물어보면 입력하세요. 글자는 안 보이는 게 정상)"
$SUDO apt-get update -y
$SUDO apt-get install -y python3 python3-venv python3-pip python3-tk fonts-nanum fonts-noto-cjk
fc-cache -f > /dev/null 2>&1 || true

echo "[2/5] Python 버전 확인 (3.9 이상 필요)"
python3 - <<'EOF'
import sys
if sys.version_info < (3, 9):
    sys.exit(f"Python {sys.version.split()[0]} 입니다. 3.9 이상이 필요합니다 (Ubuntu 22.04 이상 권장).")
print("  Python", sys.version.split()[0])
EOF

echo "[3/5] 가상환경(.venv) 만들기와 패키지 설치"
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
. .venv/bin/activate
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
python -c "import tkinter, PIL, numpy, yaml; print('  tkinter, Pillow, numpy, PyYAML OK')"

echo "[4/5] 연습용 가짜 데이터 (data/dummy_raw)"
if [ ! -d data/dummy_raw ]; then
    python scripts/make_dummy_data.py
else
    echo "  이미 있음 - 건너뜀"
fi

echo "[5/5] 자동 테스트"
python tests/test_core.py

echo
echo "설치 완료."
echo "  연습 데이터로 실행 : bash run.sh --raw data/dummy_raw"
echo "  다음부터는         : bash run.sh"
echo "창 제목줄 한글이 네모로 보이면 Windows PowerShell 에서 'wsl --shutdown' 후 다시 여세요."
