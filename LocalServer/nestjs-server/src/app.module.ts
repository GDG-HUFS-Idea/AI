import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { AnalyzeController } from './analyze.controller';

@Module({
  imports: [HttpModule],  // ✅ HttpModule 추가
  controllers: [AnalyzeController],
  providers: [],
})
export class AppModule {}
