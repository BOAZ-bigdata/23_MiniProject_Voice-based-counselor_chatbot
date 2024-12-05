import streamlit as st
from src.utils.initialization import initialize_session_state
from src.utils.error_handling import handle_streamlit_errors
import torch
import torchaudio
import os
from datetime import datetime
import time
from transformers import AutoModelForAudioClassification, AutoProcessor
import torchaudio.transforms as T
import wave
import speech_recognition as sr
from audio_recorder_streamlit import audio_recorder
import numpy as np

from src.core.services.chatbot_service import ChatbotService
from src.app.config import OpenAIConfig
from src.utils.audio_handler import process_recorded_audio, predict_audio_emotion
from src.components.message_display import apply_chat_styles, display_message, get_emotion_color
from src.core.services.personas import PERSONAS
from src.utils.state_management import (
    initialize_session_state, 
    clear_session_state, 
    ensure_state_initialization
)
from src.components.chat_components import (
    render_emotion_indicator,
    render_conversation_stats
)
from src.app.constants import (
    DEFAULT_PERSONA, 
    DEFAULT_EMOTION, 
    EMOTIONS,
    EMOTION_MAPPING,
    PERSONA_NAME_MAPPING
)

# 음성 감정 인식 모델 설정
MODEL_NAME = "forwarder1121/ast-finetuned-model"
processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForAudioClassification.from_pretrained(MODEL_NAME)

AUDIO_ENABLED = True
try:
    from src.utils.audio_handler import process_recorded_audio, predict_audio_emotion
except ImportError:
    AUDIO_ENABLED = False
    st.warning("Audio functionality is disabled. Please install required dependencies.")

def get_emotion_from_gpt(prompt: str) -> str:
    """
    GPT를 통해 텍스트의 감정을 분석합니다.
    
    Args:
        prompt (str): 분석할 텍스트
        
    Returns:
        str: 감지된 감정 (Anger, Disgust, Fear, Happy, Neutral, Sad 중 하나)
    """
    predefined_emotions = list(EMOTION_MAPPING.values())
    emotion_prompt = (
        f"The user said: \"{prompt}\".\n"
        f"Classify the user's input into one of these emotions: {', '.join(predefined_emotions)}.\n"
        f"Respond ONLY with the emotion name (e.g., Happy, Neutral).\n"
    )

    response = st.session_state.chatbot_service.llm.invoke(emotion_prompt)
    detected_emotion = response.content.strip()

    if detected_emotion not in predefined_emotions:
        detected_emotion = DEFAULT_EMOTION

    return detected_emotion

def process_audio(waveform: torch.Tensor, target_sample_rate: int = 16000, target_length: int = 16000) -> torch.Tensor:
    """Process audio to correct format."""
    try:
        if waveform.shape[0] > 1:  # 다채널 오디오인 경우 평균 처리
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        if waveform.shape[1] > 0:
            current_sample_rate = target_sample_rate
            if current_sample_rate != target_sample_rate:
                resampler = T.Resample(orig_freq=current_sample_rate, new_freq=target_sample_rate)
                waveform = resampler(waveform)

        if waveform.shape[1] < target_length:
            padding_length = target_length - waveform.shape[1]
            waveform = torch.nn.functional.pad(waveform, (0, padding_length))
        else:
            start = (waveform.shape[1] - target_length) // 2
            waveform = waveform[:, start:start + target_length]

        return waveform
    except Exception as e:
        st.error(f"Error in audio processing: {str(e)}")
        return None

def predict_audio_emotion(audio_path: str) -> str:
    """Predict emotion from audio file."""
    try:
        waveform, sample_rate = torchaudio.load(audio_path)
        processed_waveform = process_audio(waveform)
        if processed_waveform is None:
            return None

        inputs = processor(processed_waveform.squeeze(), sampling_rate=16000, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)

        predicted_class_idx = outputs.logits.argmax(-1).item()
        return EMOTION_MAPPING.get(predicted_class_idx, DEFAULT_EMOTION)

    except Exception as e:
        st.error(f"감정 분석 중 오류 발생: {str(e)}")
        return None

