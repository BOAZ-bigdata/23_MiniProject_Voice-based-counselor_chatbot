import os
import torch
import torchaudio
import streamlit as st
from datetime import datetime
from transformers import AutoModelForAudioClassification, AutoProcessor

# 음성 감정 인식 모델 설정
model_name = "forwarder1121/ast-finetuned-model"
processor = AutoProcessor.from_pretrained(model_name)
model = AutoModelForAudioClassification.from_pretrained(model_name)

# 감정 매핑
EMOTION_MAPPING = {
    0: "Anger",
    1: "Disgust", 
    2: "Fear",
    3: "Happy",
    4: "Neutral",
    5: "Sad"
}

def process_audio_emotion(audio_path):
    """통합된 오디오 처리 및 감정 분석 함수"""
    try:
        # 오디오 로드
        waveform, sample_rate = torchaudio.load(audio_path)
        
        # 모노 채널로 변환
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        
        # 16kHz로 리샘플링
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
            waveform = resampler(waveform)
        
        # 입력 길이 조정
        target_length = 16000  # 1초 길이
        if waveform.shape[1] > target_length:
            waveform = waveform[:, :target_length]
        elif waveform.shape[1] < target_length:
            padding = torch.zeros(1, target_length - waveform.shape[1])
            waveform = torch.cat([waveform, padding], dim=1)
        
        # 감정 분석
        inputs = processor(waveform.squeeze(), sampling_rate=16000, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model(**inputs)
        
        predicted_class_idx = outputs.logits.argmax(-1).item()
        emotion = EMOTION_MAPPING.get(predicted_class_idx, "Unknown")
        
        return emotion
    
    except Exception as e:
        st.error(f"음성 감정 분석 중 오류 발생: {e}")
        return None

def handle_audio_upload(uploaded_audio):
    """음성 파일 업로드 처리"""
    temp_file_path = "temp_audio.wav"
    
    try:
        # 임시 파일로 저장
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_audio.getbuffer())
        
        # 감정 분석
        with st.spinner("음성 분석 중..."):
            # 텍스트 변환 (기존 audio_handler 함수 사용)
            audio_text = process_audio_input(uploaded_audio.read())
            
            # 감정 분석
            audio_emotion = process_audio_emotion(temp_file_path)
            
            if audio_emotion:
                # 메시지 업데이트
                current_time = datetime.now().strftime('%p %I:%M')
                st.session_state.current_emotion = audio_emotion
                
                if audio_text:
                    st.session_state.messages.append({
                        "role": "user",
                        "content": f"[음성 파일] 텍스트: {audio_text}",
                        "emotion": audio_emotion,
                        "timestamp": current_time
                    })
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"음성에서 '{audio_text}'를 감지했으며, 감정은 '{audio_emotion}'입니다.",
                        "timestamp": current_time
                    })
                else:
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "[음성 파일 업로드됨]",
                        "emotion": audio_emotion,
                        "timestamp": current_time
                    })
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"음성에서 감지된 감정은 '{audio_emotion}'입니다.",
                        "timestamp": current_time
                    })
                
                # 통계 업데이트
                update_conversation_stats(audio_emotion)
            
            else:
                st.warning("음성 감정을 분석할 수 없었습니다.")
        
    except Exception as e:
        st.error(f"음성 처리 중 오류: {e}")
    
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        st.rerun()

def update_conversation_stats(emotion: str):
    """Update conversation statistics based on the detected emotion."""
    st.session_state.conversation_stats['total'] += 1
    if emotion in ['Happy', 'Neutral']:
        st.session_state.conversation_stats['positive'] += 1
    elif emotion in ['Anger', 'Disgust', 'Fear', 'Sad']:
        st.session_state.conversation_stats['negative'] += 1

def main():
    st.set_page_config(
        page_title="감정인식 챗봇",
        page_icon="🤗",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 커스텀 스타일 적용
    apply_chat_styles()

    # 세션 상태 초기화
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.chatbot_service = ChatbotService(OpenAIConfig())
        st.session_state.messages = [{
            'role': 'assistant',
            'content': "안녕하세요! 오늘 하루는 어떠셨나요? 기분이나 감정을 자유롭게 이야기해주세요. 텍스트로 입력하거나 음성 파일을 업로드해주세요. 😊",
            'timestamp': datetime.now().strftime('%p %I:%M')
        }]
        st.session_state.last_uploaded_audio = None
        st.session_state.current_emotion = "분석된 감정 없음"
        st.session_state.conversation_stats = {
            'total': 0,
            'positive': 0,
            'negative': 0
        }

    # 사이드바
    with st.sidebar:
        st.title("감정인식 챗봇 🏠")

        st.markdown("### 사용 방법")
        st.markdown("""
        1. 채팅창에 현재 기분이나 상황을 입력하세요.
        2. 음성 파일을 업로드하여 감정을 분석할 수 있습니다.
        3. 챗봇이 감정을 분석하고 공감적인 대화를 제공합니다.
        4. 필요한 경우 적절한 조언이나 위로를 받을 수 있습니다.
        """)

        # 현재 감정 상태 표시
        if 'current_emotion' in st.session_state:
            st.markdown("### 현재 감정 상태")
            emotion = st.session_state.current_emotion
            emotion_color = get_emotion_color(emotion)  # 감정에 따른 색상 가져오기
            st.markdown(f"""
            <div style="
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 16px;
            ">
                <span style="
                    background-color: {emotion_color};
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-weight: 600;
                ">{emotion}</span>
            </div>
            """, unsafe_allow_html=True)
    
            # 대화 통계 표시
            if 'conversation_stats' in st.session_state:
                st.markdown("### 대화 통계")
                stats = st.session_state.conversation_stats
                st.write(f"- 총 대화 수: {stats.get('total', 0)}")
                st.write(f"- 긍정적 감정: {stats.get('positive', 0)}")
                st.write(f"- 부정적 감정: {stats.get('negative', 0)}")
    
            # 음성 파일 업로더
            st.markdown("### 음성 파일 업로드")
            uploaded_audio = st.file_uploader("지원 형식: WAV", type=["wav"])
    
            if uploaded_audio is not None and uploaded_audio != st.session_state.last_uploaded_audio:
                st.session_state.last_uploaded_audio = uploaded_audio
                handle_audio_upload(uploaded_audio)


    # 메인 채팅 영역
    st.title("채팅")

    # 메시지 표시
    for message in st.session_state.get('messages', []):
        with st.chat_message(message["role"]):
            display_message(message)

    # 텍스트 입력창
    if prompt := st.chat_input("메시지를 입력하세요..."):
        if prompt.strip():
            chatbot = st.session_state.chatbot_service
            emotions = chatbot.analyze_emotion(prompt)
            dominant_emotion = max(emotions.items(), key=lambda x: x[1])[0]
            response = chatbot.get_response(prompt)

            current_time = datetime.now().strftime('%p %I:%M')
            st.session_state.messages.append({
                "role": "user",
                "content": prompt,
                "emotion": dominant_emotion,
                "timestamp": current_time
            })
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "timestamp": current_time
            })

            # 통계 업데이트
            update_conversation_stats(dominant_emotion)

            st.rerun()


if __name__ == "__main__":
    main()
