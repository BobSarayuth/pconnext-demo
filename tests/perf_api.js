import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

// Custom metrics
const responseTime = new Trend('response_time');
const successRate = new Rate('success_rate');

export const options = {
  vus: 200,           // 9 virtual users
  duration: '5m',   // run for 10 minutes
  thresholds: {
    http_req_duration: ['p(95)<3000'], // 95% of requests should be below 3s
    success_rate: ['rate>0.95'],       // 95% success rate
  },
};

export default function() {
  const startTime = new Date().getTime();
  const res = http.get('http://localhost:3000/api/history?beginDate=2025-04-01&lastDate=2025-04-09&deleted=false');
  const endTime = new Date().getTime();

  // Record response time
  responseTime.add(endTime - startTime);

  // Parse the JSON response
  let jsonData;
  try {
    jsonData = JSON.parse(res.body);
  } catch (e) {
    console.log('Failed to parse JSON response', e);
  }

  // Check if response is valid
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'result array length > 0': (r) => {
      try {
        const data = JSON.parse(r.body);
        return Array.isArray(data) && data.length > 0;
      } catch (e) {
        return false;
      }
    },
  });

  successRate.add(success);

  // Log details for debugging
  if (!success) {
    console.log(`Failed request: ${res.status}, ${res.body}`);
  }

  // Add random sleep between 1-3 seconds to simulate realistic user behavior
  sleep(Math.random() * 2);
}
