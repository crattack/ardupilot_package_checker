#!/usr/bin/env python3
"""
Zlib 압축 펌웨어 해제 도구
"""
import zlib
import sys
import os

def decompress_zlib_firmware(input_file, output_file=None):
    """
    Zlib으로 압축된 펌웨어 파일을 해제합니다.

    Args:
        input_file: 입력 펌웨어 파일 경로
        output_file: 출력 파일 경로 (None이면 자동 생성)
    """
    # 출력 파일명 자동 생성
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_decompressed.bin"

    try:
        print(f"[*] 파일 읽는 중: {input_file}")
        with open(input_file, 'rb') as f:
            compressed_data = f.read()

        print(f"[*] 압축된 데이터 크기: {len(compressed_data)} bytes")

        # Zlib 압축 해제 시도
        print("[*] Zlib 압축 해제 중...")
        decompressed_data = zlib.decompress(compressed_data)

        print(f"[+] 압축 해제 성공!")
        print(f"[*] 해제된 데이터 크기: {len(decompressed_data)} bytes")
        print(f"[*] 압축률: {len(compressed_data)/len(decompressed_data)*100:.2f}%")

        # 해제된 데이터 저장
        with open(output_file, 'wb') as f:
            f.write(decompressed_data)

        print(f"[+] 저장 완료: {output_file}")

        # 헤더 정보 출력 (처음 16바이트)
        print("\n[*] 파일 헤더 (처음 16바이트):")
        print(" ".join(f"{b:02x}" for b in decompressed_data[:16]))

        return True

    except zlib.error as e:
        print(f"[-] Zlib 압축 해제 실패: {e}")
        print("[*] 다른 압축 방식이거나 손상된 파일일 수 있습니다.")
        return False

    except FileNotFoundError:
        print(f"[-] 파일을 찾을 수 없습니다: {input_file}")
        return False

    except Exception as e:
        print(f"[-] 오류 발생: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("사용법: python decompress_zlib.py <firmware.bin> [output.bin]")
        print("예제: python decompress_zlib.py firmware.bin")
        print("     python decompress_zlib.py firmware.bin extracted.bin")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    decompress_zlib_firmware(input_file, output_file)

if __name__ == "__main__":
    main()




