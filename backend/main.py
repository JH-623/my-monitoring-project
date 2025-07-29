# main.py (최종 안정 버전)

import os
import sys
import uvicorn
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Union, List
from llama_index.core.llms import ChatMessage, MessageRole
import config

# --- 1. 프로젝트 경로 설정 및 라이브러리 임포트 ---

def load_dependencies():
    global create_engine, text, OpenAI, AutoTokenizer, AutoModelForTokenClassification, pipeline
    from sqlalchemy import create_engine, text
    from llama_index.llms.openai import OpenAI
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# --- 2. FastAPI 앱 및 모델 초기화 ---
app = FastAPI(title="NER 기반 감염병 모니터링 RAG 챗봇", openapi_prefix="/chat")

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    question: str
    ner_result: dict
    generated_sql: str
    answer: str
    db_result: Union[list, str]

ner_pipeline = None
llm = None
engine = None
custom_view_info = None

def extract_sql_from_response(response: str) -> str:
    """AI의 응답에서 SQL 쿼리만 추출합니다. 여러 줄로 된 쿼리도 처리합니다."""
    # ```sql ... ``` 블록이 있다면 그 내용을 반환
    match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # 여러 줄의 쿼리를 처리하기 위해 개행 문자를 공백으로 바꿉니다.
    single_line_response = response.replace('\n', ' ').replace('\r', ' ')
    
    # SELECT로 시작하는 전체 쿼리를 찾습니다.
    sql_match = re.search(r"(SELECT .*?(?:;|WHERE ROWNUM = \d+|FETCH FIRST \d+ ROWS ONLY|LIMIT \d+|$))", single_line_response, re.IGNORECASE)
    if sql_match:
        # 끝에 세미콜론이 있다면 제거
        return sql_match.group(1).strip().rstrip(';')

    return "SQL 쿼리를 추출하지 못했습니다."

@app.on_event("startup")
def startup_event():
    global ner_pipeline, llm, engine, custom_view_info
    print("서버 시작: 의존성 및 모델을 로드합니다...")
    load_dependencies()

    # --- NER 모델 로드 ---
    print(f"NER 모델 로딩 시작: {config.LOCAL_MODEL_PATH}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(config.LOCAL_MODEL_PATH)
        model = AutoModelForTokenClassification.from_pretrained(config.LOCAL_MODEL_PATH)
        ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, grouped_entities=True)
        print("NER 모델 로딩 성공.")
    except Exception as e:
        print(f"NER 모델 로딩 실패: {e}")

    # --- Oracle DB 연결 및 LLM 초기화 ---
    print("Oracle DB 연결 및 LLM 초기화 시작...")
    try:
        custom_view_info = {
            "V_MEDICAL_CODEBOOK": "CREATE TABLE V_MEDICAL_CODEBOOK (ID VARCHAR2(255), CATEGORY VARCHAR2(255), CODE_KO VARCHAR2(255), CODE_EN VARCHAR2(255))",
            "V_PROCESSED_ANTIBIOTIC": "CREATE TABLE V_PROCESSED_ANTIBIOTIC (\"항생제결과_ID\" NUMBER, \"결과_ID\" NUMBER, \"항생제명\" VARCHAR2(255), \"MIC_결과값\" VARCHAR2(50), \"판정\" VARCHAR2(50))",
            "V_PROCESSED_MICROBE": "CREATE TABLE V_PROCESSED_MICROBE (\"결과_ID\" NUMBER, \"원본_내원번호\" VARCHAR2(255), \"원본_환자번호\" VARCHAR2(255), \"성별\" VARCHAR2(10), \"생년월일\" DATE, \"입원일\" DATE, \"검사시행일시\" DATE, \"결과유형\" VARCHAR2(255), \"동정균주명\" VARCHAR2(255) COMMENT 'This is the identified microbe species name. Also called ''균'', ''병원균'', ''균주''.', \"균_정량_상세\" VARCHAR2(255), \"주요내성_특징\" VARCHAR2(255), \"코멘트\" VARCHAR2(1000), \"최종보고일시\" DATE, \"검사명\" VARCHAR2(255), \"검체명_주검체\" VARCHAR2(255)) COMMENT 'To get the top N results, please use a subquery with ROWNUM instead of FETCH FIRST N ROWS ONLY.'"
        }
        
        os.environ['TNS_ADMIN'] = config.WALLET_LOCATION
        import oracledb
        oracledb.init_oracle_client(lib_dir=config.CLIENT_LIB_DIR)
        engine = create_engine(f"oracle+oracledb://{config.ADW_USER}:{config.ADW_PASSWORD}@{config.ADW_DSN}")
        
        llm = OpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
        print("DB 연결 및 LLM 초기화 성공.")
    except Exception as e:
        print(f"DB 연결 또는 LLM 초기화 실패: {e}")

@app.post("/bot", response_model=ChatResponse, summary="챗봇에게 질문하기")
async def chat_with_bot(request: ChatRequest):
    if not engine or not ner_pipeline or not llm:
        raise HTTPException(status_code=503, detail="서버가 아직 준비되지 않았습니다.")

    question = request.question
    ner_results_raw = ner_pipeline(question)
    ner_results_processed = {item['entity_group']: item['word'] for item in ner_results_raw}

    try:
        # --- 1단계: AI에게 보낼 프롬프트 구성 ---
        context_str_prefix = "### Oracle SQL 쿼리 생성 규칙:\n- 질문에 답하기 위한 Oracle SQL 쿼리 하나만 생성해주세요.\n- 다른 설명이나 사과는 절대 포함하지 마세요.\n- 쿼리는 `SELECT`로 시작해야 합니다.\n- 쿼리 끝에는 세미콜론(;)을 붙이지 마세요.\n- 컬럼 별칭(Alias)에는 한글을 사용하지 말고, 'cnt'나 'result_name' 같은 간단한 영어를 사용하세요.\n- 집계 또는 분석 시, 주요 컬럼의 값이 NULL인 데이터는 반드시 제외하세요 (예: WHERE \"column_name\" IS NOT NULL).\n\n### 테이블 스키마 정보:\n"
        for view_name, view_schema in custom_view_info.items():
            context_str_prefix += f"테이블명: {view_name}\n스키마: {view_schema}\n"
        
        final_prompt = f"{context_str_prefix}\n### 질문:\n{question}"

        # --- 2단계: AI 모델 직접 호출 (chat 메소드 사용) ---
        print("AI 모델에 쿼리 생성 요청...")
        response_message = llm.chat([
            ChatMessage(role=MessageRole.USER, content=final_prompt)
        ])
        ai_response_text = response_message.message.content
        print(f"AI 원본 응답: {ai_response_text}")

        # --- 3단계: AI 응답에서 SQL만 추출 ---
        sql_query = extract_sql_from_response(ai_response_text)
        print(f"추출된 SQL: {sql_query}")

        db_result = "DB 결과 없음"
        if "SELECT" in sql_query.upper():
            # --- 4단계: 추출된 SQL을 DB에서 직접 실행 ---
            with engine.connect() as connection:
                cursor_result = connection.execute(text(sql_query))
                rows = cursor_result.fetchall()
                db_result = [dict(row._mapping) for row in rows]
                print(f"DB 실행 결과: {db_result}")
        else:
            db_result = "유효한 SQL이 생성되지 않았습니다."

        return ChatResponse(
            question=question,
            ner_result=ner_results_processed,
            generated_sql=sql_query,
            answer=ai_response_text,
            db_result=db_result
        )
    except Exception as e:
        print(f"챗봇 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"챗봇 응답 생성 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("경고: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    uvicorn.run(app, host="0.0.0.0", port=8001)
