// analyze.controller.ts
import { Controller, Post, Body, HttpException, HttpStatus, Res } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { Response } from 'express';
import { firstValueFrom } from 'rxjs';

@Controller()
export class AnalyzeController {
  constructor(private readonly httpService: HttpService) {}

  @Post('/analyze')
  async analyze(@Body() requestBody: any, @Res() res: Response) {
    if (!requestBody?.idea_bases) {
      throw new HttpException(
        { message: 'Invalid request: Missing idea_bases field' },
        HttpStatus.BAD_REQUEST,
      );
    }

    const fastapiUrl = 'http://localhost:8001/analyze';

    try {
      const response = await firstValueFrom(
        this.httpService.post(fastapiUrl, requestBody, {
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          responseType: 'stream',
        })
      );

      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');

      response.data.on('data', (chunk) => {
        res.write(chunk);
      });

      response.data.on('end', () => {
        res.end();
      });

      response.data.on('error', (err) => {
        console.error('❌ FastAPI stream error:', err.message);
        res.end();
      });

    } catch (error) {
      throw new HttpException(
        { message: 'FastAPI 요청 실패', error: error.message },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}