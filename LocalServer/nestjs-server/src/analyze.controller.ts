import { Controller, Post, Body, Inject } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { lastValueFrom } from 'rxjs';

@Controller('analyze')
export class AnalyzeController {
  constructor(@Inject(HttpService) private readonly httpService: HttpService) {}

  @Post()
  async analyze(@Body() request: { prompt: string }) {
    const aiServerUrl = 'http://localhost:8000/analyze'; // FastAPI 서버 URL

    try {
      const response = await lastValueFrom(this.httpService.post(aiServerUrl, request));

      if (!response || !response.data) {
        throw new Error('FastAPI 응답이 비어 있습니다.');
      }

      return response.data;  // ✅ FastAPI 응답을 그대로 반환!
    } catch (error) {
      throw new Error(`FastAPI 서버 요청 실패: ${error.message}`);
    }
  }
}