def handle_chat_message(prompt: str, current_persona: str) -> tuple:
    """
    채팅 메시지를 처하고 응답을 생성합니다.
    """
    # 감정 분석
    user_emotion = get_emotion_from_gpt(prompt)
    st.session_state.current_emotion = user_emotion
    
    # GPT 응답 생성
    response = st.session_state.chatbot_service.get_response(prompt, current_persona)
    
    return user_emotion, response

def add_chat_message(role: str, content: str, emotion: str = None):
    """
    채팅 메시지를 대화 기록에 추가합니다.
    """
    current_time = datetime.now().strftime('%p %I:%M')
    message = {
        "role": role,
        "content": content,
        "timestamp": current_time
    }
    if emotion:
        message["emotion"] = emotion
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append(message)

def update_conversation_stats(emotion: str):
    """
    대화 통계를 업데이트합니다.
    
    Args:
        emotion (str): 감지된 감정
    """
    if 'conversation_stats' not in st.session_state:
        st.session_state.conversation_stats = {
            'total': 0,
            'positive': 0,
            'negative': 0
        }
    
    # 전체 대화 수 증가
    st.session_state.conversation_stats['total'] += 1
    
    # 감정에 따른 통계 업데이트
    positive_emotions = ['Happy']
    negative_emotions = ['Anger', 'Disgust', 'Fear', 'Sad']
    
    if emotion in positive_emotions:
        st.session_state.conversation_stats['positive'] += 1
    elif emotion in negative_emotions:
        st.session_state.conversation_stats['negative'] += 1

def process_recorded_audio(audio_bytes):
    """녹음된 오디오를 처리하고 텍스트로 변환합니다."""
    temp_wav = None
    try:
        # 현재 시간을 이용한 고유한 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_wav = f"temp_audio_{timestamp}.wav"
        
        # 오디오 데이터 검증
        if not audio_bytes:
            print("[ERROR] 오디오 데이터가 없습니다.")
            return None, None
            
        try:
            # WAV 파일로 저장
            with open(temp_wav, 'wb') as f:
                f.write(audio_bytes)
            
            # 파일 크기 확인
            if os.path.getsize(temp_wav) < 100:
                print("[ERROR] 오디오 파일이 너무 작습니다.")
                return None, None
                
        except Exception as e:
            print(f"[ERROR] WAV 파일 저장 중 오류: {str(e)}")
            return None, None
            
        # 음성을 텍스트로 변환
        r = sr.Recognizer()
        
        with sr.AudioFile(temp_wav) as source:
            print("[INFO] 오디오 파일 읽기 시작...")
            # 노이즈 조정
            r.adjust_for_ambient_noise(source, duration=0.2)
            # 음성 데이터 읽기
            r.energy_threshold = 100
            r.dynamic_energy_threshold = True
            
            print("[INFO] 음성 데이터 읽기 중...")
            audio_data = r.record(source)
            print("[INFO] 음성 데이터 읽기 완료")
            
            # 한국어 우선 시도 후 영어 시도
            languages = ['ko-KR', 'en-US']
            text = None
            for language in languages:
                try:
                    print(f"[INFO] {language} 인식 시도 중...")
                    text = r.recognize_google(
                        audio_data,
                        language=language,
                        show_all=False
                    )
                    if text:
                        print(f"[SUCCESS] 음성 인식 성공 ({language}): {text}")
                        break
                except sr.UnknownValueError:
                    print(f"[WARNING] {language} 인식 실패")
                    continue
                except sr.RequestError as e:
                    print(f"[ERROR] Google API 요청 오류 ({language}): {str(e)}")
                    continue
            
            if not text:
                print("[ERROR] 모든 언어 인식 시도 실패")
                return None, None
        
        # 감정 분석
        print("[INFO] 감정 분석 시작...")
        emotion = get_emotion_from_gpt(text)
        print(f"[INFO] 감정 분석 결과: {emotion}")
        
        return text, emotion
        
    except Exception as e:
        print(f"[ERROR] 오디오 처리 중 오류 발생: {str(e)}")
        import traceback
        print(f"[ERROR] 상세 오류: {traceback.format_exc()}")
        return None, None
        
    finally:
        # 임시 파일 정리
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
                print(f"[INFO] 임시 파일 삭제 완료: {temp_wav}")
            except Exception as e:
                print(f"[WARNING] 임시 파일 삭제 중 오류 발생: {str(e)}")

