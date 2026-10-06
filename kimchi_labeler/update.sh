#!/usr/bin/env bash
# 새 버전 zip 으로 업데이트한다. 내 작업 데이터와 팀이 쓴 문서는 지키고 코드만 바꾼다.
#   bash update.sh                         다운로드 폴더의 가장 최근 kimchi_labeler*.zip 사용
#   bash update.sh /경로/kimchi_labeler.zip
set -e
cd "$(dirname "$0")"
HERE="$(pwd)"

ZIP="${1:-$(ls -t /mnt/c/Users/*/Downloads/kimchi_labeler*.zip 2>/dev/null | head -1)}"
if [ -z "$ZIP" ] || [ ! -f "$ZIP" ]; then
    echo "zip 파일을 찾지 못했습니다. 다운로드 폴더에 kimchi_labeler.zip 을 받았는지 확인하세요."
    exit 1
fi
echo "사용할 zip: $ZIP"

TMP="$(mktemp -d)"
python3 -m zipfile -e "$ZIP" "$TMP"
NEW="$TMP/kimchi_labeler"

# 1) 코드: 항상 새 버전으로 덮어쓴다 (src 는 폴더 구성이 바뀔 수 있어 통째로 교체)
rm -rf "$HERE/src"
for item in src scripts tests configs main.py run.sh setup_wsl.sh requirements.txt settings.example.json .gitignore; do
    [ -e "$NEW/$item" ] && cp -r "$NEW/$item" "$HERE/"
done

# 2) 문서·보고서: 없는 파일만 새로 넣는다 (팀이 고친 파일은 그대로)
for dir in docs reports manifests; do
    mkdir -p "$HERE/$dir"
    cp -rn "$NEW/$dir/." "$HERE/$dir/" 2>/dev/null || true
done
if [ ! -f "$HERE/README.md" ]; then
    cp "$NEW/README.md" "$HERE/"
elif ! cmp -s "$NEW/README.md" "$HERE/README.md"; then
    cp "$NEW/README.md" "$HERE/README.new.md"
    README_MSG=1
fi

# 3) 예전 이름의 보고서를 산출물 이름으로 옮긴다
if [ -f "$HERE/reports/QA_Summary.md" ] && [ ! -f "$HERE/reports/qa_summary.md" ]; then
    mv "$HERE/reports/QA_Summary.md" "$HERE/reports/qa_summary.md"
fi
if [ -f "$HERE/reports/Handoff_교과8.md" ]; then
    mv "$HERE/reports/Handoff_교과8.md" "$HERE/docs/subject08_handoff_old.md"
fi

# 이 스크립트 자신은 실행 중이므로 덮어쓰지 않고 새 파일로 바꿔 끼운다
cp "$NEW/update.sh" "$HERE/.update.sh.new" && mv -f "$HERE/.update.sh.new" "$HERE/update.sh"

rm -rf "$TMP"

# 4) 새로 필요한 패키지 설치 (예: PyYAML)
if [ -d .venv ]; then
    . .venv/bin/activate
    python -m pip install -r requirements.txt -q
    python tests/test_core.py
fi

echo
echo "업데이트 완료. 실행: bash run.sh"
if [ -n "$README_MSG" ]; then
    echo "새 README 는 README.new.md 로 저장했습니다. 팀이 README 를 고친 적이 없다면:  mv README.new.md README.md"
fi
