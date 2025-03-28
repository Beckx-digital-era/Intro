document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('top-chat-container');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    
    // Check if chat elements exist on this page
    if (!chatContainer || !messageInput) {
        console.log('Chat interface not found on this page');
        return; // Exit early if chat interface is not on this page
    }
    
    const typingIndicator = document.createElement('div');
    
    // Set up typing indicator
    typingIndicator.className = 'message ai-message typing-indicator';
    typingIndicator.innerHTML = `
        <span></span>
        <span></span>
        <span></span>
    `;
    typingIndicator.style.display = 'none';
    
    // Function to add a message to the chat
    function addMessage(content, isUser) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
        
        // Process message content for code blocks and newlines
        let processedContent = content;
        if (content.includes('```')) {
            processedContent = processCodeBlocks(content);
        } else {
            // If no code blocks, just convert newlines to HTML line breaks
            processedContent = content.replace(/\n/g, '<br>');
        }
        
        messageElement.innerHTML = processedContent;
        chatContainer.appendChild(messageElement);
        
        // Scroll to the bottom of the chat
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Process code blocks in the message
    function processCodeBlocks(content) {
        // First convert newlines to HTML line breaks
        let processedContent = content.replace(/\n/g, '<br>');
        
        // Then replace markdown code blocks with HTML
        return processedContent.replace(/```(\w*)([\s\S]*?)```/g, '<pre><code class="$1">$2</code></pre>');
    }
    
    // Function to show typing indicator
    function showTypingIndicator() {
        chatContainer.appendChild(typingIndicator);
        typingIndicator.style.display = 'flex';
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Function to hide typing indicator
    function hideTypingIndicator() {
        typingIndicator.style.display = 'none';
        if (typingIndicator.parentNode === chatContainer) {
            chatContainer.removeChild(typingIndicator);
        }
    }
    
    // Function to send a message to the server
    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, true);
        
        // Clear input
        messageInput.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send message to server
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide typing indicator
            hideTypingIndicator();
            
            // Add AI response to chat
            addMessage(data.response, false);
        })
        .catch(error => {
            console.error('Error:', error);
            hideTypingIndicator();
            addMessage('Sorry, there was an error processing your request. Please try again.', false);
        });
    }
    
    // Event listeners - only add if elements exist
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    }
    
    if (messageInput) {
        messageInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                sendMessage();
            }
        });
    }
    
    // Load chat history
    function loadChatHistory() {
        fetch('/api/chat/history')
            .then(response => response.json())
            .then(data => {
                // Clear existing messages
                while (chatContainer.firstChild) {
                    chatContainer.removeChild(chatContainer.firstChild);
                }
                
                // Add messages from history
                if (data.messages && Array.isArray(data.messages)) {
                    data.messages.forEach(msg => {
                        // Check if message has required properties
                        if (msg && typeof msg.content === 'string' && typeof msg.isUser !== 'undefined') {
                            addMessage(msg.content, msg.isUser);
                        }
                    });
                    
                    // If no messages, add a welcome message
                    if (data.messages.length === 0) {
                        addMessage('✨ Welcome to the DevOps Control Center! ✨\n\nI\'m your AI assistant, the central control for all operations between GitHub and GitLab. Try commands like:\n• "Sync Beckx-digital-era/Intro repository to GitLab"\n• "Set up CI/CD pipeline for the project"\n• "Deploy the application to production"\n\nHow can I help you today?', false);
                    }
                } else {
                    // If messages is not an array, add a welcome message
                    addMessage('✨ Welcome to the DevOps Control Center! ✨\n\nI\'m your AI assistant, the central control for all operations between GitHub and GitLab. Try commands like:\n• "Sync Beckx-digital-era/Intro repository to GitLab"\n• "Set up CI/CD pipeline for the project"\n• "Deploy the application to production"\n\nHow can I help you today?', false);
                }
            })
            .catch(error => {
                console.error('Error loading chat history:', error);
                addMessage('✨ Welcome to the DevOps Control Center! ✨\n\nI\'m your AI assistant, the central control for all operations between GitHub and GitLab. Try commands like:\n• "Sync Beckx-digital-era/Intro repository to GitLab"\n• "Set up CI/CD pipeline for the project"\n• "Deploy the application to production"\n\nHow can I help you today?', false);
            });
    }
    
    // Load chat history on page load
    loadChatHistory();
});