def render_chat_area():
    """채팅 영역을 렌더링합니다."""
    st.title("채팅")

    # 세션 상태 초기화
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'audio_bytes' not in st.session_state:
        st.session_state.audio_bytes = None
    if 'processed_audio' not in st.session_state:
        st.session_state.processed_audio = False

    # 스타일 적용
    apply_chat_styles()
    
    # 메시지 컨테이너
    messages_container = st.container()
    with messages_container:
        for message in st.session_state.messages:
            display_message(message, persona=st.session_state.selected_persona)

    # 채팅 입력 처리
    col1, col2, col3 = st.columns([8, 1.2, 1.2])
    
    with col1:
        chat_input = st.text_input("메시지를 입력하세요...", key="chat_input", label_visibility="collapsed")
    
    with col2:
        # 오디오 녹음 컴포넌트
        new_audio_bytes = audio_recorder(
            text="",
            recording_color="#e8b62c",
            neutral_color="#6aa36f",
            icon_name="microphone",
            icon_size="2x",
            pause_threshold=60.0,
            key="audio_recorder_stable"
        )
        
        # 새로운 오디오가 녹음되었을 때
        if new_audio_bytes is not None:
            # 이전 오디오와 다른 경우에만 처리
            if new_audio_bytes != st.session_state.audio_bytes and not st.session_state.processed_audio:
                st.session_state.audio_bytes = new_audio_bytes
                st.session_state.processed_audio = True
                
                with st.spinner("음성을 처리하는 중..."):
                    try:
                        # 음성 처리 및 텍스트 변환
                        audio_text, audio_emotion = process_recorded_audio(new_audio_bytes)
                        
                        if audio_text and audio_emotion:
                            # 현재 상태 저장
                            current_persona = st.session_state.selected_persona
                            
                            # GPT 응답 생성
                            response = st.session_state.chatbot_service.get_response(audio_text, current_persona)
                            
                            # 대화 통계 업데이트
                            update_conversation_stats(audio_emotion)
                            
                            # 메시지 추가
                            add_chat_message("user", f"[음성] {audio_text}", audio_emotion)
                            add_chat_message("assistant", response)
                            
                            # 상태 업데이트
                            st.session_state.current_emotion = audio_emotion
                            st.session_state.last_message = audio_text
                            
                            # 처리 완료 후 상태 초기화
                            st.session_state.processed_audio = False
                            st.session_state.audio_bytes = None
                            
                            # 화면 갱신을 위한 플래그 설정
                            st.session_state.need_rerun = True
                        else:
                            st.error("음성을 텍스트로 변환할 수 없습니다. 다시 시도해주세요.")
                            st.session_state.processed_audio = False
                            st.session_state.audio_bytes = None
                    except Exception as e:
                        st.error(f"음성 처리 중 오류가 발생했습니다: {str(e)}")
                        st.session_state.processed_audio = False
                        st.session_state.audio_bytes = None
    
    with col3:
        send_clicked = st.button("전송", use_container_width=True)
    
    # 텍스트 입력 처리
    if (send_clicked or chat_input) and chat_input.strip() and chat_input != st.session_state.get('last_message'):
        try:
            current_persona = st.session_state.selected_persona
            user_emotion, response = handle_chat_message(chat_input, current_persona)
            update_conversation_stats(user_emotion)
            add_chat_message("user", chat_input, user_emotion)
            add_chat_message("assistant", response)
            st.session_state.current_emotion = user_emotion
            st.session_state.last_message = chat_input
            st.session_state.need_rerun = True
        except Exception as e:
            st.error(f"메시지 처리 중 오류가 발생했습니다: {str(e)}")
    
    # 화면 갱신이 필요한 경우
    if st.session_state.get('need_rerun', False):
        st.session_state.need_rerun = False
        time.sleep(0.1)  # 상태 업데이트를 위한 짧은 대기
        st.rerun()

