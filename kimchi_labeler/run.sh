#!/usr/bin/env bash
# 라벨링 프로그램 실행.
#   bash run.sh                        settings.json 에 기억된 RAW 폴더로 실행
#   bash run.sh --raw data/dummy_raw   RAW 폴더를 지정해서 실행 (다음부터 기억됨)
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "먼저 설치를 하세요:  bash setup_wsl.sh"
    exit 1
fi

. .venv/bin/activate

# 새 버전에서 필요한 패키지가 늘었으면 (예: PyYAML) 자동으로 설치한다.
if ! python -c "import tkinter, PIL, yaml" 2>/dev/null; then
    echo "필요한 패키지를 설치합니다..."
    python -m pip install -r requirements.txt -q
fi

python main.py "$@"
