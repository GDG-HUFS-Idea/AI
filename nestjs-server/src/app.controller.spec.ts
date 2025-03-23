import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AnalyzeController } from './analyze.controller';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';

describe('AppController (e2e)', () => {
  let app: INestApplication;

  beforeAll(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      controllers: [AppController, AnalyzeController],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  it('/health (GET) should return server status', async () => {
    const response = await request(app.getHttpServer()).get('/health');
    expect(response.status).toBe(200);
    expect(response.body).toEqual({ status: 'ok', message: 'Server is running' });
  });

  it('/analyze (POST) should return analysis results', async () => {
    const sampleRequest = {
      idea_bases: {
        current_issue: ['High competition'],
        motivation: 'AI-driven automation',
        core_feature: ['Market analysis', 'Trend forecasting'],
        methodology: 'Deep learning & NLP',
        expected_output: 'Insights for business strategy',
      },
    };

    const response = await request(app.getHttpServer())
      .post('/analyze')
      .send(sampleRequest);

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('message', 'Analysis completed successfully!');
    expect(response.body.data).toHaveProperty('summary');
    expect(response.body.data).toHaveProperty('insights');
  });

  it('/analyze (POST) should return 400 if missing idea_bases', async () => {
    const response = await request(app.getHttpServer()).post('/analyze').send({});
    expect(response.status).toBe(400);
    expect(response.body).toHaveProperty('message', 'Invalid request: Missing idea_bases field');
  });
});
