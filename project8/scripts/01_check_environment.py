import sys

import torch
import ultralytics
from ultralytics import YOLO


def main():
    print('Python:', sys.version.split()[0])
    print('PyTorch:', torch.__version__)
    print('Ultralytics:', ultralytics.__version__)
    print('CUDA available:', torch.cuda.is_available())

    if torch.cuda.is_available():
        print('GPU:', torch.cuda.get_device_name(0))

    # 사전학습 모델 불러오기 확인 (처음 실행 때 yolo11n.pt를 자동으로 내려받음)
    model = YOLO('yolo11n.pt')
    print('YOLO load OK, classes:', len(model.names))


if __name__ == '__main__':
    main()
