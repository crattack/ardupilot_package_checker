#!/usr/bin/env python3
"""
ArduPilot 펌웨어에서 위치 관련 정보 추출
"""
import struct
import sys
import re

class LocationDataExtractor:
    def __init__(self, firmware_path):
        with open(firmware_path, 'rb') as f:
            self.data = f.read()
        self.text_data = self.data.decode('ascii', errors='ignore')

    def find_coordinate_patterns(self):
        """좌표 패턴 찾기"""
        print("=== 좌표 패턴 검색 ===")

        # GPS 좌표 패턴들
        patterns = [
            # 위도/경도 (소수점 형태)
            r'[-]?\d{1,3}\.\d{4,8}',
            # DMS 형태 (도분초)
            r'\d{1,3}[°]\s*\d{1,2}[\']\s*\d{1,2}[\"]\s*[NSEW]',
            # 파라미터 이름들
            r'HOME_LAT|HOME_LNG|FENCE_LAT|FENCE_LNG',
        ]

        coordinates = set()
        for pattern in patterns:
            matches = re.findall(pattern, self.text_data)
            for match in matches:
                if self.is_valid_coordinate(match):
                    coordinates.add(match)

        print(f"발견된 좌표 후보: {len(coordinates)}개")
        for coord in sorted(coordinates)[:10]:
            print(f"  {coord}")

    def is_valid_coordinate(self, coord_str):
        """유효한 좌표인지 확인"""
        try:
            if coord_str.replace('-', '').replace('.', '').isdigit():
                coord = float(coord_str)
                # 위도: -90 ~ 90, 경도: -180 ~ 180
                return -180 <= coord <= 180
        except:
            pass
        return len(coord_str) > 3 and any(c in coord_str for c in ['LAT', 'LNG', 'HOME', 'FENCE'])

    def find_location_strings(self):
        """위치 관련 문자열 찾기"""
        print("\n=== 위치 관련 문자열 ===")

        keywords = [
            'HOME', 'FENCE', 'GEOFENCE', 'ORIGIN', 'TAKEOFF',
            'LAND', 'RTL', 'WAYPOINT', 'MISSION', 'GPS',
            'LAT', 'LNG', 'LATITUDE', 'LONGITUDE'
        ]

        location_strings = []
        for keyword in keywords:
            start = 0
            while True:
                pos = self.text_data.upper().find(keyword, start)
                if pos == -1:
                    break

                # 주변 컨텍스트 추출
                context_start = max(0, pos - 30)
                context_end = min(len(self.text_data), pos + len(keyword) + 30)
                context = self.text_data[context_start:context_end]

                # 제어 문자 제거 및 정리
                context = ''.join(c for c in context if c.isprintable())
                context = ' '.join(context.split())

                if context and len(context) > 10:
                    location_strings.append(context)

                start = pos + 1

        # 중복 제거 및 정렬
        unique_strings = list(set(location_strings))
        unique_strings.sort()

        print(f"위치 관련 문자열 {len(unique_strings)}개:")
        for i, s in enumerate(unique_strings[:15]):
            print(f"  {i+1:2d}. {s}")

    def find_default_parameters(self):
        """기본 파라미터 값 찾기"""
        print("\n=== 기본 파라미터 검색 ===")

        # ArduPilot 파라미터 패턴
        param_patterns = [
            r'HOME_LAT[^a-zA-Z][^0-9]*[-]?\d+\.?\d*',
            r'HOME_LNG[^a-zA-Z][^0-9]*[-]?\d+\.?\d*',
            r'FENCE_LAT[^a-zA-Z][^0-9]*[-]?\d+\.?\d*',
            r'FENCE_LNG[^a-zA-Z][^0-9]*[-]?\d+\.?\d*',
            r'WPNAV_SPEED[^a-zA-Z][^0-9]*\d+',
            r'RTL_ALT[^a-zA-Z][^0-9]*\d+',
        ]

        for pattern in param_patterns:
            matches = re.findall(pattern, self.text_data, re.IGNORECASE)
            if matches:
                print(f"  패턴 '{pattern[:20]}...': {len(matches)}개 발견")
                for match in matches[:3]:
                    clean_match = ''.join(c for c in match if c.isprintable())
                    print(f"    {clean_match}")

    def search_hardcoded_locations(self):
        """하드코딩된 테스트 위치 찾기"""
        print("\n=== 하드코딩된 테스트 위치 ===")

        # 일반적인 테스트 위치들 (ArduPilot SITL 기본값)
        test_locations = [
            "37.761169",    # SITL 기본 위도
            "-122.494194",  # SITL 기본 경도
            "35.432778",    # 다른 테스트 위치들
            "149.165222",
            "40.071374",
            "-105.220780",
        ]

        found_locations = []
        for location in test_locations:
            if location in self.text_data:
                pos = self.text_data.find(location)
                # 주변 컨텍스트
                context_start = max(0, pos - 50)
                context_end = min(len(self.text_data), pos + 50)
                context = self.text_data[context_start:context_end]
                context = ''.join(c for c in context if c.isprintable())

                found_locations.append((location, context))

        if found_locations:
            print("발견된 테스트 위치:")
            for location, context in found_locations:
                print(f"  {location}: ...{context}...")
        else:
            print("하드코딩된 테스트 위치 없음")

    def extract_binary_coordinates(self):
        """바이너리에서 IEEE 754 부동소수점 좌표 찾기"""
        print("\n=== 바이너리 좌표 검색 ===")

        coordinates = []
        # 4바이트씩 읽어서 부동소수점으로 해석
        for i in range(0, len(self.data) - 4, 4):
            try:
                value = struct.unpack('<f', self.data[i:i+4])[0]
                # 유효한 GPS 좌표 범위 확인
                if -180 <= value <= 180 and abs(value) > 1:
                    # 소수점 자리가 적절한지 확인
                    if len(f"{value:.6f}".split('.')[1]) >= 4:
                        coordinates.append((i, value))
            except:
                continue

        # 유사한 값들 제거하고 상위 10개만
        unique_coords = []
        for offset, coord in coordinates:
            if not any(abs(coord - uc[1]) < 0.001 for uc in unique_coords):
                unique_coords.append((offset, coord))

        unique_coords.sort(key=lambda x: abs(x[1]), reverse=True)

        print(f"발견된 좌표 후보: {len(unique_coords)}개")
        for offset, coord in unique_coords[:10]:
            print(f"  Offset 0x{offset:08X}: {coord:.6f}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 location_extractor.py <firmware_file>")
        print("Example: python3 location_extractor.py build/Pixhawk1/bin/arducopter.bin")
        sys.exit(1)

    firmware_path = sys.argv[1]

    try:
        extractor = LocationDataExtractor(firmware_path)
        extractor.find_coordinate_patterns()
        extractor.find_location_strings()
        extractor.find_default_parameters()
        extractor.search_hardcoded_locations()
        extractor.extract_binary_coordinates()

    except FileNotFoundError:
        print(f"Error: File {firmware_path} not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
