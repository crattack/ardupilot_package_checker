# 🚀 ArduPilot Package Checker Sample1
이 프로젝트는 ArduPilot 펌웨어 관련 작업을 돕기 위한 스크립트 모음입니다. 컴파일 환경 점검, 펌웨어 파일 분석, 특정 정보 추출 등의 기능을 제공합니다.

---

### 📦 컴파일 환경 구성 및 테스트

`package_check.sh` 스크립트를 실행하여 **ArduPilot 컴파일 환경**을 설정하고 테스트할 수 있습니다.

```bash
$ bash package_check.sh
```

### 💾 펌웨어 파일 정보 분석
`firmware_analysis.sh` 스크립트를 사용하여 **펌웨어 환경 및 메모리 사이즈와 같은 주요 정보**를 추출합니다.

```bash
$ bash firmware_analysis.sh
```

### 🗺️ 펌웨어 내 GPS 정보 추출
`extract_gps.py` 파이썬 스크립트를 통해 **펌웨어 파일 내에 포함된 GPS 관련 정보**를 분석하고 추출합니다.

```bash
$ python3 extract_gps.py
```

# 🚀 ArduPilot Package Checker Sample2**
이 프로젝트는 PX4 공개 펌웨어 분석을 위한 샘플을 올려 드립니다.

---
## 미션은 다음과 같습니다.

### meta data 추출

### bin 파일 추출 

### 기본 정보 추출 IP/GPS/펌웨어