def render_chat_page():
    """채팅 페이지를 렌더링합니다."""
    # URL에서 영어 페소나 이름 가오기
    persona_url = st.query_params.get("persona")
    
    # 페르소나가 없으면 홈으로 리다이렉트
    if not persona_url:
        st.query_params["page"] = "home"
        st.rerun()
        return
    
    # URL의 영어 이름 한글 페르소나 이름으로 변
    selected_persona = PERSONA_NAME_MAPPING.get(persona_url, DEFAULT_PERSONA)
    
    # 페르소나가 변경되었거나 초기화되지 않은 경우에만 상태 초기화
    if (not st.session_state.get('initialized') or 
        st.session_state.get('selected_persona') != selected_persona):
        # 채팅 기록 유지를 위한 임시 저장
        old_messages = st.session_state.get('messages', [])
        
        # 상태 초기화
        clear_session_state()
        
        # 새운 페르소나로 초기화
        initialize_session_state(selected_persona)
        
        # 이전 채팅 기록 복원 (필한 경우)
        if old_messages and st.session_state.get('selected_persona') == selected_persona:
            st.session_state.messages = old_messages
    
    # URL 파라미터 설정
    st.query_params["page"] = "chat"
    st.query_params["persona"] = persona_url
    
    render_sidebar()
    render_chat_area()

def render_sidebar():
    """사이드바를 렌더링합니다."""
    with st.sidebar:
        st.title("감정인식 챗봇 🏠")
        
        # 홈으로 돌아가기 버튼
        if st.button("← 다른 페르소나 선택하기", key="change_persona_button"):
            # 세션 상태 완전 초기화
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # URL 파라미터 초기화
            for param in list(st.query_params.keys()):
                del st.query_params[param]
            
            # 홈 페이지로 이동하기 위한 파라터 설정
            st.query_params["page"] = "home"
            st.rerun()
            return

        st.markdown("### 사용 방법")
        st.markdown("""
        1. 채팅창에 현재 기분이나 상을 입력하요.
        2. 마이크 버튼을 눌러 음성으로 대화할 수 있습니다.
        3. 챗봇이 감정을 분석하고 공감적인 대화를 제공합니다.
        4. 필요한 경 적한 조언이나 위로를 받을 수 있습니다.
        """)

        # 현 페르소나 표시
        current_persona = st.session_state.get('selected_persona', st.query_params.get("persona"))
        st.markdown(f"### 현재 대 상대: {current_persona}")

        # 상태 초기 및 표시
        ensure_state_initialization('current_emotion', DEFAULT_EMOTION)
        ensure_state_initialization('conversation_stats', {'total': 0, 'positive': 0, 'negative': 0})
        render_emotion_indicator(st.session_state.current_emotion)
        render_conversation_stats(st.session_state.conversation_stats)

def main():
    """메 플리케이션을 실행합니다."""
    # 페이지 설정
    st.set_page_config(
        page_title="감정인식 챗봇",
        page_icon="🤗",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 페재 페이지 확
    current_page = st.query_params.get("page", "home")
    
    # 페이지 라우팅
    if current_page == "chat":
        render_chat_page()
    else:
        from src.app.home import render_home
        render_home()

if __name__ == "__main__":
    main()
