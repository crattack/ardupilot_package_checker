#!/bin/bash

# ArduPilot 패키지 충돌 문제 해결 스크립트

set -e

echo "=== ArduPilot 패키지 문제 해결 ==="

# 현재 패키지 상태 출력
echo "현재 설치된 패키지 상태:"
apt list --installed 2>/dev/null | grep -E "(libasound2|libpulse|libsdl)" || echo "관련 패키지 없음"

echo ""
echo "문제 패키지들을 제거하고 ArduPilot 개발환경을 구축합니다..."

# 1. 문제 패키지들 완전 제거
echo "1. 문제 패키지 제거 중..."
sudo apt remove --purge \
    libsdl1.2-dev \
    libasound2-dev \
    libpulse-dev \
    libpulse-mainloop-glib-dev \
    2>/dev/null || true

sudo apt autoremove -y

# 2. 패키지 시스템 정리
echo "2. 패키지 시스템 정리 중..."
sudo apt update
sudo apt --fix-broken install -y
sudo dpkg --configure -a

# 3. ArduPilot 필수 패키지 설치
echo "3. ArduPilot 필수 패키지 설치 중..."
sudo apt install -y \
    build-essential \
    git \
    cmake \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    gcc-arm-none-eabi \
    pkg-config \
    autoconf \
    automake \
    libtool \
    curl \
    wget \
    unzip

echo "✅ 핵심 패키지 설치 완료"

# 4. Python 패키지 설치
echo "4. Python 패키지 설치 중..."
pip3 install --user --upgrade pip setuptools wheel

# ArduPilot 필수 Python 패키지
pip3 install --user \
    pymavlink \
    MAVProxy \
    empy==3.3.4 \
    pyserial \
    future \
    lxml \
    pexpect \
    numpy

echo "✅ Python 패키지 설치 완료"

# 5. 환경 설정
echo "5. 환경 설정 중..."
if ! grep -q '.local/bin' ~/.bashrc; then
    echo 'export PATH=$PATH:$HOME/.local/bin' >> ~/.bashrc
    echo "PATH 설정을 ~/.bashrc에 추가했습니다"
fi

# PATH 현재 세션에 적용
export PATH=$PATH:$HOME/.local/bin

# 6. ArduPilot 설정 확인
if [ -d "ardupilot" ]; then
    echo "6. 기존 ArduPilot 업데이트 중..."
    cd ardupilot
    git pull
    git submodule update --init --recursive
else
    echo "6. ArduPilot 다운로드 중..."
    git clone https://github.com/ArduPilot/ardupilot.git
    cd ardupilot
    git submodule update --init --recursive
fi

# 7. 빌드 테스트
echo "7. 빌드 테스트 중..."
python3 ./waf configure --board Pixhawk1

if python3 ./waf copter; then
    echo "✅ ArduCopter 빌드 성공!"
    echo ""
    echo "빌드된 파일들:"
    ls -la build/Pixhawk1/bin/arducopter.* 2>/dev/null || echo "빌드 파일 확인 실패"
else
    echo "❌ 빌드 실패"
    exit 1
fi

# 8. 시뮬레이션 테스트 (간단히)
echo "8. 시뮬레이션 간단 테스트..."
cd ArduCopter

# 백그라운드에서 3초간 실행
timeout 3s python3 ../Tools/autotest/sim_vehicle.py --no-rebuild --speedup=10 &
SITL_PID=$!

sleep 1

if ps -p $SITL_PID > /dev/null 2>&1; then
    echo "✅ 시뮬레이션 테스트 성공!"
    kill $SITL_PID 2>/dev/null || true
else
    echo "⚠️  시뮬레이션 테스트 실패 (빌드는 정상)"
fi

cd ..

echo ""
echo "=================================================="
echo "  ArduPilot 개발환경 구축 완료!"
echo "=================================================="
echo ""
echo "📁 프로젝트 위치: $(pwd)"
echo ""
echo "🔨 빌드 명령어:"
echo "  ./waf copter                    # ArduCopter 빌드"
echo "  ./waf plane                     # ArduPlane 빌드"
echo "  ./waf rover                     # ArduRover 빌드"
echo ""
echo "🚁 시뮬레이션 실행:"
echo "  cd ArduCopter"
echo "  ../Tools/autotest/sim_vehicle.py --console"
echo "  ../Tools/autotest/sim_vehicle.py --console --map  # 지도 포함"
echo ""
echo "📤 펌웨어 업로드:"
echo "  ./waf copter --upload           # USB로 연결된 보드에 업로드"
echo ""
echo "🌐 네트워크 연결용 시뮬레이션:"
echo "  ../Tools/autotest/sim_vehicle.py --out=tcpin:0.0.0.0:5760"
echo "  (Mission Planner에서 TCP: 127.0.0.1:5760으로 연결)"
echo ""
echo "💡 환경변수 적용:"
echo "  source ~/.bashrc"
echo "  또는 새 터미널 열기"
echo ""
echo "⚠️  참고: SDL GUI 없이 headless 모드로 실행됩니다."
echo ""
