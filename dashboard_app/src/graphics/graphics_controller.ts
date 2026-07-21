import { Component, OnInit, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChartConfiguration, ChartData, ChartType } from 'chart.js';
import { BaseChartDirective } from 'ng2-charts';
import { FormsModule } from '@angular/forms';
import { ChartDataService } from './graphics_service';

@Component({
  selector: 'app-ai-chart',
  standalone: true,
  imports: [CommonModule, BaseChartDirective, FormsModule],
  templateUrl: './graphics_controller.html',
  styleUrls: ['./graphics_controller.css']
})
export class AiChartComponent implements OnInit {
  @ViewChild(BaseChartDirective) chart: BaseChartDirective | undefined;

  public chartData: ChartData<'line' | 'bar' | 'pie'> | undefined;
  public chartType: ChartType = 'line';
  
  // New property to display the textual reasoning from the local LLM model
  public aiTextResponse: string = ''; 

  constructor(
    public chartService: ChartDataService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    console.log('🚀 [CONTROLLER]: Component initialized, listening to chart stream...');
    
    this.chartService.chartData$.subscribe(payload => {
      console.log('🔄 [CONTROLLER]: Stream subscription triggered. Payload state:', payload);
      
      if (payload) {
        this.chartData = undefined;
        this.cdr.detectChanges();

        setTimeout(() => {
          this.chartType = payload.chartType;
          this.chartData = {
            labels: [...payload.labels],
            datasets: payload.datasets.map(d => ({
              ...d,
              backgroundColor: payload.chartType === 'pie' 
                ? ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'] 
                : 'rgba(37, 99, 235, 0.5)',
              borderColor: '#2563eb',
              borderWidth: 1
            }))
          };
          
          console.log('✅ [CONTROLLER]: chartData applied to canvas structure:', this.chartData);
          console.log('📈 [CONTROLLER]: Chart type configuration mapped:', this.chartType);
          
          this.cdr.detectChanges();
        }, 10);
      } else {
        console.warn('🛑 [CONTROLLER]: Subscription received null. Clearing chart display layout.');
        this.chartData = undefined;
        this.cdr.detectChanges();
      }
    });
  }

  public onAskAiClick(): void {
    this.chartService.isSending = true;
    this.aiTextResponse = ''; // Reset views
    this.chartData = undefined; // Hide the old canvas
    this.cdr.detectChanges(); 
    
    this.chartService.executePipeline(this.chartService.promptInput).then(() => {
      // After the service runs, check if it was a text-only refusal payload
      // Let's grab the response text straight out of the service state container
      if (!this.chartData) {
         // You can read the raw response string from a property in your service
         this.aiTextResponse = this.chartService.lastResponseContent;
         this.cdr.detectChanges();
      }
    });
  }

}