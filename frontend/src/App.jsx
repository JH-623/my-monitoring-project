// src/App.jsx
import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  // --- 대시보드 상태 ---
  const [dashboardData] = useState({
    todayCases: 120,
    criticalCases: 15,
    antibioticUsage: '세프트리악손 (75%)'
  });

  // --- 챗봇 상태 ---
  const [isChatOpen, setIsChatOpen] = useState(false); // 챗봇 창 표시 여부 상태
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');

  const handleSendMessage = async () => {
    if (!userInput.trim()) return;
    const newUserMessage = { sender: 'user', text: userInput };
    setMessages(prev => [...prev, newUserMessage]);

    try {
      const response = await axios.post('/api/bot', { question: userInput });
      const botResponseText = JSON.stringify(response.data.db_result, null, 2);
      const newBotMessage = { sender: 'bot', text: botResponseText };
      setMessages(prev => [...prev, newBotMessage]);
    } catch (error) {
      setMessages(prev => [...prev, { sender: 'bot', text: "오류가 발생했습니다." }]);
    } finally {
      setUserInput('');
    }
  };

  return (
    <div className="App">
      {/* 대시보드 영역 */}
      <div className="dashboard">
        <h1>감염병 모니터링 대시보드</h1>
        <p>이곳에 팀원들이 만든 대시보드 HTML/CSS를 적용합니다.</p>
      </div>

      {/* 챗봇 아이콘: 클릭하면 isChatOpen 상태를 반전시킴 */}
      <div className="chat-icon" onClick={() => setIsChatOpen(!isChatOpen)}>
        💬
      </div>

      {/* 챗봇 창: isChatOpen이 true일 때만 'is-open' 클래스를 추가하여 보이게 함 */}
      <div className={`chat-window ${isChatOpen ? 'is-open' : ''}`}>
        <div className="chat-header">RAG 챗봇</div>
        <div className="chat-box">
          {messages.map((msg, index) => (
            <div key={index} className={msg.sender}><pre>{msg.text}</pre></div>
          ))}
        </div>
        <div className="chat-input">
          <input
            type="text" value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          />
          <button onClick={handleSendMessage}>전송</button>
        </div>
      </div>
    </div>
  );
}

export default App;
