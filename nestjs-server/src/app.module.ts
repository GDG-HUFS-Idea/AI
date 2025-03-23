import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AnalyzeController } from './analyze.controller';
import { HttpModule } from '@nestjs/axios';

@Module({
  imports: [HttpModule],  // ✅ FastAPI 통신을 위한 HttpModule 추가
  controllers: [AppController, AnalyzeController], // ✅ 컨트롤러 등록 확인
})
export class AppModule {}
