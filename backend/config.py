# config.py
import os

# --- 외부 DB 접속 정보 ---
SOURCE_DB_USER = "TEAM03"
SOURCE_DB_PASSWORD = "oracle_4U"
SOURCE_DB_HOST = "138.2.63.245"
SOURCE_DB_PORT = 1521
SOURCE_DB_SERVICE_NAME = "srvinv.sub03250142080.kdtvcn.oraclevcn.com"

# --- OCI ADW 접속 정보 ---
ADW_USER = "ADMIN"
ADW_PASSWORD = "oracle_4Uoracle_4U"
ADW_WALLET_PASSWORD = "oracle_4U"
ADW_DSN = "qj5stctdzpuj2amt_high"

# --- 경로 및 모델 설정 ---
BASE_DIR = '/home/opc/ner_project'
# <<< 이 부분이 현재 디렉터리 이름에 맞게 수정되었습니다
WALLET_LOCATION = os.path.join(BASE_DIR, 'Wallet_QJ5STCTDZPUJ2AMT')
LOCAL_MODEL_PATH = os.path.join(BASE_DIR, 'final-korean-ner-model-optimized_v2')
MEDICAL_DICT_PATH = os.path.join(BASE_DIR, 'medical_dict_v7.json')
CLIENT_LIB_DIR = "/usr/lib/oracle/19.19/client64/lib"

# --- 모델 파라미터 ---
SIMILARITY_THRESHOLD = 85
