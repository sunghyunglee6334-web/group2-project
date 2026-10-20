"""13b_evaluate_final_test_eval74.py — 같은 Final Model 로 Frozen Test 를 eval_exclude 제외 74장 기준으로도 기록한다.

이유: docs/split_policy.md (10/15, Test 평가 전 결정)에서 애매한 라벨 사진은 평가에서 빼기로 했지만,
      13_evaluate_final_test.py 는 test 폴더 75장 전체로 평가했다.
      → 75장 결과(final_metrics.csv)는 그대로 두고, 74장 결과를 따로 남긴다.
모델 · imgsz · conf 는 13 과 완전히 같다 (튜닝 아님). test 폴더의 사진은 옮기거나 지우지 않는다.

실행 (project8 폴더에서):
    python scripts/13b_evaluate_final_test_eval74.py

출력: reports/final_metrics_eval74.csv          전체 P · R · mAP50 · mAP50-95
      reports/final_class_metrics_eval74.csv    Class별
      runs/final_test_eval74/                   Ultralytics 결과 · 74장 목록 (Git 제외)
"""
import csv
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluate_detector import (  # noqa: E402
    evaluate_detector,
    save_metrics_csv,
    summarize_overall,
    summarize_per_class,
)
from src.project_config import DATASET_VERSION, DATASET_YAML, MODEL_DIR, REPORT_DIR, RUNS_DIR  # noqa: E402

FINAL_WEIGHT = MODEL_DIR / 'final' / 'final_best.pt'
FINAL_SOURCE = 'exp003'
FINAL_MODEL = 'yolo11n.pt'
FINAL_IMGSZ = 1280                                   # 13 과 같게
TEST_MANIFEST = PROJECT_ROOT / 'manifests' / 'test.csv'
OUT_METRICS = REPORT_DIR / 'final_metrics_eval74.csv'
OUT_CLASS = REPORT_DIR / 'final_class_metrics_eval74.csv'
WORK_DIR = RUNS_DIR / 'final_test_eval74'
IMAGE_EXTS = {'.jpg', '.jpeg', '.png'}


def main():
    if not FINAL_WEIGHT.exists():
        sys.exit(f'Final weight 가 없습니다: {FINAL_WEIGHT.relative_to(PROJECT_ROOT)}')
    if OUT_METRICS.exists():
        sys.exit(f'이미 결과가 있습니다: {OUT_METRICS.relative_to(PROJECT_ROOT)} (한 번만 실행)')

    # 1) manifest 에서 eval_exclude=True 사진 찾기
    with open(TEST_MANIFEST, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    exclude = {r['image_name'] for r in rows if r['eval_exclude'] == 'True'}
    print('제외:', sorted(exclude))

    # 2) dataset.yaml 의 test 폴더에서 제외 사진만 뺀 목록 만들기 (사진은 그대로 둠)
    with open(DATASET_YAML, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    test_dir = (DATASET_YAML.parent / cfg['test']).resolve()
    if not test_dir.is_dir():
        sys.exit(f'test 폴더가 없습니다: {test_dir}')
    images = sorted(p for p in test_dir.iterdir()
                    if p.suffix.lower() in IMAGE_EXTS and p.name not in exclude)
    expected = len(rows) - len(exclude)
    if len(images) != expected:
        sys.exit(f'장수가 안 맞습니다: 폴더 {len(images)}장 · manifest {len(rows)} - 제외 {len(exclude)} = {expected}')

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    list_txt = WORK_DIR / 'test_eval74.txt'
    list_txt.write_text('\n'.join(str(p) for p in images) + '\n', encoding='utf-8')

    # 3) 74장 목록만 가리키는 임시 yaml (Class 이름은 원래 yaml 그대로)
    tmp_yaml = WORK_DIR / 'dataset_test_eval74.yaml'
    with open(tmp_yaml, 'w', encoding='utf-8') as f:
        yaml.safe_dump({'train': str(list_txt), 'val': str(list_txt), 'test': str(list_txt),
                        'names': cfg['names']}, f, allow_unicode=True)

    # 4) 13 과 같은 모델 · 같은 imgsz 로 평가
    print(f'Frozen Test (eval_exclude 제외 {len(images)}장): '
          f'{FINAL_WEIGHT.relative_to(PROJECT_ROOT)} ({FINAL_SOURCE}) · imgsz {FINAL_IMGSZ}')
    metrics = evaluate_detector(
        str(FINAL_WEIGHT), str(tmp_yaml),
        split='test', imgsz=FINAL_IMGSZ, allow_test=True,
        project=RUNS_DIR, name='final_test_eval74',
    )

    # 5) 저장 (75장 결과 final_metrics.csv 는 건드리지 않음)
    overall = summarize_overall(metrics)
    row = {'model_version': 'final', 'source': FINAL_SOURCE, 'dataset_version': DATASET_VERSION,
           'split': f'test_eval{len(images)}', 'model': FINAL_MODEL, 'imgsz': FINAL_IMGSZ, **overall}
    save_metrics_csv(row, OUT_METRICS)
    save_metrics_csv(summarize_per_class(metrics), OUT_CLASS)

    print(f'\n[Frozen Test · {len(images)}장 결과]')
    for k, v in overall.items():
        print(f'  {k:<10} {v}')
    print(f'\n저장: {OUT_METRICS.relative_to(PROJECT_ROOT)}, {OUT_CLASS.relative_to(PROJECT_ROOT)}')


if __name__ == '__main__':
    main()
