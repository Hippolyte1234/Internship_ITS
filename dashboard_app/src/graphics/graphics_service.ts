import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

// Define an interface matching the expected backend chart format
export interface ChartPayload {
  chartType: 'line' | 'bar' | 'pie';
  labels: string[];
  datasets: { data: number[]; label: string }[];
}

@Injectable({
  providedIn: 'root'
})
export class ChartDataService {
  private chartDataSubject = new BehaviorSubject<ChartPayload | null>(null);
  public chartData$: Observable<ChartPayload | null> = this.chartDataSubject.asObservable();

  public currentSessionId: string | null = null;
  public promptInput: string = '';
  public isSending: boolean = false; 
  public toastMessage: string = '';
  public isToastVisible: boolean = false;
  
  // Stores textual responses/refusals when no records are found
  public lastResponseContent: string = ''; 

  // Catch Enter key inputs to prevent needing manual button clicks
  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      // Note: Components should map this to onAskAiClick() or executePipeline directly
    }
  }

  setSamplePrompt(promptText: string): void {
    this.promptInput = promptText;
  }

  triggerToast(message: string): void {
    this.toastMessage = message;
    this.isToastVisible = true;
    setTimeout(() => {
      this.dismissToast();
    }, 8000); // Clear after 8 seconds
  }

  dismissToast(): void {
    this.isToastVisible = false;
  }

  async executePipeline(userPrompt: string): Promise<void> {
    const cleanPrompt = userPrompt.trim();
    if (!cleanPrompt) {
      this.isSending = false;
      return;
    }

    this.promptInput = ''; 
    this.scrollToBottom();
    this.lastResponseContent = '';

    try {
      const response = await fetch('http://127.0.0.1:5052/ask-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: this.currentSessionId,
          prompt: cleanPrompt
        })
      });

      // 1. Intercept network errors (400, 500, etc.) and extract message details
      if (!response.ok) {
        let errorDetails = `Status Code ${response.status}`;
        try {
          const errorData = await response.json();
          errorDetails = errorData.details || errorData.error || errorDetails;
        } catch {
          const rawText = await response.text();
          errorDetails = rawText || errorDetails;
        }
        throw new Error(errorDetails);
      }

      // 2. Process valid server data stream responses
      const responseRawText = await response.text();
      const sanitizedJsonText = responseRawText.replace(/\bNaN\b/g, 'null');
      const data = JSON.parse(sanitizedJsonText);

      console.log('📦 [FRONTEND SERVICE]: Raw data received from Flask:', data);

      if (data.session_id) {
        this.currentSessionId = data.session_id;
      }

      let rawRecords: any[] = [];
      if (data.message) {
        this.lastResponseContent = this.formatAIResponse(data.message.content || '');
        rawRecords = data.message.raw_data || [];
      }

      console.log('📊 [FRONTEND SERVICE]: Extracted raw_data array rows:', rawRecords);

      if (rawRecords && rawRecords.length > 0) {
        const detectedType = data.message?.chart_type || 'line'; 
        const parsedChart = this.parseDatabaseRows(rawRecords, detectedType); 
        
        console.log('🎨 [FRONTEND SERVICE]: Processed ChartPayload Object:', parsedChart);
        this.chartDataSubject.next(parsedChart);
      } else {
        console.warn('⚠️ [FRONTEND SERVICE]: raw_data array is EMPTY. No chart payload generated.');
        this.chartDataSubject.next(null);
      }

      if (data.session_id) {
        this.currentSessionId = data.session_id;
      }


      // 3. Process records array if it contains valid contents
      if (rawRecords && rawRecords.length > 0) {
        const detectedType = data.message?.chart_type || 'line'; 
        const parsedChart = this.parseDatabaseRows(rawRecords, detectedType); 
        if (parsedChart) {
          this.chartDataSubject.next(parsedChart);
        } else {
          this.chartDataSubject.next(null);
        }
      } else {
        // No SQL records generated (AI choice layer rejection path skipped execution)
        this.chartDataSubject.next(null);
      }

      this.scrollToBottom();

    } catch (error: any) {
      console.error('Pipeline intercepted an error:', error);
      const messageToShow = error.message || 'Unknown server database connection error occurred.';
      this.triggerToast(messageToShow);
      this.chartDataSubject.next(null);
    } finally {
      this.isSending = false; 
    }
  }

  // 4. Dynamic Robust Database Parser
  private parseDatabaseRows(rows: any[], chartType: 'line' | 'bar' | 'pie'): ChartPayload | null {
    if (!rows || rows.length === 0) return null;

    let columns = Object.keys(rows[0]);
    let labels: string[] = [];
    let datasets: { data: number[]; label: string }[] = [];

    // 1. SCALAR QUERY CORRECTION: Only one aggregate column returned (e.g., total_students)
    if (columns.length === 1) {
      const activeMetricKey = columns[0];
      labels = ['Total Aggregate Result'];
      datasets = [{
        label: activeMetricKey.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        data: [Number(rows[0][activeMetricKey])]
      }];
    } 
    // 2. MULTI-COLUMN DATA MATRIX PATHWAY
    else {
      const xAxisKey = columns.find(col => {
        const lower = col.toLowerCase();
        return ['year', 'date', 'month', 'dept', 'tanggal', 'periode', 'kode', 'tahun'].some(keyword => lower.includes(keyword));
      }) || columns[0];

      const potentialYKeys = columns.filter(col => col !== xAxisKey);
      const yAxisKeys = potentialYKeys.filter(key => {
        const value = rows[0][key];
        if (value === null || value === undefined) return false;
        return typeof value === 'number' || !isNaN(Number(value));
      });

      const activeYKeys = yAxisKeys.length > 0 ? yAxisKeys : potentialYKeys;

      labels = rows.map(row => {
        const val = row[xAxisKey];
        return val instanceof Date ? val.toISOString().split('T')[0] : String(val);
      });

      datasets = activeYKeys.map(key => ({
        label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        data: rows.map(row => Number(row[key]))
      }));
    }

    return {
      chartType: chartType,
      labels: labels,
      datasets: datasets
    };
  }

  // Simple Markdown Code Block Converter to style text outputs nicely
  formatAIResponse(text: string): string {
    if (!text) return '';
    let escaped = text;

    escaped = escaped.replace(/\*\*([\s\S]*?)\*\*/g, '<strong class="text-indigo-400 font-semibold">$1</strong>');

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

    escaped = escaped.replace(/```([\s\S]*?)```/g, (match, code) => {
      return `<pre class="bg-slate-950 border border-slate-800 rounded-xl p-4 my-3 overflow-x-auto text-xs font-mono text-slate-300">${code.trim()}</pre>`;
    });

    escaped = escaped.split('\n').join('<br>');
    return escaped;
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const responseBox = document.getElementById('responseBox');
      if (responseBox) {
        responseBox.scrollTop = responseBox.scrollHeight;
      }
    }, 50);
  }
}