### 23 Mini Project: **Voice-based-counselor_chatbot**

- **Usage**: 
  - [ ] Session
  - [ ] Conference
  - [x] Mini projects
  - [ ] Study

- **Period**:  
  - 2024.11 ~ 2024.12

- **Team**:  
  - **Team Manager**: 김동환
  - **Team Members**: 김윤주, 김현석, 김윤희, 이재욱

- **Project Summary**:  
  - 음성 기반 상담사 챗봇
  - SER(fine-tuning 진행하여 HuggingFace 등록, Inference API 이용)
  - RAG(보건복지부 질병 문서 등록, 챗봇이 문서 기반 응답)
  - Prompting(상담사의 페르소나 부여)
  - Streamlit으로 구현



---



# SER-Chatbot (Speech Emotion Recognition Chatbot)

![QR Code](https://github.com/user-attachments/assets/d4189447-4442-4ef3-976e-e7675a5a63c4)

## 프로젝트 소개

**SER-Chatbot**은 사용자의 **음성**과 **텍스트**를 통해 감정을 인식하고, 공감적인 대화를 제공하는 AI 챗봇 서비스입니다. 다양한 **페르소나**를 통해 사용자에게 맞춤형 상담과 대화를 제공합니다.

## 시스템 아키텍처

![System Architecture](https://github.com/user-attachments/assets/15f1a560-6c47-4460-9790-5ef860ba3799)

## 주요 기능

- **음성/텍스트 기반 감정 인식**
- **다중 페르소나 기반 대화**
- **실시간 감정 분석 및 통계**
- **RAG(Retrieval-Augmented Generation) 기반 맥락 인식**
- **웹 기반 실시간 음성 입력**

## 페르소나 목록

- **김서연 교수**: 심리학과 교수 | 상담심리전문가
- **박준영 멘토**: 리더십 코치 | 커리어 멘토
- **민지원 친구**: 또래 상담사 | 공감 전문가
- **이현우 상담가**: 임상심리전문가 | CBT 전문가
- **정유진 카운셀러**: 예술치료사 | 감정코칭 전문가

## 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python
- **AI/ML**:
  - OpenAI GPT-4
  - Whisper (음성 인식)
  - Hugging Face Transformers (감정 분석)
- **Vector Database**: Pinecone
- **Audio Processing**: WebRTC

## 설치 방법

1. **저장소 클론**

   ```bash
   git clone https://github.com/your-username/ser-chatbot.git
   cd ser-chatbot
   ```

2. **가상환경 생성 및 활성화**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows의 경우: venv\Scripts\activate
   ```

3. **의존성 설치**

   ```bash
   pip install -r requirements.txt
   ```

4. **환경 변수 설정**

   `.env` 파일을 생성하고 다음 내용을 추가합니다:

   ```env
   OPENAI_API_KEY=your-openai-api-key
   PINECONE_API_KEY=your-pinecone-api-key
   PINECONE_ENVIRONMENT=your-pinecone-environment
   PINECONE_INDEX_NAME=your-pinecone-index-name
   ```

## 실행 방법

```bash
python app.py
```

## 환경 변수 설정

- `OPENAI_API_KEY`: OpenAI API 키
- `PINECONE_API_KEY`: Pinecone API 키
- `PINECONE_ENVIRONMENT`: Pinecone 환경
- `PINECONE_INDEX_NAME`: Pinecone 인덱스 이름

## 프로젝트 구조

```
ser-chatbot/
├── app.py                # 메인 애플리케이션 파일
├── requirements.txt      # 필요한 라이브러리 목록
├── README.md             # 프로젝트 설명서
├── services/             # 서비스 로직 폴더
│   ├── __init__.py
│   ├── emotion_recognition.py
│   ├── persona_manager.py
│   └── chat_engine.py
└── assets/               # 이미지 및 기타 자산
```

## 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)를 따릅니다.

## 기여 방법

1. 저장소를 포크합니다.
2. 새로운 기능 브랜치를 만듭니다.

   ```bash
   git checkout -b feature/your-feature
   ```

3. 변경 사항을 커밋합니다.

   ```bash
   git commit -m "Add your feature"
   ```

4. 브랜치에 푸시합니다.

   ```bash
   git push origin feature/your-feature
   ```

5. 새로운 Pull Request를 생성합니다.

## 문의사항

- **버그 보고 및 기능 제안**: [이슈 트래커](https://github.com/your-username/ser-chatbot/issues)를 이용해주세요.
- **기타 문의사항**: 이메일 `your-email@example.com`로 연락주시기 바랍니다.

## 주의사항

- **음성 인식 기능**은 **Chrome 브라우저**에서 가장 잘 작동합니다.
- **마이크 접근 권한**이 필요합니다.
- **API 키**는 보안을 위해 반드시 환경 변수로 관리해야 합니다.

## 향후 계획

- **다국어 지원 추가**
- **음성 감정 인식 정확도 개선**
- **추가 페르소나 개발**
- **모바일 최적화**

## 감사의 글

이 프로젝트는 다음 **오픈소스 프로젝트**들의 도움을 받았습니다:

- [Streamlit](https://streamlit.io/)
- [OpenAI](https://openai.com/)
- [Hugging Face](https://huggingface.co/)
- [Pinecone](https://www.pinecone.io/)
- [WebRTC](https://webrtc.org/)

---
