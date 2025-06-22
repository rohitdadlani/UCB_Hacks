// App.js
// To run this React App:
// 1. Make sure you have Node.js and npm installed.
// 2. Create a new React project: npx create-react-app legal-aid-frontend
// 3. Navigate into the project directory: cd legal-aid-frontend
// 4. Replace the content of `src/App.js` with this code.
// 5. Replace the content of `src/index.css` with the Tailwind CSS imports.
// 6. Install Tailwind CSS: npm install -D tailwindcss && npx tailwindcss init
//    (Follow the official Tailwind CSS guide for Create React App for full setup)
// 7. Install lucide-react for icons: npm install lucide-react
// 8. Start the app: npm start
// NOTE: Make sure the Python backend is running on http://localhost:8000

import React, { useState, useEffect, useRef } from 'react';
import { FileText, Paperclip, Send, Folder, PlusCircle, Loader2 } from 'lucide-react';

// --- Configuration ---
const API_BASE_URL = 'http://localhost:8000';

// --- Main App Component ---
export default function App() {
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/cases`, { mode: 'cors' });
      if (!response.ok) {
        throw new Error('Failed to fetch cases from the backend.');
      }
      const data = await response.json();
      setCases(data);
      if (data.length > 0) {
        setSelectedCase(data[0]);
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCase = async () => {
    const newCaseName = prompt("Enter a name for the new case:");
    if (newCaseName && newCaseName.trim() !== "") {
      try {
        const response = await fetch(`${API_BASE_URL}/api/cases`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newCaseName }),
          mode: 'cors',
        });
        if (!response.ok) throw new Error('Failed to create case.');
        const newCase = await response.json();
        setCases([...cases, newCase]);
        setSelectedCase(newCase);
      } catch (err) {
        alert("Error: " + err.message);
      }
    }
  };
  
  const handleSelectCase = (caseData) => {
    setSelectedCase(caseData);
  }

  // This function will be passed down to the ChatPanel to update the state
  const updateCaseData = (caseId, updatedData) => {
      setCases(prevCases => prevCases.map(c => 
          c.id === caseId ? { ...c, ...updatedData } : c
      ));
      setSelectedCase(prevSelectedCase => 
          prevSelectedCase.id === caseId ? { ...prevSelectedCase, ...updatedData } : prevSelectedCase
      );
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading cases..."/>;
  }

  if (error) {
    return <ErrorMessage message={error} />;
  }

  return (
    <div className="bg-gray-100 font-sans h-screen flex">
      {/* Sidebar for Cases */}
      <aside className="bg-white w-1/3 max-w-sm border-r border-gray-200 flex flex-col">
        <header className="p-4 border-b border-gray-200 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-800">Legal Case Assistant</h1>
        </header>
        <div className="flex-grow overflow-y-auto">
          {cases.map((caseItem) => (
            <div
              key={caseItem.id}
              onClick={() => handleSelectCase(caseItem)}
              className={`p-4 border-b border-gray-200 cursor-pointer flex items-center gap-3 ${
                selectedCase?.id === caseItem.id ? 'bg-blue-50' : 'hover:bg-gray-50'
              }`}
            >
              <Folder className={`w-6 h-6 ${selectedCase?.id === caseItem.id ? 'text-blue-600' : 'text-gray-500'}`} />
              <div>
                <p className={`font-semibold ${selectedCase?.id === caseItem.id ? 'text-blue-700' : 'text-gray-800'}`}>{caseItem.name}</p>
                <p className="text-sm text-gray-500">{new Date(caseItem.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          ))}
        </div>
        <footer className="p-4 border-t border-gray-200">
            <button 
                onClick={handleCreateCase}
                className="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-blue-700 transition duration-200 flex items-center justify-center gap-2">
                <PlusCircle className="w-5 h-5"/>
                Create New Case
            </button>
        </footer>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">
        {selectedCase ? (
            <CaseDetailPanel caseData={selectedCase} updateCaseData={updateCaseData} />
        ) : (
            <div className="flex-1 flex justify-center items-center text-gray-500">
                <p>Select a case to view details or create a new one.</p>
            </div>
        )}
      </main>
    </div>
  );
}

// --- Child Components ---

const CaseDetailPanel = ({ caseData, updateCaseData }) => {
    return (
        <div className="flex flex-1 overflow-hidden">
            {/* Chat Panel */}
            <div className="flex-1 flex flex-col bg-white">
                <header className="p-4 border-b border-gray-200">
                    <h2 className="text-lg font-bold text-gray-800">{caseData.name}</h2>
                </header>
                <ChatPanel caseData={caseData} updateCaseData={updateCaseData} />
            </div>
            {/* Documents Panel */}
            <aside className="w-1/3 max-w-xs bg-gray-50 border-l border-gray-200 flex flex-col">
                 <header className="p-4 border-b border-gray-200">
                    <h3 className="text-md font-bold text-gray-700">Case Documents</h3>
                </header>
                <DocumentPanel caseData={caseData} updateCaseData={updateCaseData} />
            </aside>
        </div>
    );
};


const ChatPanel = ({ caseData, updateCaseData }) => {
  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatContainerRef = useRef(null);
  
  useEffect(() => {
    // Scroll to bottom when new messages are added
    if (chatContainerRef.current) {
        chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [caseData.chat_history]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || isTyping) return;

    const userMessage = {
        id: Date.now(), // temporary id
        sender: 'user',
        content: newMessage,
        timestamp: new Date().toISOString()
    };
    
    // Optimistically update UI
    updateCaseData(caseData.id, { chat_history: [...caseData.chat_history, userMessage] });
    setNewMessage('');
    setIsTyping(true);

    try {
        const response = await fetch(`${API_BASE_URL}/api/cases/${caseData.id}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: newMessage }),
            mode: 'cors',
        });
        if (!response.ok) throw new Error('Failed to send message.');
        const agentResponse = await response.json();

        // Replace optimistic update with final data
         updateCaseData(caseData.id, { chat_history: [...caseData.chat_history, userMessage, agentResponse] });

    } catch (err) {
        const errorResponse = {
            id: Date.now(),
            sender: 'agent',
            content: `Error: ${err.message}. Please check if the backend is running.`,
            timestamp: new Date().toISOString()
        };
        updateCaseData(caseData.id, { chat_history: [...caseData.chat_history, userMessage, errorResponse] });
    } finally {
        setIsTyping(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div ref={chatContainerRef} className="flex-1 p-6 overflow-y-auto space-y-6">
        {caseData.chat_history.map((msg, index) => (
          <div key={msg.id || index} className={`flex items-end gap-3 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
            {msg.sender === 'agent' && <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold text-sm">A</div>}
            <div
              className={`max-w-md p-3 rounded-2xl ${
                msg.sender === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-gray-200 text-gray-800 rounded-bl-none'
              }`}
            >
              <p>{msg.content}</p>
            </div>
             {msg.sender === 'user' && <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white font-bold text-sm">U</div>}
          </div>
        ))}
         {isTyping && (
          <div className="flex items-end gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold text-sm">A</div>
            <div className="max-w-md p-3 rounded-2xl bg-gray-200 text-gray-800 rounded-bl-none">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
              </div>
            </div>
          </div>
        )}
      </div>
      <form onSubmit={handleSendMessage} className="p-4 bg-white border-t border-gray-200">
        <div className="relative">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder="Type your message..."
            className="w-full bg-gray-100 border-gray-300 rounded-lg py-3 pl-4 pr-12 focus:ring-blue-500 focus:border-blue-500"
            disabled={isTyping}
          />
          <button type="submit" className="absolute inset-y-0 right-0 flex items-center pr-4" disabled={isTyping}>
            <Send className="w-6 h-6 text-blue-600 hover:text-blue-800" />
          </button>
        </div>
      </form>
    </div>
  );
};


const DocumentPanel = ({ caseData, updateCaseData }) => {
    const fileInputRef = useRef(null);
    const [isUploading, setIsUploading] = useState(false);

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/cases/${caseData.id}/documents`, {
                method: 'POST',
                body: formData,
                mode: 'cors',
            });
            if (!response.ok) throw new Error('File upload failed.');
            const newDocument = await response.json();
            
            // The agent adds a confirmation message, so we need to refetch the whole case
            // or get the updated chat history back. The backend currently handles this.
            // Let's refetch the case to get the latest chat history.
            const caseResponse = await fetch(`${API_BASE_URL}/api/cases`, { mode: 'cors' });
            const allCases = await caseResponse.json();
            const updatedCase = allCases.find(c => c.id === caseData.id);
            if (updatedCase) {
                updateCaseData(caseData.id, updatedCase);
            }

        } catch (err) {
            alert(`Error: ${err.message}`);
        } finally {
            setIsUploading(false);
            // Reset file input
            e.target.value = null;
        }
    };
    
    return (
        <div className="flex-1 p-4 overflow-y-auto space-y-4">
             {caseData.documents.map(doc => (
                 <div key={doc.id} className="bg-white p-3 rounded-lg border border-gray-200">
                     <div className="flex items-center gap-3">
                        <FileText className="w-6 h-6 text-indigo-500" />
                        <div>
                            <p className="font-semibold text-gray-800 truncate">{doc.name}</p>
                            <p className="text-sm text-gray-500">
                                {new Date(doc.upload_date).toLocaleDateString()}
                            </p>
                        </div>
                     </div>
                     <p className="text-sm text-gray-600 mt-2 italic">"{doc.summary}"</p>
                 </div>
             ))}
             {caseData.documents.length === 0 && <p className="text-sm text-center text-gray-500 py-4">No documents uploaded.</p>}
            
            <div className="pt-4 mt-auto">
                <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={handleFileChange}
                    disabled={isUploading}
                />
                <button 
                    onClick={() => fileInputRef.current.click()}
                    disabled={isUploading}
                    className="w-full bg-indigo-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-indigo-700 transition duration-200 flex items-center justify-center gap-2 disabled:bg-indigo-300">
                    {isUploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Paperclip className="w-5 h-5"/>}
                    {isUploading ? "Uploading..." : "Upload Document"}
                </button>
            </div>
        </div>
    );
};

// --- Utility Components ---

const LoadingSpinner = ({ message }) => (
  <div className="flex flex-col justify-center items-center h-screen bg-gray-100 text-gray-600">
    <Loader2 className="w-12 h-12 animate-spin text-blue-600 mb-4" />
    <p className="text-lg">{message}</p>
  </div>
);

const ErrorMessage = ({ message }) => (
    <div className="flex flex-col justify-center items-center h-screen bg-red-50 text-red-700 p-4">
        <h2 className="text-2xl font-bold mb-2">Connection Error</h2>
        <p className="text-center">Could not connect to the backend server. Please ensure the Python FastAPI server is running on {API_BASE_URL}.</p>
        <p className="text-sm mt-2 font-mono bg-red-100 p-2 rounded">{message}</p>
  </div>
);
