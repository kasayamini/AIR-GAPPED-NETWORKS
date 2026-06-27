const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL)
    ? import.meta.env.VITE_API_URL.replace(/\/$/, '')
    : 'https://air-gapped-networks.onrender.com';

export class ChatPanel {
    constructor(containerId) {
        this.containerId = containerId;
        this.isOpen = true;
        this.chatHistory = [];
        this.isStreaming = false;
        this.currentMessage = '';
    }

    async render(context = {}) {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        const messages = this.chatHistory.slice(-8).map(message => this.renderMessage(message)).join('');
        const status = context.network_status || 'Waiting for system context';
        const systemSummary = context.summary || 'Telemetry and RCA context will appear here once data flows.';

        container.innerHTML = `
            <div class="chat-panel ${this.isOpen ? 'open' : 'closed'}">
                <div class="chat-panel-header">
                    <div>
                        <h2>AI NOC Copilot</h2>
                        <p>${status}</p>
                    </div>
                    <button class="chat-toggle-btn" id="chat-toggle-btn">${this.isOpen ? 'Hide' : 'Show'}</button>
                </div>
                <div class="chat-panel-body">
                    <div class="chat-system-context">
                        <div class="context-header">Live Insight Context</div>
                        <pre>${this.escapeHtml(systemSummary)}</pre>
                    </div>
                    <div class="chat-messages" id="chat-messages">${messages || '<div class="chat-empty">Ask the assistant about alerts, incidents, and network issues.</div>'}</div>
                </div>
                <form class="chat-input-panel" id="chat-input-panel">
                    <textarea id="chat-input" placeholder="Ask about latency, packet loss, incidents, or troubleshooting..." rows="2"></textarea>
                    <div class="chat-controls">
                        <button type="button" class="secondary-btn" id="chat-clear-btn">Clear Chat</button>
                        <button type="submit" class="primary-btn" id="chat-send-btn">Send</button>
                    </div>
                </form>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        const toggleButton = document.getElementById('chat-toggle-btn');
        const form = document.getElementById('chat-input-panel');
        const clearButton = document.getElementById('chat-clear-btn');
        const textarea = document.getElementById('chat-input');

        if (toggleButton) {
            toggleButton.onclick = () => {
                this.isOpen = !this.isOpen;
                this.render();
            };
        }

        if (form) {
            form.onsubmit = async (event) => {
                event.preventDefault();
                const question = textarea.value.trim();
                if (!question || this.isStreaming) return;
                textarea.value = '';
                await this.submitQuestion(question);
            };
        }

        if (clearButton) {
            clearButton.onclick = () => this.clearChat();
        }

        if (textarea) {
            textarea.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                    event.preventDefault();
                    form.requestSubmit();
                }
            });
        }
    }

    async loadHistory() {
        try {
            const response = await fetch(`${API_BASE}/api/chat/history`);
            if (response.ok) {
                this.chatHistory = await response.json();
            }
        } catch (error) {
            console.error('Unable to load chat history:', error);
        }
    }

    async submitQuestion(question) {
        this.appendMessage('user', question);
        this.isStreaming = true;
        this.currentMessage = '';
        this.appendMessage('assistant', '', true);

        try {
            const controller = new AbortController();
            const response = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: question }),
                signal: controller.signal
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Chat request failed');
            }

            const data = await response.json();
            const reply = data && typeof data.reply === 'string' ? data.reply : JSON.stringify(data);
            this.updateAssistantMessage(reply);
        } catch (error) {
            const errorMessage = error?.message || 'Chat request failed';
            this.updateAssistantMessage(`Unable to get assistant response: ${errorMessage}`);
            console.error('Chat request failed:', error);
        } finally {
            this.isStreaming = false;
            this.currentMessage = '';
        }
    }

    renderMessage(message) {
        const roleClass = message.role === 'assistant' ? 'assistant-bubble' : 'user-bubble';
        const content = this.escapeHtml(message.content).replace(/\n/g, '<br/>').replace(/```([\s\S]*?)```/g, '<pre class="code-block"><code>$1</code></pre>');
        return `
            <div class="chat-message ${roleClass}">
                <div class="chat-message-role">${message.role === 'assistant' ? 'NOC Copilot' : 'You'}</div>
                <div class="chat-message-content">${content}</div>
            </div>
        `;
    }

    updateAssistantMessage(content) {
        const messagesElement = document.getElementById('chat-messages');
        if (!messagesElement) return;
        const assistantIndex = this.chatHistory.findIndex(msg => msg.role === 'assistant' && msg.streaming);
        if (assistantIndex !== -1) {
            this.chatHistory[assistantIndex].content = content;
        }
        messagesElement.innerHTML = this.chatHistory.slice(-8).map(message => this.renderMessage(message)).join('');
        messagesElement.scrollTop = messagesElement.scrollHeight;
    }

    appendMessage(role, content, streaming = false) {
        if (role === 'assistant' && streaming) {
            this.chatHistory.push({ role, content, streaming: true });
        } else {
            this.chatHistory.push({ role, content, streaming: false });
        }
        this.render();
    }

    clearChat() {
        this.chatHistory = [];
        this.render();
    }

    escapeHtml(value) {
        return value
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }
}
