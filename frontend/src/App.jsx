import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

// 다운로드 로직: JSON 데이터를 CSV 파일로 변환하여 다운로드
const downloadCSV = (data, filename = 'chatbot_result.csv') => {
  if (!data || data.length === 0) {
    alert("다운로드할 데이터가 없습니다.");
    return;
  }
  // 데이터가 객체의 배열이 아니면 중단
  if (typeof data[0] !== 'object' || data[0] === null) {
    alert("테이블 형식의 데이터가 아니므로 다운로드할 수 없습니다.");
    return;
  }

  const headers = Object.keys(data[0]);
  const csvRows = [headers.join(',')]; // 헤더 생성

  for (const row of data) {
    const values = headers.map(header => {
      const escaped = ('' + row[header]).replace(/"/g, '""'); // 쌍따옴표 처리
      return `"${escaped}"`;
    });
    csvRows.push(values.join(',')); // 데이터 행 추가
  }

  const csvString = csvRows.join('\n');
  const blob = new Blob([`\uFEFF${csvString}`], { type: 'text/csv;charset=utf-8;' }); // UTF-8 BOM 추가
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};


function App() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [size, setSize] = useState({ width: 400, height: 500 }); // 채팅창 크기 상태
  const chatWindowRef = useRef(null); // 채팅창 DOM 참조

  // 창 크기 조절 로직
  const handleMouseDown = (e) => {
    e.preventDefault();
    const startSize = size;
    const startPosition = { x: e.clientX, y: e.clientY };

    function handleMouseMove(e) {
      const newWidth = startSize.width + e.clientX - startPosition.x;
      const newHeight = startSize.height + e.clientY - startPosition.y;
      setSize({ 
        width: newWidth > 300 ? newWidth : 300, // 최소 너비 300px
        height: newHeight > 200 ? newHeight : 200 // 최소 높이 200px
      });
    }

    function handleMouseUp() {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    }

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  // 메시지 전송 및 API 호출 로직
  const handleSendMessage = async () => {
    if (!userInput.trim() || isLoading) return;

    const newUserMessage = { sender: 'user', text: userInput };
    setMessages(prev => [...prev, newUserMessage]);
    setIsLoading(true);
    
    try {
      const response = await axios.post('/api/bot', { question: userInput });
      const responseData = response.data;
      
      let botText = "결과를 확인하세요."; // 기본 텍스트
      let botData = null;

      // 백엔드 응답 구조에 따라 텍스트와 데이터 분리
      if (responseData) {
        // 'answer' 필드가 있으면 그것을 주된 텍스트 응답으로 사용
        if (responseData.answer) {
          botText = responseData.answer;
        }
        // 'db_result' 필드가 배열이면 다운로드용 데이터로 할당
        if (responseData.db_result && Array.isArray(responseData.db_result)) {
          botData = responseData.db_result;
        } else if (Array.isArray(responseData)) {
          // 응답 자체가 배열이면 그것을 다운로드용 데이터로 할당
          botData = responseData;
        }
      }

      const newBotMessage = {
        sender: 'bot',
        text: botData ? botText : JSON.stringify(responseData, null, 2), // 데이터가 없으면 전체 JSON 표시
        data: botData
      };
      setMessages(prev => [...prev, newBotMessage]);

    } catch (error) {
      const errorMessage = { sender: 'bot', text: "오류가 발생했습니다." };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setUserInput(''); // 입력창 초기화
    }
  };
  
  // 새 메시지가 생길 때마다 채팅창 스크롤을 맨 아래로 이동
  useEffect(() => {
    if (chatWindowRef.current) {
      const chatBox = chatWindowRef.current.querySelector('.chat-box');
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="App">
      {/* 이 곳에 팀원이 만든 대시보드 컴포넌트들을 배치합니다. */}

      <div className="chat-icon" onClick={() => setIsChatOpen(!isChatOpen)}>💬</div>

      <div 
        ref={chatWindowRef}
        className={`chat-window ${isChatOpen ? 'is-open' : ''}`}
        style={{ width: `${size.width}px`, height: `${size.height}px` }}
      >
        <div className="chat-header">RAG 챗봇</div>
        <div className="chat-box">
          {messages.map((msg, index) => (
            <div key={index} className={`message-bubble ${msg.sender}`}>
              <pre>{msg.text}</pre>
              {/* 봇 메시지이고, 다운로드 가능한 데이터가 있을 때만 버튼 표시 */}
              {msg.sender === 'bot' && msg.data && msg.data.length > 0 && (
                <button onClick={() => downloadCSV(msg.data)} className="download-btn">
                  CSV로 저장
                </button>
              )}
            </div>
          ))}
          {isLoading && <div className="loading-indicator">진행중...</div>}
        </div>
        <div className="chat-input">
          <input
            type="text" value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            disabled={isLoading}
            placeholder="질문을 입력하세요..."
          />
          <button onClick={handleSendMessage} disabled={isLoading}>전송</button>
        </div>
        <div className="resize-handle" onMouseDown={handleMouseDown}></div>
      </div>
    </div>
  );
}

export default App;
