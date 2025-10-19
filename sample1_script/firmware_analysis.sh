#!/bin/bash

# ArduPilot 펌웨어 정보 확인 스크립트

FIRMWARE_PATH="arducopter.bin"
ELF_PATH="arducopter.elf" # 심볼정보

echo "=== ArduPilot 펌웨어 정보 ==="
echo ""

# 1. 파일 기본 정보
echo "📁 파일 정보:"
if [ -f "$FIRMWARE_PATH" ]; then
    echo "  펌웨어 파일: $FIRMWARE_PATH"
    echo "  크기: $(du -h $FIRMWARE_PATH | cut -f1) ($(stat -c%s $FIRMWARE_PATH) bytes)"
    echo "  생성일: $(stat -c %y $FIRMWARE_PATH)"
    echo "  파일 타입: $(file -b $FIRMWARE_PATH)"
else
    echo "  ❌ 펌웨어 파일을 찾을 수 없습니다: $FIRMWARE_PATH"
    exit 1
fi

echo ""

# 2. ARM 바이너리 정보
echo "🔧 ARM 바이너리 정보:"
if [ -f "$ELF_PATH" ]; then
    echo "  아키텍처: $(arm-none-eabi-objdump -f $ELF_PATH | grep architecture | cut -d: -f2)"
    echo "  시작 주소: $(arm-none-eabi-objdump -f $ELF_PATH | grep 'start address' | cut -d: -f2)"
    echo "  포맷: $(arm-none-eabi-objdump -f $ELF_PATH | grep 'file format' | cut -d: -f2)"
else
    echo "  ⚠️  ELF 파일 없음 (바이너리 정보만 확인)"
fi

echo ""

# 3. 메모리 사용량
echo "💾 메모리 사용량:"
if [ -f "$ELF_PATH" ]; then
    arm-none-eabi-size $ELF_PATH
    echo "  - text: 코드 영역 (플래시)"
    echo "  - data: 초기화된 데이터 (RAM)"
    echo "  - bss: 초기화되지 않은 데이터 (RAM)"
else
    echo "  펌웨어 크기: $(stat -c%s $FIRMWARE_PATH) bytes"
    echo "  (ELF 파일 없음으로 세부 섹션 정보 불가)"

    # 바이너리 크기로 추정
    FW_SIZE=$(stat -c%s $FIRMWARE_PATH)
    echo "  추정 text 섹션: ~${FW_SIZE} bytes (플래시 사용)"
    echo "  추정 RAM 사용: ~64KB (일반적인 ArduPilot 사용량)"
fi

echo ""

# 4. 벡터 테이블 (처음 32바이트)
echo "🎯 벡터 테이블 (ARM Cortex-M):"
hexdump -C -n 32 $FIRMWARE_PATH | head -2
echo "  첫 4바이트: 스택 포인터 초기값"
echo "  다음 4바이트: 리셋 핸들러 주소"

echo ""

# 5. 문자열 정보
echo "📝 펌웨어 문자열 정보:"
echo "  ArduPilot 관련:"
strings $FIRMWARE_PATH | grep -i ardupilot | head -3
echo "  버전 정보:"
strings $FIRMWARE_PATH | grep -E "(version|build|commit)" | head -3
echo "  보드 정보:"
strings $FIRMWARE_PATH | grep -i pixhawk | head -3

echo ""

# 6. 체크섬
echo "🔐 무결성 체크:"
echo "  MD5: $(md5sum $FIRMWARE_PATH | cut -d' ' -f1)"
echo "  SHA256: $(sha256sum $FIRMWARE_PATH | cut -d' ' -f1)"

echo ""

# 7. 플래시 사용률 (일반적인 Pixhawk 2MB 기준)
FLASH_SIZE=$((2 * 1024 * 1024))  # 2MB
FIRMWARE_SIZE=$(stat -c%s $FIRMWARE_PATH)
USAGE_PERCENT=$((FIRMWARE_SIZE * 100 / FLASH_SIZE))

echo "📊 플래시 사용률 (Pixhawk 2MB 기준):"
echo "  사용: ${FIRMWARE_SIZE} bytes"
echo "  전체: ${FLASH_SIZE} bytes"
echo "  사용률: ${USAGE_PERCENT}%"

if [ $USAGE_PERCENT -gt 80 ]; then
    echo "  ⚠️  플래시 사용률이 높습니다!"
else
    echo "  ✅ 플래시 사용률 정상"
fi

echo ""
echo "=== 정보 확인 완료 ==="
