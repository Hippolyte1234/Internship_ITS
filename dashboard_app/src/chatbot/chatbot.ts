import { ChangeDetectorRef, Component, inject, OnInit } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

export interface ChatMessage {
  role: string;
  content?: string;
  formattedContent?: SafeHtml; // Stores the sanitized HTML string for rendering
  isThinking?: boolean;
}

export interface Session {
  session_id: string;
  title?: string;
}

@Component({
  selector: 'app-chatbot',
  templateUrl: './chatbot.html',
  styleUrls: ['./chatbot.css']
})
export class ChatbotComponent implements OnInit {
  private readonly changeDetector = inject(ChangeDetectorRef);
  chatHistory: ChatMessage[] = [];
  currentSessionId: string | null = null;
  sessions: Session[] = [];
  
  promptInput: string = '';
  isSending: boolean = false; // Replaces btn.disabled

  toastMessage: string = '';
  isToastVisible: boolean = false;

  constructor(private sanitizer: DomSanitizer) {
    // Expose downloadCSV globally so the dynamically injected HTML button can trigger it
    (window as any).downloadCSV = this.downloadCSV.bind(this);
  }

  // Initialize and load historical metadata lists from service instantly on load
  ngOnInit(): void {
    this.loadSessions();
  }

  // Catch Enter key inputs to prevent needing manual button clicks
  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendToOllama();
    }
  }

  setSamplePrompt(promptText: string): void {
    this.promptInput = promptText;
    // Note: Angular template binding will handle focusing if you use an autofocus directive, 
    // or you can rely on standard click flows.
  }

  triggerToast(message: string): void {
    this.toastMessage = message;
    this.isToastVisible = true;
    setTimeout(() => {
      this.dismissToast();
    }, 8000); // clear after 8 seconds
  }

  dismissToast(): void {
    this.isToastVisible = false;
  }

  // Pull previous conversation arrays directly from history_service
  async loadSessions(): Promise<void> {
    try {
      const response = await fetch('http://127.0.0.1:5051/get-sessions');
      if (!response.ok) throw new Error('Could not fetch sessions list');
      
      const data = await response.json();
      this.sessions = data.sessions || [];
      this.changeDetector.markForCheck();
    } catch (err) {
      console.error('Failed to fetch session indexes:', err);
      // Let the HTML template handle displaying the error state if sessions array is empty
      this.sessions = [];
      this.changeDetector.markForCheck();
    }
  }

  // Pull full array logs of single chosen session
  async loadSessionHistory(sessionId: string): Promise<void> {
    this.currentSessionId = sessionId;
    this.chatHistory = []; // Triggers loading state in your HTML template
    
    try {
      const response = await fetch(`http://127.0.0.1:5051/get-session/${sessionId}`);
      if (!response.ok) throw new Error('Could not load history elements');
      
      const data = await response.json();
      const historyData = data.history || [];
      
      this.chatHistory = historyData.map((msg: any) => {
        let rawHtml = '';
        if (msg.role === 'user') {
          rawHtml = `<strong>You:</strong> ${this.escapeHtml(msg.content)}`;
        } else {
          rawHtml = `<strong>AI:</strong> ${this.formatAIResponse(msg.content)}`;
        }
        const tableRecords = msg.result_table_in_json || msg.raw_data;
        if (tableRecords && tableRecords.length > 0) {
          rawHtml += this.renderHtmlTable(tableRecords, msg.query_id);
        }
        
        return {
          ...msg,
          formattedContent: this.sanitizer.bypassSecurityTrustHtml(rawHtml)
        };
      });
      this.changeDetector.markForCheck();

      // The selected item is already highlighted through currentSessionId; avoid a redundant refetch.
      this.changeDetector.markForCheck();
      this.scrollToBottom();

    } catch (err) {
      console.error('Failed to load historical session elements:', err);
      // Render the error state message
      this.chatHistory = [{
        role: 'system',
        formattedContent: this.sanitizer.bypassSecurityTrustHtml(`
          <div class="empty-state">
            <p style="color: #ef4444; font-weight: 600;">Could not retrieve log details</p>
          </div>
        `)
      }];
    }
      this.changeDetector.markForCheck();
  }

  // Resets current session trackers instantly
  startNewChat(): void {
    this.currentSessionId = null;
    this.chatHistory = [];
    this.promptInput = '';
  }

  async sendToOllama(): Promise<void> {
    const userPrompt = this.promptInput.trim();
    
    if (!userPrompt) {
      return; // Guard against empty submits
    }

    // 2. Append User Prompt using clean native styles
    this.chatHistory.push({
      role: 'user',
      content: userPrompt,
      formattedContent: this.sanitizer.bypassSecurityTrustHtml(`<strong>You:</strong> ${this.escapeHtml(userPrompt)}`)
    });

    // 3. Create a temporary italicized loading element
    this.chatHistory.push({
      role: 'assistant',
      isThinking: true,
      formattedContent: this.sanitizer.bypassSecurityTrustHtml(`<strong>AI:</strong> <span class="thinking">Thinking...</span>`)
    });

    const thinkingIndex = this.chatHistory.length - 1;

    // Instantly force layout repaint and align scroll container down
    this.scrollToBottom();

    // Brief yield block
    await new Promise(resolve => setTimeout(resolve, 50));

    this.promptInput = '';
    this.isSending = true;

    try {
      // Fetch to local Flask gateway pipeline server
      // Note: We filter out the temporary 'thinking' message before sending history
      const historyToSend = this.chatHistory
        .filter(msg => !msg.isThinking)
        .map(msg => ({ role: msg.role, content: msg.content }));

      const response = await fetch('http://127.0.0.1:5050/ask-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          history: historyToSend,
          session_id: this.currentSessionId
        })
      });

      if (!response.ok) {
        throw new Error(`Pipeline returned connection status: ${response.status}`);
      }

      // Capture response as raw text to prevent the browser parser from crashing on non-standard JSON tokens
      const responseRawText = await response.text();

      // Regex replacement maps illegal standalone NaN float values to safe standard JSON nulls
      const sanitizedJsonText = responseRawText.replace(/\bNaN\b/g, 'null');

      // Safely parse the valid JSON text
      const data = JSON.parse(sanitizedJsonText);
      console.log('Database Response Data (Sanitized):', data);

      if (data.session_id) {
        console.log(data.session_id);
        this.currentSessionId = data.session_id;
      }

      let aiReply = '';
      let rawRecords: any[] = [];
      let queryId = ''; // Track our backend cache reference ID instead of raw SQL

      if (data.message) {
        aiReply = data.message.content || '';
        rawRecords = data.message.raw_data || [];
        queryId = data.message.query_id || ''; // Extract the reference cache ID
      }
      console.log('--> THE EXTRACTED QUERY ID IS:', queryId);

      // 4. Locate temporary loading element and inject clean formatted outputs
      let finalHTML = `<strong>AI:</strong> ${this.formatAIResponse(aiReply)}`;

      // Render raw datasets in a simple visual grid table if rows exist
      if (rawRecords && rawRecords.length > 0) {
        finalHTML += this.renderHtmlTable(rawRecords, queryId);
      }

      // Replace the temporary 'Thinking...' message in-place with the real response
      const updatedHistory = [...this.chatHistory];
      updatedHistory[thinkingIndex] = {
        role: 'assistant',
        content: aiReply,
        formattedContent: this.sanitizer.bypassSecurityTrustHtml(finalHTML)
      };
      this.chatHistory = updatedHistory;

      this.changeDetector.markForCheck(); // Trigger UI update after replacing "Thinking..."
      this.scrollToBottom();

    } catch (error) {
      console.error('Pipeline failure:', error);
      const updatedHistory = [...this.chatHistory];
      updatedHistory[thinkingIndex] = {
        role: 'assistant',
        formattedContent: this.sanitizer.bypassSecurityTrustHtml(`<strong>AI:</strong> <span style="color: red; font-weight: bold;">Pipeline failure. Please check python console log outputs.</span>`)
      };
      this.chatHistory = updatedHistory;
      
      this.changeDetector.markForCheck(); // Trigger UI update on error
    } finally {
      this.isSending = false;
      this.changeDetector.markForCheck(); // Ensure button re-enables
    }
  }

  // Simple Markdown Code Block Converter to display high visual output
  formatAIResponse(text: string): string {
    if (!text) return '';
    let escaped = this.escapeHtml(text);

    // 1. Process bold markdown elements (**text**)
    escaped = escaped.replace(/\*\*([\s\S]*?)\*\*/g, '<strong class="text-indigo-400 font-semibold">$1</strong>');

    // 2. Convert standard code wrappers (```sql ... ```) to styling boxes
    escaped = escaped.replace(/```sql([\s\S]*?)```/g, (match, code) => {
      return `
        <div class="my-3 border border-slate-800 rounded-xl overflow-hidden shadow-md">
          <div class="bg-slate-950/80 px-4 py-2 border-b border-slate-800 flex justify-between items-center text-xs text-slate-400 font-mono">
            <span>PostgreSQL Statement</span>
            <span class="text-[10px] text-indigo-400 px-1.5 py-0.5 rounded bg-indigo-950/60 border border-indigo-900/50">SQL</span>
          </div>
          <pre class="bg-slate-950 p-4 overflow-x-auto text-xs font-mono text-emerald-400 leading-relaxed"><code>${code.trim()}</code></pre>
        </div>
      `;
    });

    // Fallback for non-language specific blocks
    escaped = escaped.replace(/```([\s\S]*?)```/g, (match, code) => {
      return `<pre class="bg-slate-950 border border-slate-800 rounded-xl p-4 my-3 overflow-x-auto text-xs font-mono text-slate-300">${code.trim()}</pre>`;
    });

    // Convert line breaks correctly
    escaped = escaped.split('\n').join('<br>');

    return escaped;
  }

  // Dynamically creates interactive scrollable HTML table layouts from JSON
  renderHtmlTable(records: any[], queryId: string): string {
    if (!records || !Array.isArray(records) || records.length === 0) return '';

    const validRecords = records.filter(r => r && typeof r === 'object');
    if (validRecords.length === 0) return '';

    const columns = Object.keys(validRecords[0]);

    let tableHeader = '<tr>';
    columns.forEach(col => {
      tableHeader += `<th>${this.escapeHtml(col)}</th>`;
    });
    tableHeader += '</tr>';

    let tableRows = '';
    validRecords.forEach(row => {
      tableRows += '<tr>';
      columns.forEach(col => {
        const cellVal = row[col];
        let displayValue = '';
        if (cellVal === null || cellVal === undefined) {
          displayValue = '<span style="color: #94a3b8; font-style: italic;">NULL</span>';
        } else if (typeof cellVal === 'object') {
          displayValue = this.escapeHtml(JSON.stringify(cellVal));
        } else {
          displayValue = this.escapeHtml(String(cellVal));
        }
        tableRows += `<td>${displayValue}</td>`;
      });
      tableRows += '</tr>';
    });

    // If a valid Query ID is present, construct the download button using the ID string directly
    let csvButtonHTML = '';
    if (queryId) {
      // Changed slightly to call the window-bound downloadCSV function
      csvButtonHTML = `
        <button onclick="window.downloadCSV('${queryId}')" style="background-color: #10b981; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: background-color 0.15s;" onmouseover="this.style.backgroundColor='#059669'" onmouseout="this.style.backgroundColor='#10b981'">
          Download Full CSV
        </button>
      `;
    }

    return `
      <div style="margin-top: 15px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
          <strong style="color: #1e3a8a; margin: 0;">Query Output Records (Previewing top 10):</strong>
          ${csvButtonHTML}
        </div>
        <div class="table-container">
          <table>
            <thead>${tableHeader}</thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
      </div>
    `;
  }

  // Prevent injection and cross site scripting
  escapeHtml(str: string): string {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Action helper routing cache requests to your gateway backend endpoint
  downloadCSV(queryId: string): void {
    if (!queryId) return;
    const downloadUrl = `http://127.0.0.1:5050/download-csv?id=${queryId}`;
    window.open(downloadUrl, '_blank');
  }

  // Helper method to keep scroll at bottom 
  private scrollToBottom(): void {
    setTimeout(() => {
      const responseBox = document.getElementById('responseBox');
      if (responseBox) {
        responseBox.scrollTop = responseBox.scrollHeight;
      }
    }, 50);
  }
}